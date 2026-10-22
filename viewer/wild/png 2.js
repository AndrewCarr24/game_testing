// Decoder for the terrain generator's PNGs (blender/wilderness/terrain.py write_png): 8-bit
// grey / RGB / RGBA or 16-bit grey, non-interlaced, rows filtered None (0) or Up (2), so a row
// unfilters with one add. Exact values (no canvas, no premultiplied alpha), no library: the IDAT
// stream inflates with the browser's DecompressionStream('deflate') (zlib framing).
// Returns { width, height, channels, depth, data } with data a Uint8Array (8-bit, row-major,
// interleaved channels) or Uint16Array (16-bit grey); image row 0 = the file's first row (north).

export async function decodePNG(buffer) {
  const bytes = new Uint8Array(buffer);
  const dv = new DataView(buffer);
  let pos = 8, w = 0, h = 0, depth = 8, color = 0;
  const idat = [];
  while (pos < bytes.length) {
    const n = dv.getUint32(pos), tag = String.fromCharCode(...bytes.subarray(pos + 4, pos + 8));
    if (tag === 'IHDR') { w = dv.getUint32(pos + 8); h = dv.getUint32(pos + 12); depth = bytes[pos + 16]; color = bytes[pos + 17]; }
    else if (tag === 'IDAT') idat.push(bytes.subarray(pos + 8, pos + 8 + n));
    else if (tag === 'IEND') break;
    pos += 12 + n;
  }
  const ch = { 0: 1, 2: 3, 4: 2, 6: 4 }[color];
  const stream = new Blob(idat).stream().pipeThrough(new DecompressionStream('deflate'));
  const raw = new Uint8Array(await new Response(stream).arrayBuffer());
  const stride = (w * ch * depth) / 8, bpp = Math.max(1, (ch * depth) / 8);
  const out = new Uint8Array(stride * h);
  for (let y = 0; y < h; y++) {
    const f = raw[y * (stride + 1)], src = y * (stride + 1) + 1, dst = y * stride;
    if (f === 0) out.set(raw.subarray(src, src + stride), dst);
    else if (f === 2) {
      if (y === 0) out.set(raw.subarray(src, src + stride), dst);
      else for (let x = 0; x < stride; x++) out[dst + x] = (raw[src + x] + out[dst - stride + x]) & 255;
    } else {
      // Sub / Average / Paeth (not written by terrain.py, but cheap to support)
      for (let x = 0; x < stride; x++) {
        const a = x >= bpp ? out[dst + x - bpp] : 0, b = y ? out[dst - stride + x] : 0, c = x >= bpp && y ? out[dst - stride + x - bpp] : 0;
        let pr;
        if (f === 1) pr = a; else if (f === 3) pr = (a + b) >> 1;
        else { const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c); pr = pa <= pb && pa <= pc ? a : pb <= pc ? b : c; }
        out[dst + x] = (raw[src + x] + pr) & 255;
      }
    }
  }
  if (depth === 16) {
    const d16 = new Uint16Array(w * h * ch);
    for (let i = 0; i < d16.length; i++) d16[i] = (out[2 * i] << 8) | out[2 * i + 1];
    return { width: w, height: h, channels: ch, depth, data: d16 };
  }
  return { width: w, height: h, channels: ch, depth, data: out };
}

export async function fetchPNG(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return decodePNG(await r.arrayBuffer());
}
