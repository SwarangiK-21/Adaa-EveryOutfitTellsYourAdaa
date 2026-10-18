import React, { useRef, useState } from 'react';
import { Crop, RefreshCw, Check, X } from 'lucide-react';
import { redoCutout, useCutoutUrl } from '../cutoutQueue.js';

/*
  "Outfit picture" for one wardrobe item: the garment with its background removed.
  If the photo shows someone wearing it (or other things), the user drags a box
  around just the garment and the cut-out is made again from that part.
*/
export default function CutoutEditor({ item, notify }) {
  const cutoutUrl = useCutoutUrl(item);
  const [framing, setFraming] = useState(false);
  const [box, setBox] = useState(null);          // { x, y, w, h } in 0..1
  const [busy, setBusy] = useState(false);
  const start = useRef(null);
  const area = useRef(null);

  const point = (e) => {
    const r = area.current.getBoundingClientRect();
    return {
      x: Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)),
      y: Math.min(1, Math.max(0, (e.clientY - r.top) / r.height)),
    };
  };
  const down = (e) => { e.preventDefault(); area.current.setPointerCapture(e.pointerId); start.current = point(e); setBox(null); };
  const move = (e) => {
    if (!start.current) return;
    const p = point(e); const s = start.current;
    setBox({ x: Math.min(s.x, p.x), y: Math.min(s.y, p.y), w: Math.abs(p.x - s.x), h: Math.abs(p.y - s.y) });
  };
  const up = () => { start.current = null; };

  const make = async (crop) => {
    setBusy(true);
    try {
      await redoCutout(item, crop);
      notify?.('Outfit picture updated.');
      setFraming(false);
      setBox(null);
    } catch (err) {
      notify?.(err.message || "Couldn't make the outfit picture.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="cutout-editor">
      <div className="cutout-head">
        <span>Outfit picture</span>
        <i>Your photo without its background, used to build outfits.</i>
      </div>

      {!framing ? (
        <div className="cutout-row">
          <div className="cutout-preview checker">
            {busy ? <RefreshCw size={18} className="spin" /> : cutoutUrl ? <img src={cutoutUrl} alt="Outfit picture" /> : <small>Being prepared…</small>}
          </div>
          <div className="cutout-actions">
            <p className="muted">Does it show only the garment? If the photo has a person or other things in it, frame just the garment.</p>
            <button type="button" className="secondary" onClick={() => setFraming(true)} disabled={busy}><Crop size={13} /> Frame just the garment</button>
            <button type="button" className="secondary" onClick={() => make(null)} disabled={busy}><RefreshCw size={13} /> Redo from whole photo</button>
          </div>
        </div>
      ) : (
        <div className="cutout-frame">
          <p className="muted">Drag a box around just the garment (e.g. from the waistband to the hem of the jeans).</p>
          <div
            className="crop-area"
            ref={area}
            onPointerDown={down}
            onPointerMove={move}
            onPointerUp={up}
            role="application"
            aria-label="Drag to frame the garment"
          >
            <img src={item.image_url} alt={item.name} draggable={false} />
            {box && (
              <div className="crop-box" style={{ left: `${box.x * 100}%`, top: `${box.y * 100}%`, width: `${box.w * 100}%`, height: `${box.h * 100}%` }} />
            )}
          </div>
          <div className="row-actions">
            <button type="button" className="primary" onClick={() => make(box)} disabled={busy || !box || box.w < 0.05 || box.h < 0.05}>
              {busy ? <><RefreshCw size={13} className="spin" /> Making…</> : <><Check size={13} /> Use this part</>}
            </button>
            <button type="button" className="secondary" onClick={() => { setFraming(false); setBox(null); }} disabled={busy}><X size={13} /> Cancel</button>
          </div>
        </div>
      )}
    </section>
  );
}
