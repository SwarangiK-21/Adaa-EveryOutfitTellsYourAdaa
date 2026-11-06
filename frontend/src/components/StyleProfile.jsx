import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Check, RefreshCw, Sparkles, X, Ruler, Palette } from 'lucide-react';
import { api } from '../api.js';
import { useUser } from '../user.js';
import { swatchFor } from './OutfitPreview.jsx';

/*
  The optional style profile: height, body shape (chosen by you, never guessed), preferred fit,
  skin undertone, styles you usually skip, colours you love or avoid, and gender (only to hide shop
  ideas you'd never wear). Every question can be skipped. Adaa uses the answers to rank outfits and
  explain "why it suits you"; it never hides your clothes because of them.
*/

const SHAPES = [
  // value, label, hint, [shoulders, waist, hips] widths for the little outline
  ['hourglass', 'Hourglass', 'Shoulders and hips about even, defined waist', [34, 20, 34]],
  ['pear', 'Pear', 'Hips wider than shoulders', [24, 20, 38]],
  ['apple', 'Apple', 'Fuller middle, slimmer legs', [30, 36, 28]],
  ['rectangle', 'Rectangle', 'Shoulders, waist and hips about even', [30, 28, 30]],
  ['inverted_triangle', 'Inverted triangle', 'Shoulders wider than hips', [40, 26, 24]],
];
const FITS = [['fitted', 'Fitted'], ['regular', 'Regular'], ['relaxed', 'Relaxed']];
const UNDERTONES = [['warm', 'Warm'], ['cool', 'Cool'], ['neutral', 'Neutral']];
const GENDERS = [['woman', 'Woman'], ['man', 'Man'], ['non_binary', 'Non-binary']];
const AVOID = [['sleeveless', 'Sleeveless'], ['short_hemlines', 'Short hemlines'], ['bodycon', 'Bodycon'], ['crop_tops', 'Crop tops']];
const COLOURS = ['black', 'white', 'cream', 'beige', 'grey', 'navy', 'brown', 'red', 'maroon', 'pink', 'peach', 'orange',
  'mustard', 'yellow', 'olive', 'green', 'emerald', 'teal', 'blue', 'sky blue', 'lavender', 'purple'];
const MAX_COLOURS = 8;

const EMPTY = { height_cm: null, body_shape: null, fit: null, undertone: null, gender: null, avoid: [], love_colours: [], avoid_colours: [] };

function ShapeOutline({ widths: [s, w, h] }) {
  const c = 30;
  const points = [[c - s / 2, 8], [c + s / 2, 8], [c + w / 2, 30], [c + h / 2, 50], [c + h / 2 - 4, 62],
    [c - h / 2 + 4, 62], [c - h / 2, 50], [c - w / 2, 30]].map((p) => p.join(',')).join(' ');
  return <svg viewBox="0 0 60 68" width="40" height="46" aria-hidden="true"><polygon points={points} /></svg>;
}

// One-choice buttons with a "no answer" option (clicking the chosen one again clears it).
function Choice({ label, options, value, onChange, none = 'Not sure' }) {
  return (
    <fieldset className="field profile-choice">
      <legend>{label}</legend>
      <div className="chips">
        {options.map(([v, text]) => (
          <button type="button" key={v} className={value === v ? 'chosen' : ''} aria-pressed={value === v}
            onClick={() => onChange(value === v ? null : v)}>{text}</button>
        ))}
        <button type="button" className={value == null ? 'chosen' : ''} aria-pressed={value == null} onClick={() => onChange(null)}>{none}</button>
      </div>
    </fieldset>
  );
}

function ColourPicker({ label, value, other, onChange }) {
  const toggle = (c) => onChange(value.includes(c) ? value.filter((x) => x !== c) : value.length < MAX_COLOURS ? [...value, c] : value);
  return (
    <fieldset className="field">
      <legend>{label} <i>(up to {MAX_COLOURS})</i></legend>
      <div className="colour-chips">
        {COLOURS.filter((c) => !other.includes(c)).map((c) => (
          <button type="button" key={c} className={value.includes(c) ? 'chosen' : ''} aria-pressed={value.includes(c)} onClick={() => toggle(c)}>
            <span style={{ background: swatchFor(c) }} aria-hidden="true" />{c}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

function Height({ value, onChange }) {
  const [unit, setUnit] = useState('cm');
  const totalInches = value ? Math.round(value / 2.54) : 0;   // 152 cm -> 60 in -> 5 ft 0 in
  const feet = value ? Math.floor(totalInches / 12) : '';
  const inches = value ? totalInches % 12 : '';
  const fromFeet = (f, i) => {
    const cm = Math.round((Number(f) || 0) * 30.48 + (Number(i) || 0) * 2.54);
    onChange(cm || null);
  };
  return (
    <fieldset className="field height-field">
      <legend>Height <i>(optional)</i></legend>
      <div className="height-row">
        {unit === 'cm' ? (
          <label><input type="number" inputMode="numeric" min="120" max="220" value={value ?? ''} placeholder="e.g. 160"
            onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)} aria-label="Height in centimetres" /> cm</label>
        ) : (
          <>
            <label><input type="number" inputMode="numeric" min="4" max="7" value={feet} placeholder="5"
              onChange={(e) => fromFeet(e.target.value, inches)} aria-label="Feet" /> ft</label>
            <label><input type="number" inputMode="numeric" min="0" max="11" value={inches} placeholder="3"
              onChange={(e) => fromFeet(feet, e.target.value)} aria-label="Inches" /> in</label>
          </>
        )}
        <button type="button" className="text-btn" onClick={() => setUnit(unit === 'cm' ? 'ft' : 'cm')}>
          Use {unit === 'cm' ? 'feet and inches' : 'centimetres'}
        </button>
      </div>
    </fieldset>
  );
}

function AboutYou({ p, set }) {
  return (
    <>
      <Height value={p.height_cm} onChange={(v) => set({ height_cm: v })} />
      <fieldset className="field">
        <legend>Body shape <i>(pick what feels closest, or skip)</i></legend>
        <div className="shape-grid">
          {SHAPES.map(([v, label, hint, widths]) => (
            <button type="button" key={v} className={`shape-card${p.body_shape === v ? ' chosen' : ''}`} aria-pressed={p.body_shape === v}
              aria-label={`${label}: ${hint}`} onClick={() => set({ body_shape: p.body_shape === v ? null : v })}>
              <ShapeOutline widths={widths} /><b>{label}</b><small>{hint}</small>
            </button>
          ))}
          <button type="button" className={`shape-card${p.body_shape == null ? ' chosen' : ''}`} aria-pressed={p.body_shape == null}
            onClick={() => set({ body_shape: null })}><b>Not sure</b><small>That's fine: Adaa still styles you</small></button>
        </div>
      </fieldset>
      <Choice label="Fit you prefer" options={FITS} value={p.fit} onChange={(v) => set({ fit: v })} none="No preference" />
      <Choice label="Gender (optional, only hides shop ideas you'd never wear)" options={GENDERS} value={p.gender}
        onChange={(v) => set({ gender: v })} none="Prefer not to say" />
    </>
  );
}

function ColoursAndComfort({ p, set }) {
  const toggleAvoid = (v) => set({ avoid: p.avoid.includes(v) ? p.avoid.filter((x) => x !== v) : [...p.avoid, v] });
  return (
    <>
      <Choice label="Skin undertone" options={UNDERTONES} value={p.undertone} onChange={(v) => set({ undertone: v })} />
      <p className="muted small-note">Not sure? In daylight, veins on your wrist look greenish for warm, bluish or purple for cool, and a bit of both for neutral. Or: if gold jewellery suits you best, warm; silver, cool. It only suggests colours that tend to glow on you, never what you can't wear.</p>
      <fieldset className="field">
        <legend>Styles you usually skip</legend>
        <div className="chips">
          {AVOID.map(([v, text]) => (
            <button type="button" key={v} className={p.avoid.includes(v) ? 'chosen' : ''} aria-pressed={p.avoid.includes(v)} onClick={() => toggleAvoid(v)}>{text}</button>
          ))}
        </div>
      </fieldset>
      <ColourPicker label="Colours you love" value={p.love_colours} other={p.avoid_colours} onChange={(v) => set({ love_colours: v })} />
      <ColourPicker label="Colours you'd rather avoid" value={p.avoid_colours} other={p.love_colours} onChange={(v) => set({ avoid_colours: v })} />
    </>
  );
}

// Only the profile questions on this screen (the Preferences page keeps style/comfort/colour mood separately).
const pick = (saved) => ({ ...EMPTY, ...Object.fromEntries(Object.entries(saved || {}).filter(([k]) => k in EMPTY)) });
const validHeight = (h) => h == null || (h >= 120 && h <= 220);

/* After sign-up: two short steps, skippable at any point. Shown once per account. */
export function StyleProfileSetup({ initial, notify, onDone }) {
  const { first } = useUser();
  const [p, setP] = useState(pick(initial));
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const set = (patch) => setP((cur) => ({ ...cur, ...patch }));

  const finish = async (skip) => {
    if (!skip && !validHeight(p.height_cm)) { setStep(1); setError('Please enter a height between 120 and 220 cm, or leave it empty.'); return; }
    setBusy(true);
    try {
      await api.saveStyleProfile(skip ? { onboarded: true } : { ...pick(p), onboarded: true });
      if (!skip) notify(`Thank you, ${first}! Your looks will now say why they suit you.`);
      onDone();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return createPortal(
    <div className="modal-backdrop">
      <form className="modal profile-setup" role="dialog" aria-modal="true" aria-labelledby="profile-title" onSubmit={(e) => { e.preventDefault(); step === 1 ? setStep(2) : finish(false); }}>
        <div className="modal-head">
          <div>
            <small>STEP {step} OF 2 · ALL OPTIONAL</small>
            <h2 id="profile-title">{step === 1 ? <>Help Adaa style you, {first}</> : 'Colours and comfort'}</h2>
          </div>
          <button type="button" className="icon-btn" onClick={() => finish(true)} aria-label="Skip for now"><X size={18} /></button>
        </div>
        <div className="profile-body">
          <p className="muted">Answer what you like and skip the rest. It's used only to pick and explain your outfits; change or clear it any time in Preferences.</p>
          {step === 1 ? <AboutYou p={p} set={set} /> : <ColoursAndComfort p={p} set={set} />}
          {error && <p className="form-error" role="alert">{error}</p>}
        </div>
        <div className="modal-actions">
          <button type="button" className="text-btn" onClick={() => finish(true)} disabled={busy}>Skip for now</button>
          {step === 2 && <button type="button" className="secondary" onClick={() => setStep(1)}>Back</button>}
          <button className="primary" disabled={busy}>
            {busy ? <RefreshCw size={15} className="spin" /> : step === 1 ? <Ruler size={15} /> : <Check size={15} />}
            {step === 1 ? 'Next' : 'Save my profile'}
          </button>
        </div>
      </form>
    </div>,
    document.body,
  );
}

/* Preferences section: the same questions on one page, with Save and Clear. */
export function StyleProfileSettings({ notify }) {
  const { first } = useUser();
  const [saved, setSaved] = useState(null);
  const [p, setP] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    api.getStyleProfile().then((s) => { setSaved(s); setP(pick(s)); }).catch((err) => setError(err.message));
  }, []);
  const set = (patch) => setP((cur) => ({ ...cur, ...patch }));

  const save = async (next) => {
    if (!validHeight(next.height_cm)) { setError('Please enter a height between 120 and 220 cm, or leave it empty.'); return; }
    setBusy(true);
    setError('');
    try {
      const s = await api.saveStyleProfile({ ...pick(next), onboarded: true });
      setSaved(s);
      setP(pick(s));
      notify(`Saved, ${first}. Your next looks will use it.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  if (!saved && !error) return <section className="style-profile"><h3>Your style profile</h3><p className="muted"><RefreshCw size={13} className="spin" /> Loading…</p></section>;
  return (
    <section className="style-profile">
      <h3><Sparkles size={15} /> Your style profile <small>(all optional)</small></h3>
      <p className="muted">Used only to pick and explain your outfits ("why it suits you"). It never hides your clothes.</p>
      <h4><Ruler size={14} /> About you</h4>
      <AboutYou p={p} set={set} />
      <h4><Palette size={14} /> Colours and comfort</h4>
      <ColoursAndComfort p={p} set={set} />
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="account-actions">
        <button type="button" className="primary" disabled={busy} onClick={() => save(p)}>
          {busy ? <RefreshCw size={14} className="spin" /> : <Check size={14} />} Save style profile
        </button>
        <button type="button" className="secondary" disabled={busy} onClick={() => save(EMPTY)}>Clear all</button>
      </div>
    </section>
  );
}
