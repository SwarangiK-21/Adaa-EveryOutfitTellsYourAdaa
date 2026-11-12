// Background thread that turns a garment photo into a clean "garment only" picture.
// Running here (not on the page) keeps Peheraav responsive, and isn't slowed down when the tab is hidden.
//
// Two free models, both on the CPU via Microsoft's onnxruntime-web (MIT):
//   1. IS-Net (Apache 2.0): separates the foreground (garment, hanger, model...) from the background.
//   2. SegFormer-B2 clothes parser (NVIDIA licence: non-commercial use only): labels each pixel
//      as top / skirt / pants / dress / shoes / bag / face / arms / legs..., so we can keep only
//      the garment itself, e.g. a top without the model wearing it, jeans without the shoes.
import * as ort from 'onnxruntime-web';

// One thread: multi-threaded mode hung when tested (nested worker threads), and this runs in the
// background once per garment anyway. (WebGPU was tried too: on Intel Iris Xe it hung.)
ort.env.wasm.numThreads = 1;

const SIZE = 1024;           // IS-Net input
const PSIZE = 512;           // parser input
const BODY = [2, 11, 12, 13, 14, 15];   // hair, face, legs, arms: "a person is in this photo"
const sessions = {};

function session(name) {
  if (!sessions[name]) {
    sessions[name] = ort.InferenceSession.create(`/api/models/${name}`, { executionProviders: ['wasm'] })
      .catch((err) => { delete sessions[name]; throw err; });
  }
  return sessions[name];
}

function pixels(img, sx, sy, sw, sh, size) {
  const canvas = new OffscreenCanvas(size, size);
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  ctx.drawImage(img, sx, sy, sw, sh, 0, 0, size, size);
  return ctx.getImageData(0, 0, size, size).data;
}

// 1. Foreground mask from IS-Net, 0..1 per pixel at SIZE x SIZE (with a contrast step against haze).
async function foreground(img, sx, sy, sw, sh) {
  const px = pixels(img, sx, sy, sw, sh, SIZE);
  let max = 1;
  for (let i = 0; i < px.length; i += 4) max = Math.max(max, px[i], px[i + 1], px[i + 2]);
  const mean = [0.485, 0.456, 0.406];
  const input = new Float32Array(3 * SIZE * SIZE);
  for (let i = 0, p = 0; p < SIZE * SIZE; i += 4, p++) {
    for (let c = 0; c < 3; c++) input[c * SIZE * SIZE + p] = px[i + c] / max - mean[c];
  }
  const s = await session('isnet');
  const out = await s.run({ [s.inputNames[0]]: new ort.Tensor('float32', input, [1, 3, SIZE, SIZE]) });
  const pred = out[s.outputNames[0]].data;
  let lo = Infinity; let hi = -Infinity;
  for (let i = 0; i < SIZE * SIZE; i++) { lo = Math.min(lo, pred[i]); hi = Math.max(hi, pred[i]); }
  const fg = new Float32Array(SIZE * SIZE);
  for (let i = 0; i < SIZE * SIZE; i++) {
    const v = (pred[i] - lo) / (hi - lo || 1);
    fg[i] = v <= 0.25 ? 0 : v >= 0.75 ? 1 : (v - 0.25) / 0.5;
  }
  return fg;
}

// What to cut away for this garment: the person (and hat/sunglasses), plus the other kinds of thing
// that are clearly separate from it. Look-alike labels (a skirt read as "dress") are never cut.
function awayLabels(want) {
  const away = new Set([...BODY, 1, 3]);
  const has = (...labels) => labels.some((l) => want.has(l));
  const add = (...labels) => labels.forEach((l) => away.add(l));
  if (has(9, 10)) add(4, 5, 6, 7, 16);                 // shoes: not the legs' clothes
  else if (has(16)) add(4, 5, 6, 7, 9, 10);            // bag: not the outfit
  else {
    add(9, 10, 16);                                    // clothes: never the shoes or a bag
    if (has(4) && !has(5, 6)) add(5, 6);               // a top: not the jeans/skirt below it
    if (has(5, 6) && !has(4)) add(4);                  // a bottom: not the top above it
  }
  want.forEach((l) => away.delete(l));
  return away;
}

// 2. Clothes parser: where the garment roughly is, and what is clearly something else.
//    Returns null when no person is in the photo (product photos, flat lays and hangers are already
//    clean with IS-Net alone) or when the parser doesn't recognise the garment.
// Run the clothes parser: the most likely label for each cell of a coarse grid (w x h), plus the
// 512 x 512 picture it looked at.
async function labelMap(img, sx, sy, sw, sh) {
  const px = pixels(img, sx, sy, sw, sh, PSIZE);
  const mean = [0.485, 0.456, 0.406];
  const std = [0.229, 0.224, 0.225];
  const input = new Float32Array(3 * PSIZE * PSIZE);
  for (let i = 0, p = 0; p < PSIZE * PSIZE; i += 4, p++) {
    for (let c = 0; c < 3; c++) input[c * PSIZE * PSIZE + p] = (px[i + c] / 255 - mean[c]) / std[c];
  }
  const s = await session('clothes');
  const out = await s.run({ [s.inputNames[0]]: new ort.Tensor('float32', input, [1, 3, PSIZE, PSIZE]) });
  const logits = out[s.outputNames[0]];
  const [, classes, h, w] = logits.dims;
  const data = logits.data;
  const labels = new Uint8Array(h * w);
  for (let p = 0; p < h * w; p++) {
    let best = 0; let bestV = -Infinity;
    for (let c = 0; c < classes; c++) {
      const v = data[c * h * w + p];
      if (v > bestV) { bestV = v; best = c; }
    }
    labels[p] = best;
  }
  return { labels, w, h, px };
}

async function parseGarment(img, sx, sy, sw, sh, parts) {
  const { labels, w, h } = await labelMap(img, sx, sy, sw, sh);
  const want = new Set(parts);
  const awaySet = awayLabels(want);
  const garment = new Uint8Array(h * w);
  const awayCells = new Uint8Array(h * w);
  let found = 0; let body = 0;
  for (let p = 0; p < h * w; p++) {
    const best = labels[p];
    if (want.has(best)) { garment[p] = 1; found++; }
    if (awaySet.has(best)) awayCells[p] = 1;
    if (BODY.includes(best)) body++;
  }
  if (body / (h * w) <= 0.01) return null;
  if (found / (h * w) < 0.02) return null;

  // "Near the garment": its cells grown by 3 (about 3% of the picture), to pick which pieces to keep.
  const near = grow(garment, w, h, 3);
  // What to cut is grown by one cell, so thin fringes (a strip of skin, the edge of a sneaker or of
  // the top underneath) go too.
  return { away: upscale(grow(awayCells, w, h, 1), w, h), near, w, h };
}

// Grow a 0/1 cell map by `times` cells in each direction.
function grow(cells, w, h, times) {
  let m = cells;
  for (let r = 0; r < times; r++) {
    const next = new Uint8Array(h * w);
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const i = y * w + x;
        next[i] = m[i] || (x > 0 && m[i - 1]) || (x < w - 1 && m[i + 1])
          || (y > 0 && m[i - w]) || (y < h - 1 && m[i + w]) ? 1 : 0;
      }
    }
    m = next;
  }
  return m;
}

// Smoothly scale a coarse 0/1 label map up to SIZE x SIZE, as 0..1 values.
function upscale(m, w, h) {
  const tiny = new OffscreenCanvas(w, h);
  const tctx = tiny.getContext('2d');
  const tdata = tctx.createImageData(w, h);
  for (let i = 0; i < h * w; i++) tdata.data[i * 4 + 3] = m[i] ? 255 : 0;
  tctx.putImageData(tdata, 0, 0);
  const big = new OffscreenCanvas(SIZE, SIZE);
  const bctx = big.getContext('2d', { willReadFrequently: true });
  bctx.imageSmoothingEnabled = true;
  bctx.imageSmoothingQuality = 'high';
  bctx.drawImage(tiny, 0, 0, SIZE, SIZE);
  const up = bctx.getImageData(0, 0, SIZE, SIZE).data;
  const mask = new Float32Array(SIZE * SIZE);
  for (let i = 0; i < SIZE * SIZE; i++) {
    const v = up[i * 4 + 3] / 255;
    mask[i] = v <= 0.3 ? 0 : v >= 0.7 ? 1 : (v - 0.3) / 0.4; // crisp but not jagged
  }
  return mask;
}

// parts: parser label numbers for this kind of garment (e.g. [6] for jeans), or null to skip the parser.
async function makeCutout(imageUrl, crop, parts) {
  const res = await fetch(imageUrl);
  if (!res.ok) throw new Error("Couldn't load the garment photo.");
  const img = await createImageBitmap(await res.blob());
  const c = crop || { x: 0, y: 0, w: 1, h: 1 };
  const sx = Math.round(c.x * img.width);
  const sy = Math.round(c.y * img.height);
  const sw = Math.max(1, Math.round(c.w * img.width));
  const sh = Math.max(1, Math.round(c.h * img.height));

  const fg = await foreground(img, sx, sy, sw, sh);
  // If the parser fails, the whole cut-out fails (and is retried later) rather than quietly saving
  // a picture that still shows the model.
  const parsed = parts && parts.length ? await parseGarment(img, sx, sy, sw, sh, parts) : null;
  const person = !!parsed;

  // 3. Combined mask -> transparency, shaving the edge so no old background (or skin, when someone
  //    wears the garment) shows as a fringe: 1 px normally, 2 px next to a person.
  const maskCanvas = new OffscreenCanvas(SIZE, SIZE);
  const mctx = maskCanvas.getContext('2d');
  const mask = mctx.createImageData(SIZE, SIZE);
  let alpha = new Uint8ClampedArray(SIZE * SIZE);
  // Keep what IS-Net sees, minus what the parser clearly says is something else (skin, shoes...).
  // Parts of the garment the parser is unsure about are kept, so it never leaves holes.
  for (let i = 0; i < SIZE * SIZE; i++) alpha[i] = Math.round(fg[i] * (parsed ? 1 - parsed.away[i] : 1) * 255);
  for (let pass = person ? 2 : 1; pass > 0; pass--) {
    const shaved = new Uint8ClampedArray(SIZE * SIZE);
    for (let y = 1; y < SIZE - 1; y++) {
      for (let x = 1; x < SIZE - 1; x++) {
        const i = y * SIZE + x;
        shaved[i] = Math.min(alpha[i], alpha[i - 1], alpha[i + 1], alpha[i - SIZE], alpha[i + SIZE]);
      }
    }
    alpha = shaved;
  }
  for (let i = 0; i < SIZE * SIZE; i++) mask.data[i * 4 + 3] = alpha[i];
  mctx.putImageData(mask, 0, 0);
  const full = new OffscreenCanvas(sw, sh);
  const fctx = full.getContext('2d', { willReadFrequently: true });
  fctx.drawImage(maskCanvas, 0, 0, sw, sh);
  fctx.globalCompositeOperation = 'source-in';
  fctx.drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh);

  // 4. Drop small stray bits (e.g. a hanger hook), but keep real parts like the second shoe or earring:
  //    every separate piece at least 15% the size of the biggest one stays. With a person in the photo,
  //    only pieces lying mostly where the parser saw the garment count (not a chair or curtain). Trim.
  const image = fctx.getImageData(0, 0, sw, sh);
  const data = image.data;
  const label = new Int32Array(sw * sh);
  const sizes = [0];
  const onGarment = [0];
  const nearGarment = (x, y) => !parsed
    || parsed.near[Math.floor((y * parsed.h) / sh) * parsed.w + Math.floor((x * parsed.w) / sw)];
  const stack = [];
  for (let i = 0; i < sw * sh; i++) {
    if (data[i * 4 + 3] <= 128 || label[i]) continue;
    const id = sizes.length; let size = 0; let on = 0;
    label[i] = id; stack.push(i);
    while (stack.length) {
      const q = stack.pop(); size++;
      const x = q % sw; const y = (q - x) / sw;
      if (nearGarment(x, y)) on++;
      if (x > 0 && !label[q - 1] && data[(q - 1) * 4 + 3] > 128) { label[q - 1] = id; stack.push(q - 1); }
      if (x < sw - 1 && !label[q + 1] && data[(q + 1) * 4 + 3] > 128) { label[q + 1] = id; stack.push(q + 1); }
      if (y > 0 && !label[q - sw] && data[(q - sw) * 4 + 3] > 128) { label[q - sw] = id; stack.push(q - sw); }
      if (y < sh - 1 && !label[q + sw] && data[(q + sw) * 4 + 3] > 128) { label[q + sw] = id; stack.push(q + sw); }
    }
    sizes.push(size);
    onGarment.push(on);
  }
  const candidate = (id) => onGarment[id] >= 0.5 * sizes[id];
  const biggest = Math.max(0, ...sizes.filter((n, id) => id && candidate(id)));
  if (!biggest) throw new Error("Couldn't find the garment in this photo.");
  const kept = (i) => label[i] && candidate(label[i]) && sizes[label[i]] >= 0.15 * biggest;
  // Faint pixels stay only along the edge of a kept piece (soft edges), not as floating specks.
  const nearKept = (i) => {
    const x = i % sw; const y = (i - x) / sw;
    for (let dy = -3; dy <= 3; dy++) {
      for (let dx = -3; dx <= 3; dx++) {
        const nx = x + dx; const ny = y + dy;
        if (nx >= 0 && ny >= 0 && nx < sw && ny < sh && kept(ny * sw + nx)) return true;
      }
    }
    return false;
  };
  let x0 = sw; let y0 = sh; let x1 = -1; let y1 = -1;
  for (let i = 0; i < sw * sh; i++) {
    const a = data[i * 4 + 3];
    if (!a) continue;
    if (label[i] ? !kept(i) : !nearKept(i)) { data[i * 4 + 3] = 0; continue; }
    const x = i % sw; const y = (i - x) / sw;
    if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
  }
  fctx.globalCompositeOperation = 'copy';
  fctx.putImageData(image, 0, 0);
  const pad = Math.round(0.03 * Math.max(x1 - x0, y1 - y0));
  const tx = Math.max(0, x0 - pad); const ty = Math.max(0, y0 - pad);
  const tw = Math.min(sw, x1 + pad + 1) - tx; const th = Math.min(sh, y1 + pad + 1) - ty;
  const trimmed = new OffscreenCanvas(tw, th);
  trimmed.getContext('2d').drawImage(full, tx, ty, tw, th, 0, 0, tw, th);
  return trimmed.convertToBlob({ type: 'image/png' });
}

// ---------- Reading a new photo: what kind of piece is it, and what colour? ----------

// What each parser label suggests for the "Add a piece" form.
const KINDS = {
  4: { category: 'Clothing', item_type: 'Top', style: 'Western' },
  5: { category: 'Clothing', item_type: 'Skirt', style: 'Western' },
  6: { category: 'Clothing', item_type: 'Trousers', style: 'Western' },
  7: { category: 'Clothing', item_type: 'Dress', style: 'Western' },
  8: { category: 'Accessories', item_type: 'Belt' },
  9: { category: 'Footwear', item_type: 'Shoes' },
  16: { category: 'Bags', item_type: 'Handbag' },
  17: { category: 'Clothing', item_type: 'Dupatta', style: 'Traditional' },
  1: { category: 'Accessories', item_type: 'Hat' },
  3: { category: 'Accessories', item_type: 'Sunglasses' },
};

// Named colours (the same words the colour box suggests), as typical RGB values.
const NAMED = {
  Black: [28, 28, 30], White: [244, 243, 239], Cream: [238, 228, 204], Beige: [214, 194, 164],
  Brown: [112, 74, 48], Tan: [188, 144, 100], Grey: [140, 140, 142], Navy: [26, 34, 62],
  Blue: [58, 98, 168], 'Sky blue': [142, 186, 226], Teal: [32, 126, 126], Green: [62, 134, 76],
  Sage: [156, 174, 142], Olive: [112, 110, 58], Mustard: [200, 156, 42], Yellow: [238, 208, 64],
  Orange: [228, 128, 52], Peach: [238, 188, 160], Red: [188, 40, 46], Maroon: [112, 30, 46],
  Pink: [228, 150, 176], Lavender: [186, 166, 214], Purple: [116, 72, 150],
  'Baby pink': [242, 196, 204], Lemon: [244, 232, 148], 'Bottle green': [24, 62, 42],
  Denim: [84, 106, 136],
};

function toLab([r, g, b]) {
  const lin = (v) => { v /= 255; return v > 0.04045 ? ((v + 0.055) / 1.055) ** 2.4 : v / 12.92; };
  const [R, G, B] = [lin(r), lin(g), lin(b)];
  const f = (t) => (t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116);
  const x = f((R * 0.4124 + G * 0.3576 + B * 0.1805) / 0.95047);
  const y = f(R * 0.2126 + G * 0.7152 + B * 0.0722);
  const z = f((R * 0.0193 + G * 0.1192 + B * 0.9505) / 1.08883);
  return [116 * y - 16, 500 * (x - y), 200 * (y - z)];
}
const NAMED_LAB = Object.entries(NAMED).map(([name, rgb]) => [name, toLab(rgb)]);
const dist = (a, b) => (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2;

// The garment's main colour: the biggest group of similar pixels (k-means, 3 groups), then the
// nearest named colour. Shadows form their own groups, so the main colour wins. If no group is
// clearly the main one (checks, prints), the most colourful sizeable group is used (brown checks on
// white read as brown).
function mainColour(samples) {
  if (!samples.length) return null;
  let centres = [samples[0], samples[Math.floor(samples.length / 2)], samples[samples.length - 1]];
  let groups = [];
  for (let round = 0; round < 8; round++) {
    groups = centres.map(() => []);
    for (const s of samples) {
      let best = 0;
      for (let k = 1; k < centres.length; k++) if (dist(s, centres[k]) < dist(s, centres[best])) best = k;
      groups[best].push(s);
    }
    centres = groups.map((grp, k) => (grp.length
      ? [0, 1, 2].map((c) => grp.reduce((sum, s) => sum + s[c], 0) / grp.length) : centres[k]));
  }
  const biggest = groups.reduce((b, grp, k) => (grp.length > groups[b].length ? k : b), 0);
  const chroma = (lab) => Math.hypot(lab[1], lab[2]);
  let main = biggest;
  if (groups[biggest].length < samples.length / 2) {
    groups.forEach((grp, k) => {
      if (grp.length >= samples.length / 4 && chroma(centres[k]) > chroma(centres[main])) main = k;
    });
  }
  const target = centres[main];
  let best = ['', Infinity];
  for (const [name, lab] of NAMED_LAB) {
    const d = dist(lab, target);
    if (d < best[1]) best = [name, d];
  }
  return best[0];
}

// The parser often mixes up top / skirt / dress on product photos (a top laid flat looks like a
// dress to it). When it clearly says "top" or "skirt" (70% of the garment), that is used. Otherwise
// the garment's shape decides:
//   - someone wearing it with legs showing below -> skirt; with arms beside it -> top (dress if tall)
//   - tall (height >= 1.45 x width, or 1.25 when the parser itself says "dress") -> dress
//   - otherwise wide at the top (shoulders, sleeves) -> top; wider at the hem -> skirt
const CLOTH = new Set([4, 5, 7]);
const ARMS = new Set([14, 15]);
const LEGS = new Set([12, 13]);

function shape(inside, w, h) {
  let x0 = w; let y0 = h; let x1 = -1; let y1 = -1;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      if (inside(x, y)) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
    }
  }
  if (x1 < 0) return null;
  const rowWidth = (y) => {
    let a = -1; let b = -1;
    for (let x = x0; x <= x1; x++) if (inside(x, y)) { if (a < 0) a = x; b = x; }
    return a < 0 ? 0 : b - a + 1;
  };
  const band = (from, to) => {
    let sum = 0;
    for (let y = from; y <= to; y++) sum += rowWidth(y);
    return sum / (to - from + 1);
  };
  const quarter = Math.max(1, Math.floor((y1 - y0 + 1) / 4));
  return {
    x0, y0, x1, y1,
    ratio: (y1 - y0 + 1) / (x1 - x0 + 1),
    topWidth: band(y0, y0 + quarter - 1),
    hemWidth: band(y1 - quarter + 1, y1),
  };
}

function clothingKind(labels, w, h, person) {
  const votes = { 4: 0, 5: 0, 7: 0 };
  for (const l of labels) if (CLOTH.has(l)) votes[l]++;
  const total = votes[4] + votes[5] + votes[7];
  if (votes[4] >= 0.7 * total) return 4;
  if (votes[5] >= 0.7 * total) return 5;
  const inside = (x, y) => CLOTH.has(labels[y * w + x]);
  const s = shape(inside, w, h);
  if (!s) return 4;
  if (person) {
    let size = 0;
    for (const l of labels) if (CLOTH.has(l)) size++;
    const at = (x, y) => (x >= 0 && y >= 0 && x < w && y < h ? labels[y * w + x] : 0);
    const pad = Math.round((s.x1 - s.x0) * 0.3);
    const middle = Math.floor((s.y0 + s.y1) / 2);
    let arms = 0; let legs = 0;
    for (let y = s.y0; y <= middle; y++) for (let x = s.x0 - pad; x <= s.x1 + pad; x++) if (ARMS.has(at(x, y))) arms++;
    const below = Math.min(h - 1, s.y1 + Math.ceil((s.y1 - s.y0) / 2));
    for (let y = s.y1 + 1; y <= below; y++) for (let x = s.x0; x <= s.x1; x++) if (LEGS.has(at(x, y))) legs++;
    if (legs > 0.03 * size) return 5;
    if (arms > 0.03 * size) return s.ratio >= 1.3 ? 7 : 4;
  }
  if (s.ratio >= (votes[7] >= 0.7 * total ? 1.25 : 1.45)) return 7;
  return s.topWidth >= s.hemWidth * 0.95 ? 4 : 5;
}

async function analyse(imageUrl) {
  const res = await fetch(imageUrl);
  if (!res.ok) throw new Error('Could not read the photo.');
  const img = await createImageBitmap(await res.blob());
  const { labels, w, h, px } = await labelMap(img, 0, 0, img.width, img.height);
  // Group the labels: top/skirt/dress count together (decided by shape below), both shoes are a pair.
  const group = (l) => (CLOTH.has(l) ? 'cloth' : l === 10 ? 9 : l);
  const counts = new Map();
  let body = 0;
  for (const l of labels) {
    if (BODY.includes(l)) body++;
    const key = group(l);
    if (key === 'cloth' || KINDS[key]) counts.set(key, (counts.get(key) || 0) + 1);
  }
  const person = body / (w * h) > 0.01;
  const [key, n] = [...counts].sort((a, b) => b[1] - a[1])[0] || [];
  // Too little garment to be sure. Jewellery is sometimes misread as clothes, so clothes need a
  // bigger share of the photo than shoes or a bag (which look small in their photos).
  const minimum = key === 'cloth' || key === 6 ? (person ? 0.06 : 0.1) : 0.03;
  if (!key || n / (w * h) < minimum) return null;

  // Colour from a set of labels' inner cells (not their edges, which blend with the background).
  const cell = PSIZE / w;
  const colourOf = (wanted) => {
    const mine = (x, y) => x >= 0 && y >= 0 && x < w && y < h && wanted(labels[y * w + x]);
    const samples = [];
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        if (!mine(x, y) || !mine(x - 1, y) || !mine(x + 1, y) || !mine(x, y - 1) || !mine(x, y + 1)) continue;
        const i = (Math.floor((y + 0.5) * cell) * PSIZE + Math.floor((x + 0.5) * cell)) * 4;
        samples.push(toLab([px[i], px[i + 1], px[i + 2]]));
      }
    }
    return mainColour(samples);
  };

  let label = key === 'cloth' ? clothingKind(labels, w, h, person) : key;
  // Worn: a "top" and a "skirt" in the same colour are one dress or gown.
  if (key === 'cloth' && person) {
    let tops = 0; let skirts = 0;
    for (const l of labels) { if (l === 4) tops++; else if (l === 5 || l === 7) skirts++; }
    if (tops >= 0.15 * n && skirts >= 0.15 * n
      && colourOf((l) => l === 4) === colourOf((l) => l === 5 || l === 7)) label = 7;
  }
  const colour = colourOf((l) => group(l) === key);
  const kind = { ...KINDS[label] };
  // Blue trousers are usually jeans.
  if (label === 6 && ['Blue', 'Navy', 'Sky blue', 'Denim'].includes(colour)) kind.item_type = 'Jeans';
  return { ...kind, colour };
}

// One job at a time: a model can't run two jobs at once ("Session already started"), e.g. when the
// user re-frames a garment while the background queue is working.
let line = Promise.resolve();
self.onmessage = ({ data: { id, url, crop, parts, task } }) => {
  line = line.then(async () => {
    try {
      if (task === 'analyse') self.postMessage({ id, result: await analyse(url) });
      else self.postMessage({ id, blob: await makeCutout(url, crop, parts) });
    } catch (err) {
      self.postMessage({ id, error: err.message || 'Cut-out failed.' });
    }
  });
};
