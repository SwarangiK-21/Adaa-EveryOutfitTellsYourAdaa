// Background thread that turns a garment photo into a clean "garment only" picture.
// Running here (not on the page) keeps Adaa responsive, and isn't slowed down when the tab is hidden.
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
async function parseGarment(img, sx, sy, sw, sh, parts) {
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
  const want = new Set(parts);
  const awaySet = awayLabels(want);
  const garment = new Uint8Array(h * w);
  const awayCells = new Uint8Array(h * w);
  let found = 0; let body = 0;
  for (let p = 0; p < h * w; p++) {
    let best = 0; let bestV = -Infinity;
    for (let c = 0; c < classes; c++) {
      const v = data[c * h * w + p];
      if (v > bestV) { bestV = v; best = c; }
    }
    if (want.has(best)) { garment[p] = 1; found++; }
    if (awaySet.has(best)) awayCells[p] = 1;
    if (BODY.includes(best)) body++;
  }
  if (body / (h * w) <= 0.01) return null;
  if (found / (h * w) < 0.02) return null;

  // "Near the garment": its cells grown by 3 (about 3% of the picture), to pick which pieces to keep.
  let near = garment;
  for (let r = 0; r < 3; r++) {
    const next = new Uint8Array(h * w);
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const i = y * w + x;
        next[i] = near[i] || (x > 0 && near[i - 1]) || (x < w - 1 && near[i + 1])
          || (y > 0 && near[i - w]) || (y < h - 1 && near[i + w]) ? 1 : 0;
      }
    }
    near = next;
  }
  return { away: upscale(awayCells, w, h), near, w, h };
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

// One job at a time: a model can't run two jobs at once ("Session already started"), e.g. when the
// user re-frames a garment while the background queue is working.
let line = Promise.resolve();
self.onmessage = ({ data: { id, url, crop, parts } }) => {
  line = line.then(async () => {
    try {
      self.postMessage({ id, blob: await makeCutout(url, crop, parts) });
    } catch (err) {
      self.postMessage({ id, error: err.message || 'Cut-out failed.' });
    }
  });
};
