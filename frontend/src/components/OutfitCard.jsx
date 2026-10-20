import React from 'react';
import { Check, AlertTriangle, Repeat } from 'lucide-react';
import OutfitPreview, { PieceImage } from './OutfitPreview.jsx';

// One outfit: a large full-body preview first, then the individual pieces
// (with swap buttons), why it works, anything to watch out for, and actions.
// Optional: label/title override, photo (verified preview), onSwap(piece), actions, notice.
export default function OutfitCard({ outfit, label, title, onSwap, actions, notice, photo, personal }) {
  const clothing = outfit.pieces.filter((p) => p.item.category === 'Clothing');
  const extras = outfit.pieces.filter((p) => p.item.category !== 'Clothing');
  const heading = title || clothing.map((p) => p.item.name).join(' + ') || 'Your look';

  const piece = (p) => (
    <figure key={p.item.id}>
      <div className="piece-photo">
        <PieceImage item={p.item} />
        {onSwap && (
          <button type="button" className="icon-btn swap-btn" onClick={() => onSwap(p)}
            aria-label={`Swap ${p.item.name}`} title="Swap this piece">
            <Repeat size={13} />
          </button>
        )}
      </div>
      <figcaption><b>{p.role}</b>{p.item.name}</figcaption>
    </figure>
  );

  return (
    <article className="outfit">
      <header>
        <small>{label ?? `LOOK ${outfit.rank}`}</small>
        <h3>{heading}</h3>
        {personal && <p className="personal-note">{personal}</p>}
      </header>

      <div className="outfit-layout">
        <OutfitPreview pieces={outfit.pieces} photo={photo} title={heading} />

        <div className="outfit-details">
          {notice && <p className="outfit-notice"><AlertTriangle size={13} />{notice}</p>}

          {outfit.pieces.length > 0 && (
            <div className="outfit-pieces">
              <small className="pieces-label">THE PIECES{onSwap ? ' · TAP ⇄ TO SWAP' : ''}</small>
              {clothing.length > 0 && <div className="outfit-main">{clothing.map(piece)}</div>}
              {extras.length > 0 && <div className="outfit-extras">{extras.map(piece)}</div>}
            </div>
          )}

          <ul className="reasons">
            {outfit.reasons.map((r) => <li key={r}><Check size={14} />{r}</li>)}
          </ul>
          {outfit.cautions.length > 0 && (
            <ul className="cautions">
              {outfit.cautions.map((c) => <li key={c}><AlertTriangle size={14} />{c}</li>)}
            </ul>
          )}

          {actions && <div className="outfit-actions">{actions}</div>}
        </div>
      </div>
    </article>
  );
}
