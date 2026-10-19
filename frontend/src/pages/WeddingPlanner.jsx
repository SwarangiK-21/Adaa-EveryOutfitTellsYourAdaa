import React, { useEffect, useState } from 'react';
import { Gem, Plus, X, RefreshCw, Sparkles } from 'lucide-react';
import { api } from '../api.js';
import Heading from '../components/Heading.jsx';
import PlanResult from '../components/PlanResult.jsx';

const FULL_WEDDING = ['haldi', 'mehendi', 'sangeet', 'wedding', 'reception'];
const STYLES = ['', 'Traditional', 'Western', 'Indo-Western'];

/*
  Wedding planner: pick the functions you're attending (haldi, mehendi, sangeet...), in order.
  Adaa plans a different look for each from your wardrobe, following the usual dress code, with no
  garment repeated; jewellery, shoes and bags are reused.
*/
export default function WeddingPlanner({ goToWardrobe }) {
  const [functions, setFunctions] = useState(null);     // [{ key, label, dress_code, colours }]
  const [chosen, setChosen] = useState(FULL_WEDDING);
  const [style, setStyle] = useState('');
  const [plan, setPlan] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => { api.getEventFunctions().then(setFunctions).catch((err) => setError(err.message)); }, []);
  const byKey = Object.fromEntries((functions || []).map((f) => [f.key, f]));

  const add = (key) => setChosen((c) => (c.length >= 10 ? c : [...c, key]));
  const remove = (index) => setChosen((c) => c.filter((_, i) => i !== index));

  const submit = async (e) => {
    e.preventDefault();
    if (!chosen.length) return;
    setBusy(true);
    setError('');
    try {
      setPlan(await api.planEvent(chosen, style));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Heading
        eyebrow="SHAADI SEASON, SORTED"
        title={<>Plan your <em>wedding looks</em></>}
        sub="Pick the functions you're attending. Adaa styles a different look for each from your wardrobe, following the usual dress code (yellow for haldi, green for mehendi...), without repeating a single garment."
      />
      <div className="trip-layout">
        <form className="style-form trip-form" onSubmit={submit}>
          <fieldset className="field">
            <legend>Your functions, in order</legend>
            {chosen.length === 0 && <p className="muted">Add at least one function below.</p>}
            <ol className="function-list">
              {chosen.map((key, i) => (
                <li key={`${key}-${i}`}>
                  <span><b>{byKey[key]?.label || key}</b><small>{byKey[key]?.dress_code}</small></span>
                  <button type="button" className="icon-btn" onClick={() => remove(i)} aria-label={`Remove ${byKey[key]?.label || key}`}><X size={13} /></button>
                </li>
              ))}
            </ol>
          </fieldset>
          <fieldset className="field">
            <legend>Add a function</legend>
            <div className="chips">
              {(functions || []).map((f) => (
                <button type="button" key={f.key} onClick={() => add(f.key)} disabled={chosen.length >= 10}><Plus size={10} /> {f.label}</button>
              ))}
            </div>
            <button type="button" className="text-btn" onClick={() => setChosen(FULL_WEDDING)}>Reset to a full wedding (haldi to reception)</button>
          </fieldset>
          <fieldset className="field">
            <legend>Style</legend>
            <div className="chips">
              {STYLES.map((s) => (
                <button type="button" key={s || 'any'} className={style === s ? 'chosen' : ''} aria-pressed={style === s} onClick={() => setStyle(s)}>{s || 'As usual for each'}</button>
              ))}
            </div>
          </fieldset>
          <button className="primary" disabled={busy || !chosen.length || !functions}>
            {busy ? <><RefreshCw size={15} className="spin" /> Planning…</> : <><Sparkles size={15} /> Plan my looks</>}
          </button>
          {error && <p className="form-error">{error}</p>}
          <p className="muted small-note">Dress codes are common customs, used as gentle preferences. Every look uses only your own pieces.</p>
        </form>

        <div className="trip-result">
          {!plan ? (
            <div className="empty">
              <div><Gem /></div>
              <h3>A look for every function</h3>
              <p>Choose your functions on the left and press <b>Plan my looks</b>. Tag festive and wedding pieces in My Wardrobe for the best results.</p>
            </div>
          ) : <PlanResult plan={plan} goToWardrobe={goToWardrobe} events />}
        </div>
      </div>
    </>
  );
}
