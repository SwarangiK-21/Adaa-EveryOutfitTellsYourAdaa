import React from 'react';
import { Check, AlertTriangle, Repeat } from 'lucide-react';

// One outfit: clothes as big photos, accessories as small ones,
// then why it works and anything to watch out for.
// Optional: label/title override, onSwap(piece) to show swap buttons, and action buttons.
export default function OutfitCard({ outfit, label, title, onSwap, actions, notice }) {
  const clothing = outfit.pieces.filter((p) => p.item.category === 'Clothing');
  const extras = outfit.pieces.filter((p) => p.item.category !== 'Clothing');
  const heading = title || clothing.map((p) => p.item.name).join(' + ') || 'Your look';

  const piece = (p) => (
    <figure key={p.item.id}>
      <div className="piece-photo">
        <img src={p.item.image_url} alt={p.item.name} loading="lazy" />
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
      </header>

      {notice && <p className="outfit-notice"><AlertTriangle size={13} />{notice}</p>}

      {clothing.length > 0 && <div className="outfit-main">{clothing.map(piece)}</div>}
      {extras.length > 0 && <div className="outfit-extras">{extras.map(piece)}</div>}

      <ul className="reasons">
        {outfit.reasons.map((r) => <li key={r}><Check size={14} />{r}</li>)}
      </ul>
      {outfit.cautions.length > 0 && (
        <ul className="cautions">
          {outfit.cautions.map((c) => <li key={c}><AlertTriangle size={14} />{c}</li>)}
        </ul>
      )}

      {actions && <div className="outfit-actions">{actions}</div>}
    </article>
  );
}
