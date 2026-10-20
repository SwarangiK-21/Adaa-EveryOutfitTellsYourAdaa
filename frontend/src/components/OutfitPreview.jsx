import React, { useEffect, useRef, useState } from 'react';
import { BadgeCheck, Shirt, AlertTriangle, ImageOff, Download } from 'lucide-react';
import OutfitBoard, { needsCutouts } from './OutfitBoard.jsx';
import { subscribeCutouts } from '../cutoutQueue.js';
import { downloadBoard } from '../boardImage.js';

/*
  Full-body preview of an outfit. Best available first:
    1. Verified      - your own photo wearing this saved look, while the look is unchanged
    2. Outfit board  - your real garments, background removed, arranged as if worn
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
  const [showOld, setShowOld] = useState(false);
  const [photoFailed, setPhotoFailed] = useState(false);
  const [cutouts, setCutouts] = useState({ running: false });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  const boardFrame = useRef(null);
  useEffect(() => subscribeCutouts(setCutouts), []);

  const verified = photo && photo.matches_current && !photoFailed;
  const outdated = photo && !photo.matches_current;

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

  // 2. Outfit board
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
