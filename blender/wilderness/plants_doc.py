"""Budget / palette / memory tables of a kit from build/wilderness/veg/veg.json, as Markdown
(pasted into design/wilderness/blue_ridge/plants.md).   python3 blender/wilderness/plants_doc.py [blue_ridge]"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
VEG = os.path.join(ROOT, "build", "wilderness", "veg")


def gpu_mb(px):
    return px * px * 4 * 1.333 / 1048576


def main(kit="blue_ridge"):
    man = json.load(open(os.path.join(VEG, "veg.json")))
    K = man["kits"][kit]
    S = man["species"]
    order = ["canopy", "understory", "ground", "deadwood", "rock"]
    out = []
    out.append("| id (+ variants) | kind | height | LOD0 / LOD1 / LOD2 tris | far | draws / LOD | LOD switch (m) | geometry KB |")
    out.append("|---|---|---|---|---|---|---|---|")
    tex = {}
    imp = {}
    geo = 0
    for g in order:
        for base in K["groups"].get(g, []):
            vs = [v for v in K["species"].get(base, []) if v in S]
            if not vs:
                continue
            s = S[vs[0]]
            lods = " / ".join(str(l["tris"]) for l in s["lods"])
            rng = " / ".join(f"{min(S[v]['lods'][i]['tris'] for v in vs)}-{max(S[v]['lods'][i]['tris'] for v in vs)}"
                             if len(vs) > 1 and min(S[v]['lods'][i]['tris'] for v in vs) != max(S[v]['lods'][i]['tris'] for v in vs)
                             else str(s["lods"][i]["tris"]) for i in range(3))
            far = "impostor" if s.get("impostor") else ("culled" if s["kind"] in ("clump", "mat") else "LOD2")
            if s.get("impostor"):
                far += f" {s['impostor']['atlas_px']}/{s['impostor'].get('normal_px', s['impostor']['atlas_px'])}"
            draws = "/".join(str(l["draw_calls"]) for l in s["lods"])
            kb = sum(S[v]["bytes_geometry"] for v in vs) / 1024
            geo += sum(S[v]["bytes_geometry"] for v in vs)
            name = f"`{base}`" + (f" (+{len(vs) - 1})" if len(vs) > 1 else "")
            out.append(f"| {name} | {s['kind']} | {s['height_m']:.1f} m | {rng} | {far} | {draws} | "
                       f"{' / '.join(str(d) for d in s['lod_dist'][1:])} | {kb:.0f} |")
            for v in vs:
                for role, (f, px) in S[v].get("textures", {}).items():
                    tex[f] = px
                if S[v].get("impostor") and not S[v]["impostor"].get("shared_from"):
                    im = S[v]["impostor"]
                    imp[im["albedo"]] = im["atlas_px"]
                    imp[im["normal"]] = im.get("normal_px", im["atlas_px"])
    out.append("")
    t_mb = sum(gpu_mb(px) for px in tex.values())
    i_mb = sum(gpu_mb(px) for px in imp.values())
    shipped = 0
    seen = set()
    for v in [v for l in K["species"].values() for v in l if v in S]:
        s = S[v]
        for f in [s["gltf"]]:
            g = json.load(open(os.path.join(VEG, f)))
            for b in g.get("buffers", []):
                shipped += os.path.getsize(os.path.join(VEG, b["uri"]))
            shipped += os.path.getsize(os.path.join(VEG, f))
            for im in g.get("images", []):
                if im["uri"] not in seen:
                    seen.add(im["uri"])
                    shipped += os.path.getsize(os.path.join(VEG, im["uri"]))
    for f in imp:
        shipped += os.path.getsize(os.path.join(VEG, f))
    out.append(f"Unique textures: {len(tex)} maps, {t_mb:.0f} MB GPU (RGBA8 + mips); impostors: {len(imp)} maps, "
               f"{i_mb:.0f} MB GPU; download for the whole kit (gltf + bin + WebP, every variant): {shipped / 1048576:.1f} MB "
               f"(geometry {geo / 1048576:.1f} MB).")
    out.append("")
    out.append("| texture | px | GPU MB |")
    out.append("|---|---|---|")
    for f, px in sorted(tex.items(), key=lambda kv: -kv[1]):
        out.append(f"| {f} | {px} | {gpu_mb(px):.1f} |")
    out.append("")
    out.append("| species | brief (Appendix B) | measured card means |")
    out.append("|---|---|---|")
    for g in order:
        for base in K["groups"].get(g, []):
            s = S.get(base)
            if s and s.get("palette") and s.get("leaf_mean_srgb"):
                out.append(f"| {s['title']} | {s['palette']} | {', '.join(f'{k}: {v}' for k, v in s['leaf_mean_srgb'].items())} |")
    print("\n".join(out))


if __name__ == "__main__":
    main(*(sys.argv[1:] or []))
