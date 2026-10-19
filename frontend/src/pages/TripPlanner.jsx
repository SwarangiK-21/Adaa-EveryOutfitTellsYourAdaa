import React, { useEffect, useState } from 'react';
import { Luggage, Minus, Plus, RefreshCw, Check, Info } from 'lucide-react';
import { api } from '../api.js';
import Heading from '../components/Heading.jsx';
import OutfitBoard from '../components/OutfitBoard.jsx';
import { PieceImage } from '../components/OutfitPreview.jsx';

const MAX_DAYS = 14;
const STYLES = ['', 'Traditional', 'Western', 'Indo-Western'];

/*
  Trip planner: pick the occasion for each day; Adaa picks an outfit per day from your wardrobe
  without wearing any garment twice (shoes, bags and jewellery are reused), plus a packing checklist.
*/
export default function TripPlanner({ goToWardrobe }) {
  const [occasions, setOccasions] = useState([]);
  const [days, setDays] = useState(['Travel', 'Casual', 'Casual']);
  const [style, setStyle] = useState('');
  const [plan, setPlan] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [packed, setPacked] = useState(() => new Set());

  useEffect(() => { api.getOptions().then((o) => setOccasions(o.occasions)).catch((err) => setError(err.message)); }, []);

  const setCount = (n) => setDays((d) => {
    const count = Math.max(1, Math.min(MAX_DAYS, n));
    return count <= d.length ? d.slice(0, count) : [...d, ...Array(count - d.length).fill(d[d.length - 1] || 'Casual')];
  });
  const setDay = (i, occasion) => setDays((d) => d.map((o, j) => (j === i ? occasion : o)));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      setPlan(await api.planTrip(days, style));
      setPacked(new Set());
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const toggle = (id) => setPacked((s) => {
    const next = new Set(s);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });

  return (
    <>
      <Heading
        eyebrow="PACK LIGHT, LOOK GOOD"
        title={<>Plan a <em>trip</em></>}
        sub="Tell Adaa what each day looks like. It picks a different outfit for every day from your wardrobe (no garment worn twice), and reuses shoes, bags and jewellery to keep the suitcase light."
      />
      <div className="trip-layout">
        <form className="style-form trip-form" onSubmit={submit}>
          <fieldset className="field">
            <legend>How many days?</legend>
            <div className="stepper">
              <button type="button" className="icon-btn" onClick={() => setCount(days.length - 1)} disabled={days.length <= 1} aria-label="One day fewer"><Minus size={14} /></button>
              <b aria-live="polite">{days.length} day{days.length === 1 ? '' : 's'}</b>
              <button type="button" className="icon-btn" onClick={() => setCount(days.length + 1)} disabled={days.length >= MAX_DAYS} aria-label="One more day"><Plus size={14} /></button>
            </div>
          </fieldset>
          <fieldset className="field">
            <legend>What's each day for?</legend>
            <div className="trip-days">
              {days.map((o, i) => (
                <label key={i}>
                  <span>Day {i + 1}</span>
                  <select value={o} onChange={(e) => setDay(i, e.target.value)}>
                    {occasions.map((occ) => <option key={occ} value={occ}>{occ}</option>)}
                  </select>
                </label>
              ))}
            </div>
          </fieldset>
          <fieldset className="field">
            <legend>Style</legend>
            <div className="chips">
              {STYLES.map((s) => (
                <button type="button" key={s || 'any'} className={style === s ? 'chosen' : ''} aria-pressed={style === s} onClick={() => setStyle(s)}>{s || 'Any'}</button>
              ))}
            </div>
          </fieldset>
          <button className="primary" disabled={busy || !occasions.length}>
            {busy ? <><RefreshCw size={15} className="spin" /> Planning…</> : <><Luggage size={15} /> Plan my trip</>}
          </button>
          {error && <p className="form-error">{error}</p>}
        </form>

        <div className="trip-result">
          {!plan && (
            <div className="empty">
              <div><Luggage /></div>
              <h3>Your suitcase, sorted</h3>
              <p>Choose the days on the left and press <b>Plan my trip</b>. Every outfit uses only pieces from your wardrobe.</p>
            </div>
          )}
          {plan && (
            <>
              <div className="gap-summary">
                <div><strong>{plan.pieces}</strong><span>piece{plan.pieces === 1 ? '' : 's'} to pack for {plan.outfits} outfit{plan.outfits === 1 ? '' : 's'}</span></div>
                {plan.notes.map((n) => <p key={n}><Info size={13} /> {n}</p>)}
                {plan.outfits === 0 && <p><button type="button" className="text-btn" onClick={goToWardrobe}>Add clothes to your wardrobe ↗</button></p>}
              </div>

              {plan.packing.length > 0 && (
                <section className="packing">
                  <h3>Packing list <small>{packed.size} of {plan.packing.length} packed</small></h3>
                  <ul>
                    {plan.packing.map(({ item, uses, days: worn }) => (
                      <li key={item.id} className={packed.has(item.id) ? 'done' : ''}>
                        <label>
                          <input type="checkbox" checked={packed.has(item.id)} onChange={() => toggle(item.id)} />
                          <PieceImage item={item} />
                          <span><b>{item.name}</b><small>{item.category} · {uses === 1 ? `day ${worn[0]}` : `${uses} days (${worn.join(', ')})`}</small></span>
                          {packed.has(item.id) && <Check size={14} />}
                        </label>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              <div className="trip-days-grid">
                {plan.days.map((d) => (
                  <article className="trip-day" key={d.day}>
                    <header><b>Day {d.day}</b><span>{d.occasion}</span></header>
                    {d.outfit ? (
                      <>
                        <div className="preview-frame board-frame trip-board"><OutfitBoard pieces={d.outfit.pieces} /></div>
                        <p>{d.outfit.pieces.filter((p) => p.item.category === 'Clothing').map((p) => p.item.name).join(' + ')}</p>
                      </>
                    ) : <p className="muted">No outfit for this day: there aren't enough different clothes for {d.occasion} without repeating any (see the note above).</p>}
                  </article>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}
