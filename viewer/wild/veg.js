import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';

// The vegetation kit (build/wilderness/veg, veg.json) for a level: only the species the level
// places, only the variants the quality allows, only the textures the runtime samples.
//
//  - The glTFs are parsed for geometry only (their images, normal maps and samplers are stripped
//    from the JSON before GLTFLoader sees it), so nothing but base-colour maps is downloaded.
//  - Base-colour maps are fetched once per image URI across every species and variant (the kit
//    shares one leaf atlas per family and barks across species) and capped at `maxTex` px.
//  - Node names come from veg.json (lods[i].name), never derived.
//  - Each LOD's primitives are sorted into three roles by material: `leaf` (alphaMode MASK: the
//    twig cards), `shell` (the opaque metaball hull inside heaths and thickets, *_Shell) and
//    `wood` (bark, and anything else opaque). Each LOD is returned as
//      opaque: the hull + wood merged (hull triangles first), attribute `part` 0 = wood, 1 = hull
//      leaf:   the cards
//      all:    the three merged (hull, wood, cards), part 2 = card: one draw for far LODs
//    with the maps { wood, shell, leaf }. COLOR_0 (AO) becomes the `ao` attribute.

const ROLE = { wood: 0, shell: 1, leaf: 2, soil: 3 };

// variants (seeded re-growths, a draw call each at LOD0) only for the species that fill the
// near views: the cove poplars, the creekside hemlocks and the ridge's red oaks
export const VARIANT_SPECIES = ['tulip_poplar', 'eastern_hemlock', 'northern_red_oak'];

export async function loadVegKit({ world, base = '../build/wilderness/veg/', maxTex = 1024, maxVariants = 1, aniso = 4, variantSpecies = VARIANT_SPECIES,
  propIds = ['chestnut_log_2', 'blowdown_log', 'creek_boulder'] }) {
  let vj;
  try { vj = await (await fetch(base + 'veg.json')).json(); } catch { return { models: {}, vj: null }; }
  const kit = vj.kits?.blue_ridge?.species || {};
  const draco = new DRACOLoader().setDecoderPath('https://unpkg.com/three@0.160.0/examples/jsm/libs/draco/gltf/');
  const loader = new GLTFLoader().setDRACOLoader(draco);
  const texCache = new Map();
  const getTex = (url) => {
    if (!texCache.has(url)) texCache.set(url, (async () => {
      const blob = await (await fetch(url)).blob();
      let bmp = await createImageBitmap(blob, { premultiplyAlpha: 'none', colorSpaceConversion: 'none' });
      if (Math.max(bmp.width, bmp.height) > maxTex) {
        const k = maxTex / Math.max(bmp.width, bmp.height);
        const small = await createImageBitmap(blob, { premultiplyAlpha: 'none', colorSpaceConversion: 'none',
          resizeWidth: Math.round(bmp.width * k), resizeHeight: Math.round(bmp.height * k), resizeQuality: 'high' });
        bmp.close(); bmp = small;
      }
      const t = new THREE.Texture(bmp);
      t.flipY = false;                                   // glTF UV convention
      t.colorSpace = THREE.SRGBColorSpace;
      t.wrapS = t.wrapT = THREE.RepeatWrapping;
      t.minFilter = THREE.LinearMipmapLinearFilter; t.magFilter = THREE.LinearFilter;
      t.anisotropy = aniso;
      t.name = url.split('/').pop();
      t.needsUpdate = true;
      return t;
    })());
    return texCache.get(url);
  };

  const once = new Map();
  const loadOne = (vid) => { if (!once.has(vid)) once.set(vid, loadOne0(vid)); return once.get(vid); };
  const loadOne0 = async (vid) => {
    const sp = vj.species[vid];
    const url = base + sp.gltf;
    const json = await (await fetch(url)).json();
    // base-colour URI per material, then strip every texture reference
    const uriOf = (ti) => {
      if (ti === undefined) return null;
      const t = json.textures[ti], src = t.source ?? t.extensions?.EXT_texture_webp?.source;
      return src === undefined ? null : new URL(json.images[src].uri, new URL(url, location.href)).href;
    };
    const matInfo = (json.materials || []).map((m) => ({
      name: m.name || '', leaf: m.alphaMode === 'MASK', map: uriOf(m.pbrMetallicRoughness?.baseColorTexture?.index) }));
    for (const m of json.materials || []) {
      delete m.normalTexture; delete m.occlusionTexture; delete m.emissiveTexture;
      if (m.pbrMetallicRoughness) { delete m.pbrMetallicRoughness.baseColorTexture; delete m.pbrMetallicRoughness.metallicRoughnessTexture; }
    }
    delete json.textures; delete json.images; delete json.samplers;
    for (const k of ['extensionsUsed', 'extensionsRequired']) if (json[k]) json[k] = json[k].filter((e) => e !== 'EXT_texture_webp');
    const g = await new Promise((ok, err) => loader.parse(JSON.stringify(json), base, ok, err));
    // material name -> info (GLTFLoader keeps material names)
    const byName = new Map(matInfo.map((m) => [m.name, m]));
    const lods = [];
    for (const L of sp.lods) {
      const node = g.scene.getObjectByName(L.name);
      if (!node) break;
      const parts = [];
      node.traverse((o) => {
        if (!o.isMesh) return;
        const mi = byName.get(o.material.name) || { leaf: o.material.alphaTest > 0, map: null, name: o.material.name };
        // (dead wood and rock: the moss tile is the second opaque slot, a root plate's soil the third)
        const role = mi.leaf ? 'leaf' : /Shell|Moss/i.test(mi.name) ? 'shell' : /soil/i.test(mi.name) ? 'soil' : 'wood';
        parts.push({ geo: o.geometry, role, url: mi.map });
      });
      lods.push(parts);
    }
    return { vid, sp, lods };
  };

  // which species: every placed id with a kit model (veg_ids), plus its variants up to maxVariants
  const models = {};
  const jobs = [];
  for (const [id, info] of Object.entries(world.speciesInfo)) {
    if (!info.count || !world.species[id]?.length) continue;
    const vid = (info.veg_ids || []).find((v) => vj.species[v]);
    if (!vid) continue;
    // (ground cover never uses variants: they would only add draw calls under a fern)
    const nv = ['clump', 'mat'].includes(vj.species[vid].kind) || !variantSpecies.includes(vj.species[vid].species || vid) ? 1 : Math.max(1, maxVariants);
    const vars = (kit[vj.species[vid].species || vid] || [vid]).filter((v) => vj.species[v]).slice(0, nv);
    if (!vars.includes(vid)) vars[0] = vid;
    jobs.push((async () => {
      try {
        const loaded = await Promise.all(vars.map(loadOne));
        const variants = [];
        for (const L of loaded) {
          const lods = [];
          for (const parts of L.lods) {
            const maps = {};
            for (const p of parts) if (p.url && !maps[p.role]) maps[p.role] = p.url;
            const tex = {};
            await Promise.all(Object.entries(maps).map(async ([r, u]) => { tex[r] = await getTex(u); }));
            lods.push({ ...mergeLod(parts), maps: tex, parts: parts.map((p) => ({ geo: withAO(p.geo, p.role), map: tex[p.role], role: p.role })) });
          }
          if (lods.length && (lods[0].maps.leaf || lods[0].maps.wood)) variants.push({ name: L.vid, lods, sp: L.sp });
        }
        if (variants.length) models[id] = { name: vid, sp: vj.species[vid], kind: vj.species[vid].kind, variants };
      } catch (e) { console.warn(`veg ${vid}: ${e.message} (stand-in)`); }
    })());
  }
  // props: the kit's dead wood and rock (one LOD each: they are instanced by Props, not the forest)
  const props = {};
  await Promise.all(propIds.filter((v) => vj.species[v]).map(async (vid) => {
    try {
      const L = await loadOne(vid);
      const li = Math.min(1, L.lods.length - 1), parts = L.lods[li];
      const maps = {};
      for (const p of parts) if (p.url && !maps[p.role]) maps[p.role] = p.url;
      const tex = {};
      await Promise.all(Object.entries(maps).map(async ([r, u]) => { tex[r] = await getTex(u); }));
      props[vid] = { ...mergeLod(parts), maps: tex, sp: vj.species[vid] };
    } catch (e) { console.warn(`veg prop ${vid}: ${e.message}`); }
  }));
  await Promise.all(jobs);
  return { models, props, vj, textures: texCache };
}

function withAO(geo, role) {
  if (!geo.attributes.ao) {
    const c = geo.attributes.color, n = geo.attributes.position.count, ao = new Float32Array(n).fill(1);
    if (c) for (let k = 0; k < n; k++) ao[k] = c.getX(k);
    geo.setAttribute('ao', new THREE.BufferAttribute(ao, 1));
  }
  return geo;
}

// one geometry from parts (position, normal, uv, ao + part role), in the given role order
function merge(parts, order) {
  const list = order.flatMap((r) => parts.filter((p) => p.role === r));
  if (!list.length) return null;
  let nv = 0, ni = 0;
  for (const p of list) { nv += p.geo.attributes.position.count; ni += p.geo.index ? p.geo.index.count : p.geo.attributes.position.count; }
  const pos = new Float32Array(nv * 3), nor = new Float32Array(nv * 3), uv = new Float32Array(nv * 2), ao = new Float32Array(nv), part = new Float32Array(nv);
  const idx = nv > 65535 ? new Uint32Array(ni) : new Uint16Array(ni);
  let ov = 0, oi = 0;
  for (const p of list) {
    const g = withAO(p.geo, p.role), n = g.attributes.position.count;
    const P = g.attributes.position, N = g.attributes.normal, U = g.attributes.uv, A = g.attributes.ao;
    for (let k = 0; k < n; k++) {
      pos[(ov + k) * 3] = P.getX(k); pos[(ov + k) * 3 + 1] = P.getY(k); pos[(ov + k) * 3 + 2] = P.getZ(k);
      if (N) { nor[(ov + k) * 3] = N.getX(k); nor[(ov + k) * 3 + 1] = N.getY(k); nor[(ov + k) * 3 + 2] = N.getZ(k); } else nor[(ov + k) * 3 + 1] = 1;
      if (U) { uv[(ov + k) * 2] = U.getX(k); uv[(ov + k) * 2 + 1] = U.getY(k); }
      ao[ov + k] = A.getX(k); part[ov + k] = ROLE[p.role];
    }
    if (g.index) for (let k = 0; k < g.index.count; k++) idx[oi + k] = g.index.getX(k) + ov;
    else for (let k = 0; k < n; k++) idx[oi + k] = k + ov;
    ov += n; oi += g.index ? g.index.count : n;
  }
  const out = new THREE.BufferGeometry();
  out.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  out.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
  out.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  out.setAttribute('ao', new THREE.BufferAttribute(ao, 1));
  out.setAttribute('part', new THREE.BufferAttribute(part, 1));
  out.setIndex(new THREE.BufferAttribute(idx, 1));
  out.computeBoundingBox();
  return out;
}

function mergeLod(parts) {
  return { opaque: merge(parts, ['shell', 'wood', 'soil']), leaf: merge(parts, ['leaf']), all: merge(parts, ['shell', 'wood', 'soil', 'leaf']),
    tris: parts.reduce((a, p) => a + (p.geo.index ? p.geo.index.count : p.geo.attributes.position.count) / 3, 0) };
}
