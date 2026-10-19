import React, { useEffect, useRef, useState } from 'react';
import { Sparkles, RefreshCw, Plus, Info, Heart, Check, CloudSun, Shirt, X } from 'lucide-react';
import { api } from '../api.js';
import Heading from '../components/Heading.jsx';
import OutfitCard from '../components/OutfitCard.jsx';
import AskBox from '../components/AskBox.jsx';
import SwapPanel from '../components/SwapPanel.jsx';
import { loadPreferences, toStylistDefaults } from '../preferences.js';
import { useTodayWeather, styleHint } from '../weather.js';

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

const prefsOf = ({ occasion, style, colour, colour_mood, comfort, festival }) => ({ occasion, style, colour, colour_mood, comfort, festival: festival || null });
const idsOf = (outfit) => outfit.pieces.map((p) => p.item.id);

export default function Stylist({ anchorId, preset, goToWardrobe, goToPreferences, notify, onLookSaved }) {
  const [options, setOptions] = useState(null);
  const [items, setItems] = useState([]);
  const [loadError, setLoadError] = useState('');
  // Start from the preferences saved on the Preferences page (if any).
  const [savedPrefs] = useState(() => toStylistDefaults(loadPreferences()));
  const [form, setForm] = useState({
    occasion: '', style: '', colour: '', colour_mood: '', comfort: '', ...savedPrefs, anchor_item_id: anchorId ?? '',
    festival: '', festival_label: '',   // a festival brings its usual colours (e.g. Republic Day: saffron, white, green)
    ...(preset ? {
      occasion: preset.occasion, colour: preset.colour, style: preset.style ?? '',
      festival: preset.festival ?? '', festival_label: preset.reason ?? '',
    } : {}),
  });
  const [status, setStatus] = useState('idle'); // 'idle' | 'loading' | 'done' | 'error'
  const [result, setResult] = useState(null);
  const [resultPrefs, setResultPrefs] = useState(null); // the preferences these results were made for
  const [saved, setSaved] = useState({});               // outfit rank -> saved look id
  const [worn, setWorn] = useState({});                 // outfit rank -> logged as worn today
  // Today's weather for your saved city (Preferences), as a gentle nudge. Can be switched off.
  const { place, weather, error: weatherError } = useTodayWeather();
  const [useWeather, setUseWeather] = useState(true);
  const [swapping, setSwapping] = useState(null);       // { rank, piece } while the swap panel is open
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
      const wx = useWeather && weather ? { temp_c: weather.temp_c, rain: weather.rain, label: weather.label } : null;
      const { festival_label: _label, ...request } = values;
      const data = await api.recommend({
        ...request,
        festival: values.festival || null,
        weather: wx,
        anchor_item_id: values.anchor_item_id === '' ? null : Number(values.anchor_item_id),
      });
      setResult(data);
      setResultPrefs({ ...prefsOf(values), weather: wx });
      setSaved({});
      setWorn({});
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

  // Opened with a preset (e.g. "Style me in peacock green" for today's festival): style straight away,
  // once today's weather is known (if a city is set).
  const presetDone = useRef(false);
  const weatherSettled = !place || Boolean(weather) || Boolean(weatherError);
  useEffect(() => {
    if (preset && options && weatherSettled && !presetDone.current) {
      presetDone.current = true;
      runStyle(form);
    }
  }, [preset, options, weatherSettled]); // eslint-disable-line react-hooks/exhaustive-deps

  // A typed request: read it into the form, then style straight away if we know the occasion.
  const ask = async (text) => {
    setAsking(true);
    try {
      const parsed = await api.parseRequest(text);
      const fromText = {
        occasion: parsed.occasion ?? '', style: parsed.style ?? '', colour: parsed.colour ?? '',
        colour_mood: parsed.colour_mood ?? '', comfort: parsed.comfort ?? '',
        anchor_item_id: parsed.anchor_item_id != null ? String(parsed.anchor_item_id) : '',
        festival: parsed.festival ?? '',
        festival_label: (parsed.understood.find((u) => u.startsWith('Festival: ')) || '').replace('Festival: ', ''),
      };
      // No occasion in the message but one already chosen? Treat it as a follow-up
      // ("make it more comfortable") and only change what the message mentions.
      const refining = !parsed.occasion && Boolean(form.occasion);
      const typed = Object.fromEntries(Object.entries(fromText).filter(([, v]) => v !== ''));
      const next = refining
        ? { ...form, ...typed }
        : { ...fromText, ...savedPrefs, ...typed }; // what you typed beats saved preferences
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

  const saveLook = async (outfit) => {
    try {
      const look = await api.saveLook(resultPrefs, idsOf(outfit));
      setSaved((s) => ({ ...s, [outfit.rank]: look.id }));
      onLookSaved?.();
      notify(`Saved "${look.name}" to your looks.`);
    } catch (err) {
      notify(err.message);
    }
  };

  const woreIt = async (outfit) => {
    try {
      await api.wearOutfit(idsOf(outfit), resultPrefs.occasion);
      setWorn((w) => ({ ...w, [outfit.rank]: true }));
      notify('Added to your outfit history. It counts in your wear stats.');
    } catch (err) {
      notify(err.message);
    }
  };

  // Replace one piece, then ask the engine to re-explain the outfit.
  const swapPiece = async (option) => {
    const { rank, piece } = swapping;
    setSwapping(null);
    const outfit = result.outfits.find((o) => o.rank === rank);
    const ids = idsOf(outfit).map((id) => (id === piece.item.id ? option.item.id : id));
    const update = (changes) =>
      setResult((r) => ({ ...r, outfits: r.outfits.map((o) => (o.rank === rank ? { ...o, ...changes } : o)) }));
    setSaved((s) => ({ ...s, [rank]: undefined }));
    try {
      const updated = await api.evaluateOutfit(resultPrefs, ids);
      update({ ...updated, outdated: false });
      notify(`Swapped in ${option.item.name}.`);
    } catch (err) {
      // Keep the piece you chose; only the explanation couldn't be refreshed.
      update({
        pieces: outfit.pieces.map((p) => (p.item.id === piece.item.id ? { role: option.role, item: option.item } : p)),
        outdated: true,
      });
      notify(`Swapped in ${option.item.name}, but the reasons couldn't be refreshed: ${err.message}`);
    }
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
          {form.festival && (
            <p className="festival-chip">
              <span>✦ {form.festival_label || 'Festival'} · its usual colours are preferred</span>
              <button type="button" className="icon-btn" aria-label="Don't style for this festival"
                onClick={() => setForm((f) => ({ ...f, festival: '', festival_label: '' }))}><X size={12} /></button>
            </p>
          )}
          {place ? (
            <div className={`weather-chip ${useWeather ? '' : 'off'}`}>
              <CloudSun size={17} />
              <span>
                <b>{weather ? `Today: ${weather.label}` : weatherError || "Checking today's weather…"}</b>
                {weather && <small>{useWeather ? styleHint(weather) : 'Not using the weather'}</small>}
              </span>
              {weather && (
                <label className="weather-toggle">
                  <input type="checkbox" checked={useWeather} onChange={(e) => setUseWeather(e.target.checked)} /> Use
                </label>
              )}
            </div>
          ) : (
            <p className="weather-chip quiet"><CloudSun size={15} /> <span>Add your city in <button type="button" className="text-btn" onClick={goToPreferences}>Preferences</button> to dress for today's weather.</span></p>
          )}
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
                  {result.outfits.map((o) => (
                    <OutfitCard
                      key={o.rank}
                      outfit={o}
                      onSwap={(piece) => setSwapping({ rank: o.rank, piece })}
                      notice={o.outdated ? "Couldn't re-check this look after your swap, so the reasons below may be outdated. Try another swap or Style me again." : null}
                      actions={<>
                        {saved[o.rank]
                          ? <button className="secondary" disabled><Check size={14} /> Saved to your looks</button>
                          : <button className="secondary" onClick={() => saveLook(o)}><Heart size={14} /> Save look</button>}
                        {worn[o.rank]
                          ? <button className="secondary" disabled><Check size={14} /> Worn today</button>
                          : <button className="secondary" onClick={() => woreIt(o)}><Shirt size={14} /> Wore it today</button>}
                      </>}
                    />
                  ))}
                </div>
              )}
            </>
          )}
        </section>
      </div>

      {swapping && (
        <SwapPanel
          prefs={resultPrefs}
          itemIds={idsOf(result.outfits.find((o) => o.rank === swapping.rank))}
          piece={swapping.piece}
          onPick={swapPiece}
          onClose={() => setSwapping(null)}
        />
      )}
    </>
  );
}
