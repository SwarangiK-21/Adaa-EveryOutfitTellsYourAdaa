import React, { useEffect, useState } from 'react';
import { Luggage, Minus, Plus, RefreshCw } from 'lucide-react';
import { api } from '../api.js';
import Heading from '../components/Heading.jsx';
import { useUser } from '../user.js';
import PlanResult from '../components/PlanResult.jsx';

const MAX_DAYS = 14;
const STYLES = ['', 'Traditional', 'Western', 'Indo-Western'];

/*
  Trip planner: pick the occasion for each day; Adaa picks an outfit per day from your wardrobe
  without wearing any garment twice (shoes, bags and jewellery are reused), plus a packing checklist.
*/
export default function TripPlanner({ goToWardrobe }) {
  const { first } = useUser();
  const [occasions, setOccasions] = useState([]);
  const [days, setDays] = useState(['Travel', 'Casual', 'Casual']);
  const [style, setStyle] = useState('');
  const [plan, setPlan] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

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
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };


  return (
    <>
      <Heading
        eyebrow="PACK LIGHT, LOOK GOOD"
        title={<>Plan a <em>trip, {first}</em></>}
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
          {plan && <PlanResult plan={plan} goToWardrobe={goToWardrobe} />}
        </div>
      </div>
    </>
  );
}
