import React, { useEffect, useState } from 'react';
import { useCutoutUrls } from '../cutoutQueue.js';

/*
  "Ghost mannequin" outfit board: the user's own garments, background removed,
  arranged as if worn. No person and no AI image: every piece is the user's real photo.

  Layout works in "board units": the board is 100 wide and 166.7 tall (3:5).
  Garments are sized relative to each other (a top a little wider than the skirt's waist),
  stacked with the top's hem over the waistband, shoes just below the hem, and accessories
  (jewellery, watch, bag) in tidy columns on either side. Each picture's real proportions (width/height) are used,
  so nothing is stretched.
*/

const BOARD_H = (100 * 5) / 3;
const has = (text, words) => words.some((w) => text.includes(w));
const typeOf = (p) => `${p.item.item_type} ${p.item.name}`.toLowerCase();

// Natural width/height of each picture (cut-out, or the original photo while it's being prepared).
function useAspects(urls) {
  const [aspects, setAspects] = useState({});
  const key = urls.join('|');
  useEffect(() => {
    let alive = true;
    urls.forEach((url) => {
      if (!url || aspects[url]) return;
      const img = new Image();
      img.onload = () => alive && setAspects((a) => ({ ...a, [url]: img.naturalWidth / img.naturalHeight }));
      img.src = url;
    });
    return () => { alive = false; };
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps
  return aspects;
}

// How wide each kind of piece is drawn, in board units, before any final scaling.
function baseWidth(piece) {
  const t = typeOf(piece);
  switch (piece.role) {
    case 'Top':
    case 'Blouse':
      return has(t, ['sleeveless', 'tank', 'cami', 'halter', 'tube', 'strap']) ? 44 : has(t, ['kurta', 'kurti', 'tunic']) ? 52 : 56;
    case 'Bottom':
      if (has(t, ['palazzo', 'sharara', 'baggy', 'wide', 'flare', 'lehenga'])) return 44;
      if (has(t, ['skirt'])) return 42;
      // Slim fits: the photo's box is mostly air between the legs, so give them a little more room.
      return has(t, ['skinny', 'skin fit', 'slim', 'legging', 'jegging', 'churidar']) ? 41 : 38;
    case 'Outfit':
      return has(t, ['saree', 'sari', 'lehenga', 'gown', 'anarkali', 'maxi']) ? 58 : 50;
    case 'Layer': return 62;
    case 'Dupatta': return 34;
    case 'Footwear': return 26;
    case 'Bag': return 22;
    case 'Necklace': return 19;
    case 'Earrings': return 13;
    default: return 15;   // bangles, bracelets, watch, other accessories
  }
}

function layout(pieces, urlOf, aspects) {
  const by = (...roles) => pieces.filter((p) => roles.includes(p.role));
  const box = (piece, w) => {
    const a = aspects[urlOf(piece)] || 0.8;
    return { piece, w, h: w / a };
  };
  const onePiece = by('Outfit')[0];
  const top = by('Top', 'Blouse')[0];
  const bottom = by('Bottom')[0];
  const shoes = by('Footwear')[0];

  // 1. The main column: top over bottom (or a one-piece), then shoes.
  const column = [];
  let y = 0;
  let topBox = null;
  if (onePiece) {
    topBox = box(onePiece, baseWidth(onePiece));
    column.push({ ...topBox, y, z: 3 });
    y += topBox.h;
  } else {
    if (top) {
      // A regular top is drawn no taller than it is wide (photos taken on a model are often long).
      const w = baseWidth(top);
      const long = has(typeOf(top), ['kurta', 'kurti', 'tunic', 'long']);
      const a = aspects[urlOf(top)] || 0.8;
      // ...and at most about 1.35 times as wide as the bottom, so the two balance.
      const maxW = bottom ? baseWidth(bottom) * 1.35 : w;
      const topW = Math.min(w, maxW);
      topBox = box(top, long ? topW : Math.min(topW, 0.95 * topW * a));
      column.push({ ...topBox, y, z: 4 });
      y += topBox.h * (bottom ? 0.9 : 1);     // the top's hem sits over the waistband
    }
    if (bottom) {
      const b = box(bottom, baseWidth(bottom));
      column.push({ ...b, y, z: 2 });
      y += b.h;
    }
  }
  const t = [onePiece, bottom].filter(Boolean).map(typeOf).join(' ');
  const longHem = onePiece ? has(t, ['saree', 'sari', 'gown', 'maxi', 'lehenga', 'anarkali', 'long'])
    : has(t, ['jeans', 'pant', 'trouser', 'palazzo', 'legging', 'churidar', 'salwar', 'maxi', 'long', 'sharara']);
  if (shoes) {
    // Shoes are sized to the hem: a pair is about half as wide as the trousers or skirt above it,
    // and no taller than a fifth of a long outfit (short outfits still get full-size shoes).
    const under = bottom || onePiece;
    const a = aspects[urlOf(shoes)] || 1;
    let sw = under ? Math.min(24, Math.max(17, baseWidth(under) * 0.52)) : baseWidth(shoes);
    if (column.length) sw = Math.min(sw, Math.max(26, y * 0.2) * a);
    const s = box(shoes, sw);
    y += column.length ? (longHem ? -2 : 3) : 0;  // tucked under long hems; just below short ones
    column.push({ ...s, y, z: 1 });
    y += s.h;
  }
  const columnH = Math.max(y, 1);

  // 2. Fit the column into the board (leaving room above and below), centred.
  const room = BOARD_H * 0.86;
  const scale = Math.min(1.15, room / columnH);
  const top0 = (BOARD_H - columnH * scale) / 2;
  const slots = column.map((s) => ({ piece: s.piece, cx: 50, y: top0 + s.y * scale, w: s.w * scale, h: s.h * scale, z: s.z }));

  // Layers sit behind the top; a dupatta drapes over one side.
  if (topBox) {
    const ts = slots[0];
    const layer = by('Layer')[0];
    if (layer && !onePiece) {
      const l = box(layer, ts.w * 1.12);
      slots.push({ piece: layer, cx: 50, y: ts.y - 1, w: l.w, h: Math.min(l.h, ts.h * 1.3), z: 1 });
    }
    const dupatta = by('Dupatta')[0];
    if (dupatta) {
      const d = box(dupatta, baseWidth(dupatta) * scale);
      slots.push({ piece: dupatta, cx: 50 + ts.w * 0.32, y: ts.y, w: d.w, h: Math.min(d.h, BOARD_H * 0.55), z: 5 });
    }
  }

  // 3. Accessories in two tidy columns beside the outfit. (Necklaces go in a column too: product
  //    photos of chains are long diagonal lines that look like a hanger wire when laid over the top.)
  //    Each column is a neat stack around the outfit's upper half, close to the clothes beside it.
  const left = [...by('Earrings'), ...by('Bangles / bracelet'), ...by('Accessory')];
  const right = [...by('Necklace'), ...by('Bag'), ...by('Jewellery')];
  const main = slots.slice(0, column.length);
  const outfitTop = top0; const outfitH = columnH * scale;
  const halfWidthAt = (y0, y1) => Math.max(14, ...main.filter((m) => m.y < y1 && m.y + m.h > y0).map((m) => m.w / 2));
  const placeSide = (list, side) => {
    if (!list.length) return;
    const boxes = list.map((piece) => box(piece, baseWidth(piece)));
    const room = outfitH - 8;
    const used = boxes.reduce((sum, b) => sum + b.h, 0);
    const gap = Math.min(9, Math.max(2, (room - used) / Math.max(1, boxes.length - 1)));
    const total = used + gap * (boxes.length - 1);
    let y = Math.max(16, outfitTop + Math.max(4, outfitH * 0.42 - total / 2));
    boxes.forEach((b) => {
      const reach = halfWidthAt(y, y + b.h) + 3 + b.w / 2;
      const cx = side < 0 ? Math.max(b.w / 2 + 2, 50 - reach) : Math.min(98 - b.w / 2, 50 + reach);
      slots.push({ piece: b.piece, cx, y, w: b.w, h: b.h, z: 6 });
      y += b.h + gap;
    });
  };
  placeSide(left, -1);
  placeSide(right, 1);
  return slots;
}

function Slot({ slot, urlOf }) {
  const [failed, setFailed] = useState(false);
  const { piece, cx, y, w, h, z } = slot;
  const url = urlOf(piece);
  const isCutout = url !== piece.item.image_url && !failed;
  return (
    <div
      className="board-slot"
      style={{ left: `${cx - w / 2}%`, top: `${(y / BOARD_H) * 100}%`, width: `${w}%`, height: `${(h / BOARD_H) * 100}%`, zIndex: z }}
      title={`${piece.role}: ${piece.item.name}`}
    >
      {isCutout
        ? <img className="board-cutout" src={url} alt="" onError={() => setFailed(true)} />
        : <img className="board-photo" src={piece.item.image_url} alt="" />}
    </div>
  );
}

export default function OutfitBoard({ pieces }) {
  // Each piece's best picture: its clean cut-out if ready, else the original photo.
  const cutouts = useCutoutUrls(pieces.map((p) => p.item));
  const urlOf = (piece) => cutouts[piece.item.id] || piece.item.image_url;
  const aspects = useAspects(pieces.map(urlOf));
  const slots = layout(pieces, urlOf, aspects);
  const summary = pieces.map((p) => `${p.item.name} (${p.role.toLowerCase()})`).join(', ');
  return (
    <div className="board" role="img" aria-label={`Your pieces arranged as an outfit: ${summary}`}>
      <div className="board-floor" />
      {slots.map((s) => <Slot key={s.piece.item.id} slot={s} urlOf={urlOf} />)}
    </div>
  );
}

// True while any piece is still waiting for its clean cut-out.
export const needsCutouts = (pieces) => pieces.some((p) => !p.item.cutout_url);
