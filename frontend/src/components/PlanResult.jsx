import React, { useEffect, useState } from 'react';
import { Check, Info } from 'lucide-react';
import OutfitBoard from './OutfitBoard.jsx';
import { PieceImage } from './OutfitPreview.jsx';

/*
  The result of a trip or wedding plan: a summary with notes, a checklist of pieces to pack
  (or get ready), and a card with an outfit board for each day or function.
  events = true shows function names and dress codes instead of "Day 1".
*/
export default function PlanResult({ plan, goToWardrobe, events = false }) {
  const [packed, setPacked] = useState(() => new Set());
  useEffect(() => setPacked(new Set()), [plan]);
  const toggle = (id) => setPacked((s) => {
    const next = new Set(s);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });
  const labelOf = (d) => d.label || `Day ${d.day}`;
  const nameOf = (n) => (events ? labelOf(plan.days[n - 1]) : `day ${n}`);

  return (
    <>
      <div className="gap-summary">
        <div>
          <strong>{plan.pieces}</strong>
          <span>piece{plan.pieces === 1 ? '' : 's'} {events ? 'to get ready' : 'to pack'} for {plan.outfits} {events ? 'look' : 'outfit'}{plan.outfits === 1 ? '' : 's'}</span>
        </div>
        {plan.notes.map((n) => <p key={n}><Info size={13} /> {n}</p>)}
        {plan.outfits === 0 && <p><button type="button" className="text-btn" onClick={goToWardrobe}>Add clothes to your wardrobe ↗</button></p>}
      </div>

      {plan.packing.length > 0 && (
        <section className="packing">
          <h3>{events ? 'Get-ready list' : 'Packing list'} <small>{packed.size} of {plan.packing.length} ready</small></h3>
          <ul>
            {plan.packing.map(({ item, uses, days: worn }) => (
              <li key={item.id} className={packed.has(item.id) ? 'done' : ''}>
                <label>
                  <input type="checkbox" checked={packed.has(item.id)} onChange={() => toggle(item.id)} />
                  <PieceImage item={item} />
                  <span><b>{item.name}</b><small>{item.category} · {uses === 1 ? nameOf(worn[0]) : `${uses} ${events ? 'functions' : 'days'} (${worn.map(nameOf).join(', ')})`}</small></span>
                  {packed.has(item.id) && <Check size={14} />}
                </label>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className={`trip-days-grid ${events ? 'events' : ''}`}>
        {plan.days.map((d) => (
          <article className="trip-day" key={d.day}>
            <header><b>{labelOf(d)}</b>{!events && <span>{d.occasion}</span>}</header>
            {events && d.dress_code && <p className="dress-code">{d.dress_code}</p>}
            {d.outfit ? (
              <>
                <div className="preview-frame board-frame trip-board"><OutfitBoard pieces={d.outfit.pieces} /></div>
                <p>{d.outfit.pieces.filter((p) => p.item.category === 'Clothing').map((p) => p.item.name).join(' + ')}</p>
                {events && d.outfit.reasons[0] && <p className="plan-reason"><Check size={11} /> {d.outfit.reasons[0]}</p>}
                {events && d.outfit.cautions[0] && <p className="plan-caution">{d.outfit.cautions[0]}</p>}
              </>
            ) : (
              <p className="muted">No look here: there aren't enough different clothes without repeating any (see the note above).</p>
            )}
          </article>
        ))}
      </div>
    </>
  );
}
