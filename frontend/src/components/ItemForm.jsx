import React, { useEffect, useRef, useState } from 'react';
import { ImagePlus, X, Check, Sparkles, RefreshCw } from 'lucide-react';
import { api } from '../api.js';
import CutoutEditor from './CutoutEditor.jsx';
import { forgetCutout, queueMissingCutouts } from '../cutoutQueue.js';

const MAX_PHOTO_MB = 5;
const PHOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const COLOUR_SUGGESTIONS = [
  'Black', 'White', 'Ivory', 'Cream', 'Beige', 'Brown', 'Tan', 'Grey', 'Navy', 'Blue',
  'Sky blue', 'Denim', 'Teal', 'Green', 'Sage', 'Olive', 'Mustard', 'Yellow', 'Orange', 'Peach',
  'Red', 'Maroon', 'Pink', 'Baby pink', 'Rose', 'Lemon', 'Bottle green', 'Lavender', 'Purple', 'Gold', 'Silver', 'Multicolour',
];

const emptyFields = (options) => ({
  name: '',
  category: options.categories[0],
  item_type: '',
  colour: '',
  style: options.styles[0],
  occasions: [],
  notes: '',
  price: '',
});

// Add a new wardrobe item (item = null) or edit an existing one.
export default function ItemForm({ options, item, onClose, onSaved, notify }) {
  const isEdit = Boolean(item);
  const [initialFields] = useState(() =>
    isEdit
      ? {
          name: item.name, category: item.category, item_type: item.item_type,
          colour: item.colour, style: item.style, occasions: item.occasions, notes: item.notes,
          price: item.price ?? '',
        }
      : emptyFields(options),
  );
  const [fields, setFields] = useState(initialFields);
  const [photo, setPhoto] = useState(null);
  const [preview, setPreview] = useState(isEdit ? item.image_url : '');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  // Reading a new photo to suggest category, type, colour and name: null | { status, text }
  const [autoFill, setAutoFill] = useState(null);
  const touched = useRef(new Set());   // fields the user typed or picked: never overwritten
  const photoRun = useRef(0);
  const firstField = useRef(null);

  const hasChanges = photo !== null || JSON.stringify(fields) !== JSON.stringify(initialFields);

  // Escape and clicking outside are easy to do by accident, so ask before losing changes.
  const closeSafely = () => {
    if (!hasChanges || window.confirm('Discard your changes to this piece?')) onClose();
  };
  const closeSafelyRef = useRef(closeSafely);
  closeSafelyRef.current = closeSafely;

  useEffect(() => firstField.current?.focus(), []);

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && closeSafelyRef.current();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // Free the temporary preview URL when it is replaced or the form closes.
  useEffect(() => () => preview.startsWith('blob:') && URL.revokeObjectURL(preview), [preview]);

  const set = (key, value) => {
    touched.current.add(key);
    setFields((f) => ({ ...f, [key]: value }));
  };
  // Read the latest occasions inside the update, so quick taps never undo each other.
  const toggleOccasion = (o) =>
    setFields((f) => ({
      ...f,
      occasions: f.occasions.includes(o) ? f.occasions.filter((x) => x !== o) : [...f.occasions, o],
    }));

  const choosePhoto = async (e) => {
    const file = e.target.files[0];
    e.target.value = '';
    if (!file) return;
    if (!PHOTO_TYPES.includes(file.type)) {
      setError('Please choose a JPEG, PNG or WebP photo. (iPhone HEIC photos: export as JPEG first.)');
      return;
    }
    if (file.size > MAX_PHOTO_MB * 1024 * 1024) {
      setError(`That photo is larger than ${MAX_PHOTO_MB} MB. Please choose a smaller one.`);
      return;
    }
    // Make sure the browser can actually show it (a renamed text file can't be decoded).
    const url = URL.createObjectURL(file);
    try {
      const img = new Image();
      img.src = url;
      await img.decode();
    } catch {
      URL.revokeObjectURL(url);
      setError("That file doesn't look like a real photo. Please choose another one.");
      return;
    }
    setError('');
    setPhoto(file);
    setPreview(url);
    if (!isEdit) readPhoto(url);
  };

  // Suggest the details from the photo (clothes parser, in the browser). Only empty or untouched
  // fields are filled, and the user can change anything.
  const readPhoto = async (url) => {
    const run = ++photoRun.current;
    setAutoFill({ status: 'reading' });
    try {
      const { analysePhoto } = await import('../cutout.js');
      const found = await analysePhoto(url);
      if (run !== photoRun.current) return;   // a newer photo was chosen meanwhile
      if (!found) { setAutoFill({ status: 'none' }); return; }
      setFields((f) => {
        const next = { ...f };
        const fill = (key, value) => { if (value && !touched.current.has(key)) next[key] = value; };
        fill('category', found.category);
        fill('item_type', found.item_type);
        fill('colour', found.colour);
        fill('style', found.style);
        if (!touched.current.has('name') && !f.name.trim() && found.colour) {
          next.name = `${found.colour} ${found.item_type.toLowerCase()}`;
        }
        return next;
      });
      setAutoFill({ status: 'done', text: [found.category, found.item_type, found.colour].filter(Boolean).join(' · ') });
    } catch {
      if (run === photoRun.current) setAutoFill({ status: 'none' });
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!isEdit && !photo) return setError('Please add a photo of this piece.');
    if (!fields.name.trim() || !fields.item_type.trim() || !fields.colour.trim()) {
      return setError('Please fill in the name, type and colour.');
    }
    if (fields.occasions.length === 0) return setError('Please pick at least one occasion.');

    setSaving(true);
    setError('');
    try {
      const saved = isEdit
        ? await api.updateItem(item.id, fields, photo)
        : await api.createItem(fields, photo);
      if (photo) { forgetCutout(saved.id); queueMissingCutouts([saved]); }
      onSaved(saved, !isEdit);
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  };

  const typeSuggestions = options.item_type_suggestions[fields.category] || [];

  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && closeSafely()}>
      <form className="modal item-form" role="dialog" aria-modal="true" aria-labelledby="item-form-title" onSubmit={submit}>
        <div className="modal-head">
          <div>
            <small>{isEdit ? 'UPDATE THIS PIECE' : 'ADD TO YOUR WARDROBE'}</small>
            <h2 id="item-form-title">{isEdit ? 'Edit piece' : 'Add a piece'}</h2>
          </div>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close"><X size={18} /></button>
        </div>

        <div className="form-body">
          <div className="photo-col">
            <label className="photo-pick">
              {preview ? <img src={preview} alt="Selected piece" /> : (
                <span><ImagePlus size={26} /><b>Add a photo</b><small>JPEG, PNG or WebP · up to {MAX_PHOTO_MB} MB</small></span>
              )}
              {preview && <em>Change photo</em>}
              <input type="file" accept="image/jpeg,image/png,image/webp" onChange={choosePhoto} />
            </label>
            {/* Outfit boards are made from this photo, so a clean photo gives the best looks. */}
            <div className="photo-tips">
              <b>For the best outfit pictures</b>
              <ul>
                <li className="good">Just the garment, laid flat or against a plain wall</li>
                <li className="good">Plain, light background and good light</li>
                <li className="good">The whole garment in the frame</li>
                <li className="avoid">Avoid hangers, people wearing it and other clothes in the shot</li>
              </ul>
            </div>
            {autoFill?.status === 'reading' && (
              <p className="autofill"><RefreshCw size={12} className="spin" /> Reading your photo…</p>
            )}
            {autoFill?.status === 'done' && (
              <p className="autofill"><Sparkles size={12} /> Filled in from your photo: <b>{autoFill.text}</b>. Please check and change anything that's off.</p>
            )}
            {autoFill?.status === 'none' && (
              <p className="autofill quiet">Adaa couldn't tell what this is from the photo (it recognises clothes, shoes and bags, not jewellery yet). Please fill in the details.</p>
            )}
          </div>

          <div className="form-fields">
            <label className="field">
              <span>Name</span>
              <input ref={firstField} value={fields.name} maxLength={80} onChange={(e) => set('name', e.target.value)} placeholder="e.g. Green chikankari kurta" />
            </label>

            <div className="field-row">
              <label className="field">
                <span>Category</span>
                <select value={fields.category} onChange={(e) => set('category', e.target.value)}>
                  {options.categories.map((c) => <option key={c}>{c}</option>)}
                </select>
              </label>
              <label className="field">
                <span>Type</span>
                <input list="type-suggestions" value={fields.item_type} maxLength={40} onChange={(e) => set('item_type', e.target.value)} placeholder="e.g. Kurta" />
                <datalist id="type-suggestions">{typeSuggestions.map((t) => <option key={t} value={t} />)}</datalist>
              </label>
            </div>

            <div className="field-row">
              <label className="field">
                <span>Main colour</span>
                <input list="colour-suggestions" value={fields.colour} maxLength={40} onChange={(e) => set('colour', e.target.value)} placeholder="e.g. Green" />
                <datalist id="colour-suggestions">{COLOUR_SUGGESTIONS.map((c) => <option key={c} value={c} />)}</datalist>
              </label>
              <label className="field">
                <span>Price <i>(optional, for cost per wear)</i></span>
                <input type="number" inputMode="decimal" min="0" step="1" value={fields.price} onChange={(e) => set('price', e.target.value)} placeholder="e.g. 1499" />
              </label>
            </div>

            <fieldset className="field">
              <legend>Style</legend>
              <div className="chips">
                {options.styles.map((s) => (
                  <button type="button" key={s} className={fields.style === s ? 'chosen' : ''} aria-pressed={fields.style === s} onClick={() => set('style', s)}>{s}</button>
                ))}
              </div>
            </fieldset>

            <fieldset className="field">
              <legend>Suitable occasions</legend>
              <div className="chips">
                {options.occasions.map((o) => {
                  const on = fields.occasions.includes(o);
                  return <button type="button" key={o} className={on ? 'chosen' : ''} aria-pressed={on} onClick={() => toggleOccasion(o)}>{o}{on ? ' ✓' : ''}</button>;
                })}
              </div>
            </fieldset>

            <label className="field">
              <span>Notes <i>(optional)</i></span>
              <textarea rows={2} value={fields.notes} maxLength={300} onChange={(e) => set('notes', e.target.value)} placeholder="Fabric, fit, anything worth remembering" />
            </label>
          </div>
        </div>

        {isEdit && !photo && <CutoutEditor item={item} notify={notify} />}

        {error && <p className="form-error" role="alert">{error}</p>}

        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose}>Cancel</button>
          <button className="primary" disabled={saving}>
            {saving ? 'Saving…' : <>{isEdit ? 'Save changes' : 'Add to wardrobe'} <Check size={15} /></>}
          </button>
        </div>
      </form>
    </div>
  );
}
