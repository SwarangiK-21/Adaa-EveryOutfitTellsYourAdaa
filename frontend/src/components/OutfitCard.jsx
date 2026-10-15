import React from 'react';
import { Check, AlertTriangle } from 'lucide-react';

// One recommended outfit: clothes as big photos, accessories as small ones,
// then why it works and anything to watch out for.
export default function OutfitCard({ outfit }) {
  const clothing = outfit.pieces.filter((p) => p.item.category === 'Clothing');
  const extras = outfit.pieces.filter((p) => p.item.category !== 'Clothing');
  const title = clothing.map((p) => p.item.name).join(' + ');

  return (
    <article className="outfit">
      <header>
        <small>LOOK {outfit.rank}</small>
        <h3>{title}</h3>
      </header>

      <div className="outfit-main">
        {clothing.map((p) => (
          <figure key={p.item.id}>
            <img src={p.item.image_url} alt={p.item.name} loading="lazy" />
            <figcaption><b>{p.role}</b>{p.item.name}</figcaption>
          </figure>
        ))}
      </div>

      {extras.length > 0 && (
        <div className="outfit-extras">
          {extras.map((p) => (
            <figure key={p.item.id}>
              <img src={p.item.image_url} alt={p.item.name} loading="lazy" />
              <figcaption><b>{p.role}</b>{p.item.name}</figcaption>
            </figure>
          ))}
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
    </article>
  );
}
