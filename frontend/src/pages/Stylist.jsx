import React, { useEffect, useRef, useState } from 'react';
import { Sparkles, RefreshCw, Plus, Info } from 'lucide-react';
import { api } from '../api.js';
import Heading from '../components/Heading.jsx';
import OutfitCard from '../components/OutfitCard.jsx';
import AskBox from '../components/AskBox.jsx';

// Chips for picking one value. '' means "Any".
function ChoiceChips({ label, value, choices, onChange, allowAny = true }) {
  return (
    <fieldset className="field">
      <legend>{label}</legend>
      <div className="chips">
        {(allowAny ? ['', ...choices] : choices).map((c) => (
          <button type="button" key={c || 'any'} className={value === c ? 'chosen' : ''} aria-pressed={value === c} onClick={() => onChange(c)}>
            {c || 'Any'}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

export default function Stylist({ anchorId, goToWardrobe }) {
  const [options, setOptions] = useState(null);
  const [items, setItems] = useState([]);
  const [loadError, setLoadError] = useState('');
  const [form, setForm] = useState({
    occasion: '', style: '', colour: '', colour_mood: '', comfort: '', anchor_item_id: anchorId ?? '',
  });
  const [status, setStatus] = useState('idle'); // 'idle' | 'loading' | 'done' | 'error'
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [chat, setChat] = useState(null); // the last typed request and what Adaa understood
  const [asking, setAsking] = useState(false);
  const resultsRef = useRef(null);

  const loadWardrobe = () => {
    setLoadError('');
    Promise.all([api.getOptions(), api.listItems()])
      .then(([opts, list]) => { setOptions(opts); setItems(list); })
      .catch((err) => setLoadError(err.message));
  };
  useEffect(loadWardrobe, []);

  const set = (key, value) => setForm((f) => ({ ...f, [key]: value }));
  const anchor = items.find((i) => i.id === Number(form.anchor_item_id));

  const runStyle = async (values) => {
    if (!values.occasion) return;
    setStatus('loading');
    setError('');
    try {
      const data = await api.recommend({
        ...values,
        anchor_item_id: values.anchor_item_id === '' ? null : Number(values.anchor_item_id),
      });
      setResult(data);
      setStatus('done');
      // On narrow screens the results are below the form, so bring them into view.
      if (window.innerWidth < 1050) resultsRef.current?.scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
      setError(err.message);
      setStatus('error');
    }
  };

  const submit = (e) => {
    e.preventDefault();
    runStyle(form);
  };

  // A typed request: read it into the form, then style straight away if we know the occasion.
  const ask = async (text) => {
    setAsking(true);
    try {
      const parsed = await api.parseRequest(text);
      const fromText = {
        occasion: parsed.occasion ?? '', style: parsed.style ?? '', colour: parsed.colour ?? '',
        colour_mood: parsed.colour_mood ?? '', comfort: parsed.comfort ?? '',
        anchor_item_id: parsed.anchor_item_id != null ? String(parsed.anchor_item_id) : '',
      };
      // No occasion in the message but one already chosen? Treat it as a follow-up
      // ("make it more comfortable") and only change what the message mentions.
      const refining = !parsed.occasion && Boolean(form.occasion);
      const next = refining
        ? { ...form, ...Object.fromEntries(Object.entries(fromText).filter(([, v]) => v !== '')) }
        : fromText;
      setForm(next);
      setChat({ text, parsed, refining, keptOccasion: refining ? form.occasion : '' });
      if (next.occasion) runStyle(next);
      else setStatus('idle');
    } catch (err) {
      setChat({ text, error: err.message });
    } finally {
      setAsking(false);
    }
  };

  const pickAmbiguous = (id) => {
    const next = { ...form, anchor_item_id: String(id) };
    setForm(next);
    setChat((c) => ({ ...c, parsed: { ...c.parsed, ambiguous: [] }, picked: items.find((i) => i.id === id)?.name }));
    runStyle(next);
  };

  const heading = (
    <Heading
      eyebrow="YOUR PERSONAL STYLE COMPANION"
      title={<>Let's find your <em>kind of lovely.</em></>}
      sub="Tell Adaa what you need, or pick the details yourself. Every look uses only pieces from your wardrobe."
    />
  );

  if (loadError) {
    return <>{heading}<div className="empty"><div>!</div><h3>Couldn't load your wardrobe</h3><p>{loadError}</p>
      <button className="primary" onClick={loadWardrobe}><RefreshCw size={15} /> Try again</button></div></>;
  }
  if (!options) return <>{heading}<p className="muted">Loading your wardrobe…</p></>;
  if (items.length === 0) {
    return <>{heading}<div className="empty"><div><Sparkles size={34} /></div><h3>Your stylist needs a wardrobe first</h3>
      <p>Add a few pieces (clothes, footwear, jewellery) and Adaa will style them for you.</p>
      <button className="primary" onClick={goToWardrobe}><Plus size={15} /> Add pieces</button></div></>;
  }

  const categories = [...new Set(items.map((i) => i.category))];

  return (
    <>
      {heading}
      <AskBox items={items} chat={chat} asking={asking} onAsk={ask} onPick={pickAmbiguous} />
      <div className="stylist-layout">
        <form className="style-form" onSubmit={submit}>
          <ChoiceChips label="Where are you going?" value={form.occasion} choices={options.occasions} allowAny={false} onChange={(v) => set('occasion', v)} />

          <label className="field">
            <span>Build around a piece <i>(optional)</i></span>
            <div className="anchor-pick">
              {anchor && <img src={anchor.image_url} alt="" />}
              <select value={form.anchor_item_id} onChange={(e) => set('anchor_item_id', e.target.value)}>
                <option value="">No, surprise me</option>
                {categories.map((c) => (
                  <optgroup key={c} label={c}>
                    {items.filter((i) => i.category === c).map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
                  </optgroup>
                ))}
              </select>
            </div>
          </label>

          <ChoiceChips label="Style" value={form.style} choices={options.styles} onChange={(v) => set('style', v)} />

          <label className="field">
            <span>Favourite colour <i>(optional)</i></span>
            <input value={form.colour} maxLength={40} onChange={(e) => set('colour', e.target.value)} placeholder="e.g. green" />
          </label>

          <ChoiceChips label="Colour mood" value={form.colour_mood} choices={options.colour_moods} onChange={(v) => set('colour_mood', v)} />
          <ChoiceChips label="Comfort" value={form.comfort} choices={options.comfort_levels} onChange={(v) => set('comfort', v)} />

          <button className="primary style-btn" disabled={!form.occasion || status === 'loading'}>
            <Sparkles size={16} /> {status === 'loading' ? 'Styling…' : 'Style me'}
          </button>
          {!form.occasion && <p className="muted hint">Pick an occasion to begin{anchor ? ` styling your ${anchor.name}` : ''}.</p>}
        </form>

        <section className="results" ref={resultsRef} aria-live="polite">
          {status === 'idle' && (
            <div className="tip">
              <small>HOW IT WORKS</small>
              <h3>Looks from your own wardrobe.</h3>
              <p>Choose an occasion and any preferences, then press <b>Style me</b>. Adaa suggests up to four different outfits, explains why each works, and tells you honestly if something is missing.</p>
              <div className="tip-art">✧</div>
            </div>
          )}

          {status === 'loading' && <p className="muted">Putting your looks together…</p>}

          {status === 'error' && <p className="form-error" role="alert">{error}</p>}

          {status === 'done' && result && (
            <>
              {result.notes.length > 0 && (
                <div className={'notes' + (result.relaxed ? ' relaxed' : '')}>
                  <Info size={17} />
                  <ul>{result.notes.map((n) => <li key={n}>{n}</li>)}</ul>
                </div>
              )}
              {result.outfits.length === 0 ? (
                <div className="empty">
                  <div><Sparkles size={30} /></div>
                  <h3>No complete outfit yet</h3>
                  <p>Adaa only uses pieces you own, and it couldn't build a full look for this request.</p>
                  <button className="primary" onClick={goToWardrobe}><Plus size={15} /> Add pieces</button>
                </div>
              ) : (
                <div className="outfits">
                  {result.outfits.map((o) => <OutfitCard key={o.rank} outfit={o} />)}
                </div>
              )}
            </>
          )}
        </section>
      </div>
    </>
  );
}
