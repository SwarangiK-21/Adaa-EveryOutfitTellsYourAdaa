import React, { useContext, useEffect, useRef, useState } from 'react';
import { BadgeCheck, Shirt, AlertTriangle, ImageOff, Sparkles, RefreshCw, LayoutGrid, Download } from 'lucide-react';
import OutfitBoard, { needsCutouts } from './OutfitBoard.jsx';
import { TryOnContext, requestTryOn } from '../tryon.js';
import { subscribeCutouts } from '../cutoutQueue.js';
import { downloadBoard } from '../boardImage.js';

/*
  Full-body preview of an outfit. Best available first:
    1. Verified      - your own photo wearing this saved look, while the look is unchanged
    2. Outfit board  - your real garments, background removed, arranged as if worn (default; instant)
    3. AI try-on     - optional, only when you ask for it (needs your Colab try-on server)
  Each kind is labelled; nothing is presented as more accurate than it is.
*/

// Rough colour for a piece, used when its photo can't be shown.
const SWATCHES = {
  black: '#2b2724', white: '#f6f4ef', ivory: '#f3ead8', cream: '#efe3c8', beige: '#dccbb0',
  grey: '#9a968f', gray: '#9a968f', navy: '#27324d', tan: '#b58a5c', brown: '#6e4b32',
  denim: '#4a6488', blue: '#3f62a8', red: '#b23a3a', maroon: '#6d2131', pink: '#e39ab3',
  green: '#4f8a5b', sage: '#9cad8f', olive: '#76794a', yellow: '#e2c249', mustard: '#c99a2e',
  orange: '#de8a3e', peach: '#f0bfa0', purple: '#7b5aa0', lavender: '#bba8d8', gold: '#c9a23a',
  silver: '#bfc2c7', teal: '#2f8481',
};
export function swatchFor(colour) {
  const words = (colour || '').toLowerCase().split(/[^a-z]+/);
  return SWATCHES[words.find((w) => SWATCHES[w])] || '#d9c7b7';
}

// An item photo that falls back to a colour swatch if it can't load.
export function PieceImage({ item, className }) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <span className={`img-fallback ${className || ''}`} style={{ background: swatchFor(item.colour) }}
        role="img" aria-label={`${item.name} (photo unavailable)`} title="Photo unavailable">
        <ImageOff size={14} />
      </span>
    );
  }
  return <img className={className} src={item.image_url} alt={item.name} loading="lazy" onError={() => setFailed(true)} />;
}

const formatDate = (iso) => new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });

export default function OutfitPreview({ pieces, photo, title }) {
  const { profile } = useContext(TryOnContext);
  const [showOld, setShowOld] = useState(false);
  const [photoFailed, setPhotoFailed] = useState(false);
  const [showTryOn, setShowTryOn] = useState(false);
  const [attempt, setAttempt] = useState(0);
  // status: 'idle' | 'loading' | 'ready' | 'failed'
  const [tryOnState, setTryOnState] = useState({ status: 'idle' });
  const [cutouts, setCutouts] = useState({ running: false });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  const boardFrame = useRef(null);
  useEffect(() => subscribeCutouts(setCutouts), []);

  const verified = photo && photo.matches_current && !photoFailed;
  const outdated = photo && !photo.matches_current;
  const canTryOn = Boolean(profile?.photo_url && profile?.tryon_configured);
  const ids = pieces.map((p) => p.item.id);
  const key = ids.join(',');

  // A swap changes the pieces: go back to the instant board (try-on is only made when asked).
  useEffect(() => { setShowTryOn(false); setTryOnState({ status: 'idle' }); }, [key]);

  useEffect(() => {
    if (!showTryOn || !canTryOn) return undefined;
    let alive = true;
    setTryOnState({ status: 'loading' });
    requestTryOn(ids, { retry: attempt > 0 })
      .then((result) => alive && setTryOnState({ status: 'ready', result }))
      .catch((err) => alive && setTryOnState({ status: 'failed', message: err.message }));
    return () => { alive = false; };
  }, [showTryOn, key, attempt, canTryOn, profile?.photo_url]); // eslint-disable-line react-hooks/exhaustive-deps

  // 1. Verified photo
  if (verified) {
    return (
      <figure className="preview">
        <div className="preview-frame">
          <img className="preview-photo" src={photo.url} alt="Your photo wearing this look" onError={() => setPhotoFailed(true)} />
          <span className="preview-badge verified"><BadgeCheck size={13} /> Verified · your photo</span>
        </div>
        <figcaption>Your own photo of this exact look, added {formatDate(photo.taken_at)}.</figcaption>
      </figure>
    );
  }

  // 3. AI try-on, when asked for
  if (showTryOn && tryOnState.status === 'ready' && !(outdated && showOld)) {
    const r = tryOnState.result;
    return (
      <figure className="preview">
        <div className="preview-frame">
          <img className="preview-photo" src={r.url} alt="You wearing this outfit (AI)" />
          <span className="preview-badge tryon"><Sparkles size={13} /> AI try-on · approximation</span>
          <button type="button" className="preview-action" onClick={() => setShowTryOn(false)}>
            <LayoutGrid size={14} /> Back to my pieces
          </button>
        </div>
        <figcaption>
          Made by your try-on server. AI can get details wrong.
          {r.skipped.length > 0 && ` Not shown on you: ${r.skipped.join(', ')}.`}
          {(r.notes || []).map((n) => <span key={n} className="preview-note"> {n}</span>)}
        </figcaption>
      </figure>
    );
  }

  // 2. Outfit board (default)
  const preparing = needsCutouts(pieces) && cutouts.running;
  const saveImage = async () => {
    setSaving(true);
    setSaveError('');
    try {
      await downloadBoard(boardFrame.current, title);
    } catch (err) {
      setSaveError(err.message || "Couldn't save the image.");
    } finally {
      setSaving(false);
    }
  };
  return (
    <figure className="preview">
      <div className="preview-frame board-frame" ref={boardFrame}>
        {outdated && showOld ? (
          <>
            <img className="preview-photo old" src={photo.url} alt="Your earlier photo of this look (outdated)" />
            <span className="preview-badge outdated"><AlertTriangle size={13} /> Outdated photo</span>
          </>
        ) : (
          <>
            <OutfitBoard pieces={pieces} />
            <span className="preview-badge"><Shirt size={13} /> Your pieces</span>
            {showTryOn && tryOnState.status === 'loading' && (
              <span className="preview-progress"><RefreshCw size={14} className="spin" /> Putting this look on you… (about 1 minute)</span>
            )}
            {canTryOn && !showTryOn && (
              <button type="button" className="preview-action subtle" onClick={() => setShowTryOn(true)}>
                <Sparkles size={13} /> Try on me (AI)
              </button>
            )}
          </>
        )}
      </div>
      <figcaption>
        {outdated && showOld
          ? 'Your earlier photo. Some pieces have changed since, so it no longer shows this exact look.'
          : 'Your own garment photos, arranged as an outfit.'}
        {!(outdated && showOld) && (
          <>
            {' '}
            <button type="button" className="text-btn download-btn" onClick={saveImage} disabled={saving}>
              <Download size={11} /> {saving ? 'Saving…' : 'Download image'}
            </button>
          </>
        )}
        {saveError && <span className="preview-note"> {saveError}</span>}
        {preparing && !(outdated && showOld) && (
          <span className="preview-hint"> Cleaning up photo backgrounds… ({cutouts.done + 1} of {cutouts.total})</span>
        )}
        {showTryOn && tryOnState.status === 'failed' && (
          <span className="preview-note">
            {' '}Couldn’t make your try-on: {tryOnState.message}{' '}
            <button type="button" className="text-btn" onClick={() => setAttempt((a) => a + 1)}>Try again</button>
          </span>
        )}
        {photoFailed && <span className="preview-note"> Your photo couldn’t be loaded.</span>}
        {outdated && (
          <span className="preview-note">
            {' '}Your photo of this look is outdated
            {photo.changed_pieces.length > 0 ? ` (now includes ${photo.changed_pieces.join(', ')})` : ' (a piece was removed)'}.{' '}
            <button type="button" className="text-btn" onClick={() => setShowOld((v) => !v)}>
              {showOld ? 'Show my pieces' : 'View old photo'}
            </button>
          </span>
        )}
      </figcaption>
    </figure>
  );
}
