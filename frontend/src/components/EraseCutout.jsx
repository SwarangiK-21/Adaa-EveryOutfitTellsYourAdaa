import React, { useEffect, useRef, useState } from 'react';
import { Check, RefreshCw, Undo2, X } from 'lucide-react';
import { saveEditedCutout } from '../cutoutQueue.js';

/*
  Erase brush for an item's outfit picture: paint over leftovers (a hanger, a strip of skin, part of
  a shoe) to make them transparent, then save. The garment photo itself is never changed.
*/
const BRUSHES = [
  { label: 'Small', size: 0.025 },
  { label: 'Medium', size: 0.05 },
  { label: 'Large', size: 0.09 },
];

export default function EraseCutout({ item, url, onDone, notify }) {
  const canvas = useRef(null);
  const last = useRef(null);
  const history = useRef([]);
  const [brush, setBrush] = useState(1);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [steps, setSteps] = useState(0);

  useEffect(() => {
    let alive = true;
    fetch(url)
      .then((res) => res.blob())
      .then((blob) => createImageBitmap(blob))
      .then((img) => {
        if (!alive) return;
        const c = canvas.current;
        c.width = img.width;
        c.height = img.height;
        c.getContext('2d').drawImage(img, 0, 0);
        setReady(true);
      })
      .catch(() => notify?.("Couldn't open the outfit picture."));
    return () => { alive = false; };
  }, [url]); // eslint-disable-line react-hooks/exhaustive-deps

  const point = (e) => {
    const c = canvas.current;
    const r = c.getBoundingClientRect();
    return { x: ((e.clientX - r.left) / r.width) * c.width, y: ((e.clientY - r.top) / r.height) * c.height };
  };
  const erase = (from, to) => {
    const c = canvas.current;
    const ctx = c.getContext('2d');
    ctx.save();
    ctx.globalCompositeOperation = 'destination-out';
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.lineWidth = BRUSHES[brush].size * Math.max(c.width, c.height);
    ctx.beginPath();
    ctx.moveTo(from.x, from.y);
    ctx.lineTo(to.x + 0.01, to.y);
    ctx.stroke();
    ctx.restore();
  };
  const down = (e) => {
    if (!ready || busy) return;
    e.preventDefault();
    canvas.current.setPointerCapture(e.pointerId);
    const c = canvas.current;
    history.current = [...history.current.slice(-14), c.getContext('2d').getImageData(0, 0, c.width, c.height)];
    setSteps(history.current.length);
    last.current = point(e);
    erase(last.current, last.current);
  };
  const move = (e) => {
    if (!last.current) return;
    const p = point(e);
    erase(last.current, p);
    last.current = p;
  };
  const up = () => { last.current = null; };
  const undo = () => {
    const snap = history.current.pop();
    if (snap) canvas.current.getContext('2d').putImageData(snap, 0, 0);
    setSteps(history.current.length);
  };

  // Trim the now-empty edges, then save as the item's outfit picture.
  const save = async () => {
    const c = canvas.current;
    const { data } = c.getContext('2d').getImageData(0, 0, c.width, c.height);
    let x0 = c.width; let y0 = c.height; let x1 = -1; let y1 = -1;
    for (let y = 0; y < c.height; y++) {
      for (let x = 0; x < c.width; x++) {
        if (data[(y * c.width + x) * 4 + 3] > 8) {
          if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
        }
      }
    }
    if (x1 < 0) { notify?.('Everything was erased. Undo a little and try again.'); return; }
    const pad = Math.round(0.03 * Math.max(x1 - x0, y1 - y0));
    const tx = Math.max(0, x0 - pad); const ty = Math.max(0, y0 - pad);
    const tw = Math.min(c.width, x1 + pad + 1) - tx; const th = Math.min(c.height, y1 + pad + 1) - ty;
    const out = document.createElement('canvas');
    out.width = tw;
    out.height = th;
    out.getContext('2d').drawImage(c, tx, ty, tw, th, 0, 0, tw, th);
    setBusy(true);
    try {
      const blob = await new Promise((resolve) => out.toBlob(resolve, 'image/png'));
      await saveEditedCutout(item, blob);
      notify?.('Outfit picture updated.');
      onDone();
    } catch (err) {
      notify?.(err.message || "Couldn't save the outfit picture.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="cutout-frame">
      <p className="muted">Paint over anything that isn't part of the garment, like a hanger or a bit of skin.</p>
      <div className="chips" role="group" aria-label="Brush size">
        {BRUSHES.map((b, i) => (
          <button key={b.label} type="button" className={brush === i ? 'chosen' : ''} aria-pressed={brush === i} onClick={() => setBrush(i)}>
            {b.label} brush
          </button>
        ))}
      </div>
      <div className="erase-area checker">
        {!ready && <RefreshCw size={18} className="spin" />}
        <canvas
          ref={canvas}
          onPointerDown={down}
          onPointerMove={move}
          onPointerUp={up}
          onPointerCancel={up}
          style={{ display: ready ? 'block' : 'none' }}
          aria-label="Paint to erase parts of the outfit picture"
        />
      </div>
      <div className="row-actions">
        <button type="button" className="primary" onClick={save} disabled={busy || !ready || !steps}>
          {busy ? <><RefreshCw size={13} className="spin" /> Saving…</> : <><Check size={13} /> Save</>}
        </button>
        <button type="button" className="secondary" onClick={undo} disabled={busy || !steps}><Undo2 size={13} /> Undo</button>
        <button type="button" className="secondary" onClick={onDone} disabled={busy}><X size={13} /> Cancel</button>
      </div>
    </div>
  );
}
