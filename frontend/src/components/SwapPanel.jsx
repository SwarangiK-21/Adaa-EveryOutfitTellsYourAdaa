import React, { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { api } from '../api.js';

// Shows other pieces from the wardrobe that could replace one piece of an outfit.
export default function SwapPanel({ prefs, itemIds, piece, onPick, onClose }) {
  const [options, setOptions] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.swapOptions(prefs, itemIds, piece.item.id).then(setOptions).catch((err) => setError(err.message));
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <section className="modal swap-panel" role="dialog" aria-modal="true" aria-labelledby="swap-title">
        <div className="modal-head">
          <div>
            <small>SWAP {piece.role.toUpperCase()}</small>
            <h2 id="swap-title">Instead of {piece.item.name}…</h2>
          </div>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close"><X size={18} /></button>
        </div>

        <div className="swap-body">
          {error && <p className="form-error" role="alert">{error}</p>}
          {!options && !error && <p className="muted">Looking through your wardrobe…</p>}
          {options && options.length === 0 && (
            <p className="muted">
              No other piece in your wardrobe can take this place and still make a wearable outfit.
              Add more {piece.role.toLowerCase()} options in My Wardrobe for more choice.
            </p>
          )}
          {options && options.length > 0 && (
            <div className="swap-options">
              {options.map((o) => (
                <button type="button" key={o.item.id} className={'swap-option' + (o.tagged ? '' : ' untagged')} onClick={() => onPick(o)}>
                  <img src={o.item.image_url} alt="" />
                  <b>{o.item.name}</b>
                  <small>{o.reason}</small>
                </button>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
