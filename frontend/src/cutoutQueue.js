// Makes missing garment cut-outs in the background, one at a time, and saves them.
// Each garment is done once (about 10–30 s); outfit boards then appear instantly.
import { useEffect, useState } from 'react';
import { api } from './api.js';

// Bump when the cut-out method improves: older automatic cut-outs are then redone.
// "6" = background removal + clothes parser; "6m" = framed by the user (never redone automatically).
export const CUTOUT_VERSION = '6';
const isCurrent = (item) => item.cutout_url && String(item.cutout_version || '').startsWith(CUTOUT_VERSION);

// Which clothes-parser labels make up this item (SegFormer ATR labels):
// 4 top, 5 skirt, 6 pants, 7 dress, 8 belt, 9/10 shoes, 16 bag, 17 scarf, 1 hat, 3 sunglasses.
// null = no parser (jewellery, watches...): background removal only.
export function partsFor(item) {
  const t = `${item.item_type} ${item.name}`.toLowerCase();
  const has = (...w) => w.some((x) => t.includes(x));
  if (item.category === 'Footwear') return [9, 10];
  if (item.category === 'Bags') return [16];
  if (item.category === 'Jewellery') return null;
  if (item.category === 'Accessories') {
    if (has('belt')) return [8];
    if (has('scarf', 'stole')) return [17];
    if (has('hat', 'cap')) return [1];
    if (has('sunglass')) return [3];
    return null;
  }
  // Clothing
  if (has('dupatta', 'stole', 'scarf')) return [17];
  if (has('saree', 'sari', 'gown', 'dress', 'frock', 'one piece', 'jumpsuit', 'anarkali', 'maxi', 'kaftan')) return [4, 5, 6, 7];
  // Bottoms accept their look-alikes: the parser often reads part of a skirt as pants or dress.
  if (has('lehenga')) return [5, 6, 7];
  if (has('skirt')) return [5, 6, 7];
  if (has('jeans', 'pant', 'trouser', 'palazzo', 'legging', 'churidar', 'salwar', 'short', 'jogger', 'sharara')) return [6, 5];
  if (has('kurta', 'kurti', 'tunic')) return [4, 7];
  if (has('top', 'shirt', 'blouse', 'tee', 'sweater', 'hoodie', 'jacket', 'shrug', 'blazer', 'coat', 'cardigan', 'crop')) return [4];
  return [4, 5, 6, 7];
}

const listeners = new Set();
let state = { running: false, done: 0, total: 0, current: '', failed: [] };
let pending = [];             // items waiting for a cut-out
const queued = new Set();     // item ids already waiting or in progress
const made = new Map();       // item id -> new cut-out URL (made since the page loaded)

// The AI library is large, so it's only loaded when a cut-out is actually needed.
const cutter = () => import('./cutout.js');

function emit(patch) {
  state = { ...state, ...patch };
  listeners.forEach((fn) => fn(state));
}

export function subscribeCutouts(fn) {
  listeners.add(fn);
  fn(state);
  return () => listeners.delete(fn);
}

// Called after items load, and after an item is added or its photo changes.
export function queueMissingCutouts(items) {
  const fresh = items.filter((i) => !isCurrent(i) && !made.has(i.id) && !queued.has(i.id));
  if (!fresh.length) return;
  fresh.forEach((i) => queued.add(i.id));
  pending.push(...fresh);
  emit({ total: state.total + fresh.length });
  if (!state.running) run();
}

async function run() {
  emit({ running: true });
  while (pending.length) {
    const item = pending.shift();
    emit({ current: item.name });
    try {
      const { makeCutout } = await cutter();
      const saved = await api.saveCutout(item.id, await makeCutout(item.image_url, null, partsFor(item)), CUTOUT_VERSION);
      made.set(item.id, saved.cutout_url);
    } catch {
      emit({ failed: [...state.failed, item.name] });
    }
    emit({ done: state.done + 1 });
  }
  queued.clear();
  emit({ running: false, current: '', done: 0, total: 0 });
}

// Re-do one garment's cut-out, optionally keeping only a framed part of the photo.
export async function redoCutout(item, crop) {
  const { makeCutout } = await cutter();
  const blob = await makeCutout(item.image_url, crop, partsFor(item));
  const saved = await api.saveCutout(item.id, blob, crop ? `${CUTOUT_VERSION}m` : CUTOUT_VERSION);
  made.set(item.id, saved.cutout_url);
  emit({});
  return saved;
}

// Forget a cut-out made this visit (e.g. the item's photo was replaced).
export function forgetCutout(itemId) {
  made.delete(itemId);
}

// The best cut-out URL for an item: one made since the page loaded, else the item's own.
export function useCutoutUrl(item) {
  const [, setTick] = useState(0);
  useEffect(() => subscribeCutouts(() => setTick((t) => t + 1)), []);
  return made.get(item.id) || item.cutout_url || null;
}

// Same, for several items at once: { [item id]: cut-out URL or null }.
export function useCutoutUrls(items) {
  const [, setTick] = useState(0);
  useEffect(() => subscribeCutouts(() => setTick((t) => t + 1)), []);
  return Object.fromEntries(items.map((i) => [i.id, made.get(i.id) || i.cutout_url || null]));
}
