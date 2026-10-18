import React, { useContext, useRef, useState } from 'react';
import { Camera, Trash2, Check, PlugZap, Sparkles, X } from 'lucide-react';
import { api } from '../api.js';
import { TryOnContext, forgetTryOns } from '../tryon.js';

const PHOTO_TIPS = [
  'Full length, head to feet',
  'Standing straight, facing the camera',
  'Fitted, plain clothes work best',
  'Good light, plain background',
];

// Shared picker: checks the file, uploads it, refreshes the profile.
function usePhotoUpload(notify) {
  const { refreshProfile } = useContext(TryOnContext);
  const input = useRef(null);
  const [busy, setBusy] = useState(false);
  const pick = () => { input.current.value = ''; input.current.click(); };
  const onChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024) {
      notify('Please choose a JPEG, PNG or WebP photo up to 5 MB. (iPhone HEIC: export as JPEG first.)');
      return;
    }
    setBusy(true);
    try {
      await api.uploadProfilePhoto(file);
      forgetTryOns();
      await refreshProfile();
      notify('Your photo is saved.');
    } catch (err) {
      notify(err.message);
    } finally {
      setBusy(false);
    }
  };
  const fileInput = <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={onChange} />;
  return { pick, busy, fileInput };
}

// First time Adaa opens: ask for a full-length photo (can be skipped).
export function WelcomeSetup({ notify, onDone }) {
  const { pick, busy, fileInput } = usePhotoUpload((msg) => { notify(msg); if (msg === 'Your photo is saved.') onDone(); });
  return (
    <div className="modal-backdrop">
      <section className="modal welcome" role="dialog" aria-modal="true" aria-labelledby="welcome-title">
        <div className="modal-head">
          <div>
            <small>WELCOME TO ADAA</small>
            <h2 id="welcome-title">See every outfit on you.</h2>
          </div>
          <button type="button" className="icon-btn" onClick={onDone} aria-label="Skip for now"><X size={18} /></button>
        </div>
        <div className="welcome-body">
          <p>Add one full-length photo of yourself. When your try-on server is running, Adaa shows the outfits it suggests <b>on you</b>, and updates the picture when you swap a piece.</p>
          <ul>{PHOTO_TIPS.map((t) => <li key={t}><Check size={13} />{t}</li>)}</ul>
          <p className="muted">Your photo stays on this computer. It's only sent to <b>your own</b> try-on server (your Colab notebook), and only when you set one up in Preferences.</p>
        </div>
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onDone}>Skip for now</button>
          <button type="button" className="primary" onClick={pick} disabled={busy}>
            <Camera size={15} /> {busy ? 'Saving…' : 'Upload my photo'}
          </button>
        </div>
        {fileInput}
      </section>
    </div>
  );
}

// Preferences page section: your photo + the try-on server link and token.
export function YourPhotoSettings({ notify }) {
  const { profile, refreshProfile } = useContext(TryOnContext);
  const { pick, busy, fileInput } = usePhotoUpload(notify);
  const [url, setUrl] = useState(profile?.tryon_url || '');
  const [token, setToken] = useState('');
  const [quality, setQuality] = useState(profile?.tryon_quality || 'standard');
  const [tryShoes, setTryShoes] = useState(profile?.tryon_shoes ?? false);
  const [status, setStatus] = useState(null);
  const [checking, setChecking] = useState(false);

  const removePhoto = async () => {
    if (!window.confirm('Remove your photo? Outfits will show the drawn model instead.')) return;
    try { await api.deleteProfilePhoto(); forgetTryOns(); await refreshProfile(); notify('Photo removed.'); } catch (err) { notify(err.message); }
  };

  const test = async () => {
    setChecking(true);
    try { setStatus(await api.tryOnStatus()); } catch (err) { setStatus({ online: false, message: err.message }); }
    setChecking(false);
  };

  const save = async (e) => {
    e.preventDefault();
    try {
      await api.saveTryOnSettings(url.trim(), token.trim(), quality, tryShoes);
      forgetTryOns();
      await refreshProfile();
      setToken('');
      notify(url.trim() ? 'Try-on server saved.' : 'Try-on switched off.');
      if (url.trim()) test();
    } catch (err) {
      notify(err.message);
    }
  };

  return (
    <>
      <section>
        <h3>Your photo</h3>
        <div className="your-photo">
          <div className="your-photo-frame">
            {profile?.photo_url ? <img src={profile.photo_url} alt="Your full-length photo" /> : <Camera size={26} />}
          </div>
          <div>
            <p className="muted">Used to show outfits on you. A full-length, front-facing photo works best. It stays on this computer.</p>
            <div className="row-actions">
              <button type="button" className="secondary" onClick={pick} disabled={busy}><Camera size={14} /> {profile?.photo_url ? 'Replace photo' : 'Upload photo'}</button>
              {profile?.photo_url && <button type="button" className="icon-btn danger" onClick={removePhoto} aria-label="Remove your photo" title="Remove photo"><Trash2 size={14} /></button>}
            </div>
          </div>
        </div>
        {fileInput}
      </section>

      <section>
        <h3>Try-on server <small className="muted">(your free Colab GPU)</small></h3>
        <p className="muted">Open <b>tryon/Adaa_TryOn_Colab.ipynb</b> in Google Colab, choose a T4 GPU, and press <i>Run all</i>. Paste the link and token it prints here. Full steps: docs/TRYON_SETUP.md.</p>
        <form className="tryon-form" onSubmit={save}>
          <label className="field"><span>Server link</span>
            <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://something.trycloudflare.com" />
          </label>
          <label className="field"><span>Token {profile?.tryon_configured && <i>(saved; type a new one to change it)</i>}</span>
            <input value={token} onChange={(e) => setToken(e.target.value)} placeholder={profile?.tryon_configured ? '••••••••' : 'Paste the token from Colab'} autoComplete="off" />
          </label>
          <fieldset className="field">
            <legend>Quality</legend>
            <div className="chips">
              {[['standard', 'Standard (recommended, ~1 min)'], ['high', 'High (~1.5× slower)']].map(([value, label]) => (
                <button type="button" key={value} className={quality === value ? 'chosen' : ''} aria-pressed={quality === value} onClick={() => setQuality(value)}>{label}</button>
              ))}
            </div>
          </fieldset>
          <label className="check">
            <input type="checkbox" checked={tryShoes} onChange={(e) => setTryShoes(e.target.checked)} />
            Also try shoes on me <i>(experimental: usually looks smudged; adds time to each look)</i>
          </label>
          <p className="muted">Jewellery, watches and bags can't be tried on with this model; they're shown as product photos.</p>
          <div className="row-actions">
            <button className="primary" disabled={!url.trim() && !profile?.tryon_configured}><Check size={14} /> Save</button>
            {profile?.tryon_configured && <button type="button" className="secondary" onClick={test} disabled={checking}><PlugZap size={14} /> {checking ? 'Checking…' : 'Test connection'}</button>}
          </div>
        </form>
        {status && <p className={`tryon-status ${status.online ? 'ok' : 'bad'}`}>{status.online ? <Sparkles size={13} /> : null} {status.message}</p>}
      </section>
    </>
  );
}
