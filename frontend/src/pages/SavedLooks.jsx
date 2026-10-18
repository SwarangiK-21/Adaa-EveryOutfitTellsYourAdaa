import React, { useEffect, useRef, useState } from 'react';
import { Sparkles, RefreshCw, Check, Pencil, Trash2, X, Camera } from 'lucide-react';
import { api } from '../api.js';
import Heading from '../components/Heading.jsx';
import OutfitCard from '../components/OutfitCard.jsx';
import SwapPanel from '../components/SwapPanel.jsx';

const formatDate = (iso) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });

export default function SavedLooks({ notify, goToStylist, onCountChange }) {
  const [tab, setTab] = useState('saved'); // 'saved' | 'history'
  const [looks, setLooks] = useState(null);
  const [history, setHistory] = useState(null);
  const [error, setError] = useState('');
  const [swapping, setSwapping] = useState(null); // { look, piece }
  const photoInput = useRef(null);
  const photoFor = useRef(null); // which look the file picker is for

  const load = () => {
    setError('');
    Promise.all([api.getLooks(), api.getHistory()])
      .then(([l, h]) => { setLooks(l); setHistory(h); onCountChange?.(l.length); })
      .catch((err) => setError(err.message));
  };
  useEffect(load, []); // eslint-disable-line react-hooks/exhaustive-deps

  const replaceLook = (look) => setLooks((ls) => ls.map((l) => (l.id === look.id ? look : l)));

  const act = async (fn, message) => {
    try {
      await fn();
      if (message) notify(message);
    } catch (err) {
      notify(err.message);
    }
  };

  const wear = (look) => act(async () => {
    await api.wearLook(look.id);
    load();
  }, `Added "${look.name}" to today's outfit history.`);

  const rename = (look) => {
    const name = window.prompt('Name this look', look.name);
    if (!name || !name.trim() || name.trim() === look.name) return;
    act(async () => replaceLook(await api.updateLook(look.id, { name: name.trim() })), 'Look renamed.');
  };

  const remove = (look) => {
    if (!window.confirm(`Delete the saved look "${look.name}"? Your clothes stay in your wardrobe, and past history entries are kept.`)) return;
    act(async () => { await api.deleteLook(look.id); load(); }, 'Look deleted.');
  };

  const swapPiece = (option) => {
    const { look, piece } = swapping;
    setSwapping(null);
    const ids = look.pieces.map((p) => (p.item.id === piece.item.id ? option.item.id : p.item.id));
    act(async () => replaceLook(await api.updateLook(look.id, { item_ids: ids })), `Swapped in ${option.item.name}.`);
  };

  // Your own photo wearing a saved look = a verified preview.
  const pickPhoto = (look) => {
    photoFor.current = look;
    photoInput.current.value = '';
    photoInput.current.click();
  };
  const uploadPhoto = (e) => {
    const file = e.target.files[0];
    const look = photoFor.current;
    if (!file || !look) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024) {
      notify('Please choose a JPEG, PNG or WebP photo up to 5 MB.');
      return;
    }
    act(async () => replaceLook(await api.uploadLookPhoto(look.id, file)), 'Photo added. It now shows as a verified preview.');
  };
  const removePhoto = (look) => {
    if (!window.confirm('Remove your photo from this look?')) return;
    act(async () => { await api.deleteLookPhoto(look.id); replaceLook({ ...look, photo: null }); }, 'Photo removed.');
  };

  const removeHistory = (entry) =>
    act(async () => { await api.deleteHistoryEntry(entry.id); load(); }, 'Removed from history.');

  const heading = (
    <Heading
      eyebrow="YOUR PERSONAL LOOKBOOK"
      title={<>Looks to <em>love again.</em></>}
      sub="Keep the combinations you love, swap pieces, and remember what you wore."
    />
  );

  if (error) {
    return <>{heading}<div className="empty"><div>!</div><h3>Couldn't load your looks</h3><p>{error}</p>
      <button className="primary" onClick={load}><RefreshCw size={15} /> Try again</button></div></>;
  }
  if (!looks) return <>{heading}<p className="muted">Loading your looks…</p></>;

  // Group history by date: { '2026-10-15': [entries...] }
  const byDate = history.reduce((acc, h) => ({ ...acc, [h.worn_on]: [...(acc[h.worn_on] || []), h] }), {});

  return (
    <>
      {heading}
      <div className="chips tabs" role="tablist">
        <button role="tab" aria-selected={tab === 'saved'} className={tab === 'saved' ? 'chosen' : ''} onClick={() => setTab('saved')}>
          Saved looks ({looks.length})
        </button>
        <button role="tab" aria-selected={tab === 'history'} className={tab === 'history' ? 'chosen' : ''} onClick={() => setTab('history')}>
          Outfit history ({history.length})
        </button>
      </div>

      {tab === 'saved' && looks.length === 0 && (
        <div className="empty">
          <div>♡</div>
          <h3>Your lookbook starts here</h3>
          <p>Ask your stylist for outfits, then press <b>Save look</b> on the ones you love.</p>
          <button className="primary" onClick={goToStylist}>Explore styling <Sparkles size={15} /></button>
        </div>
      )}

      {tab === 'saved' && looks.length > 0 && (
        <div className="outfits">
          {looks.map((look) => (
            <OutfitCard
              key={look.id}
              outfit={look}
              title={look.name}
              label={`${look.prefs.occasion.toUpperCase()} · ${look.wear_count ? `WORN ${look.wear_count}× · LAST ${formatDate(look.last_worn_on).toUpperCase()}` : 'NOT WORN YET'}`}
              notice={look.missing_pieces > 0
                ? `${look.missing_pieces} piece${look.missing_pieces > 1 ? 's were' : ' was'} deleted from your wardrobe since you saved this look.`
                : null}
              photo={look.photo}
              onSwap={(piece) => setSwapping({ look, piece })}
              actions={<>
                <button className="secondary" onClick={() => wear(look)} disabled={look.pieces.length === 0}><Check size={14} /> Wore it today</button>
                <button className="icon-btn" onClick={() => pickPhoto(look)} aria-label={`${look.photo ? 'Replace' : 'Add'} your photo of ${look.name}`} title={look.photo ? 'Replace your photo' : 'Add your photo wearing this look'}><Camera size={14} /></button>
                {look.photo && <button className="icon-btn" onClick={() => removePhoto(look)} aria-label={`Remove your photo of ${look.name}`} title="Remove your photo"><X size={14} /></button>}
                <button className="icon-btn" onClick={() => rename(look)} aria-label={`Rename ${look.name}`} title="Rename"><Pencil size={14} /></button>
                <button className="icon-btn danger" onClick={() => remove(look)} aria-label={`Delete ${look.name}`} title="Delete"><Trash2 size={14} /></button>
              </>}
            />
          ))}
        </div>
      )}

      {tab === 'history' && history.length === 0 && (
        <div className="empty">
          <div>✧</div>
          <h3>No outfits recorded yet</h3>
          <p>When you wear a saved look, press <b>Wore it today</b> and it will appear here.</p>
        </div>
      )}

      {tab === 'history' && history.length > 0 && (
        <div className="history">
          {Object.entries(byDate).map(([day, entries]) => (
            <section key={day}>
              <h3>{formatDate(day)}</h3>
              {entries.map((h) => (
                <div className="history-entry" key={h.id}>
                  <div className="history-photos">
                    {h.pieces.length > 0
                      ? h.pieces.slice(0, 5).map((p) => <img key={p.item.id} src={p.item.image_url} alt={p.item.name} title={p.item.name} />)
                      : <span className="muted">Saved look deleted</span>}
                  </div>
                  <div><b>{h.look_name}</b><small>{h.occasion}</small></div>
                  <button className="icon-btn" onClick={() => removeHistory(h)} aria-label={`Remove ${h.look_name} from history`} title="Remove from history"><X size={14} /></button>
                </div>
              ))}
            </section>
          ))}
        </div>
      )}

      <input ref={photoInput} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={uploadPhoto} />

      {swapping && (
        <SwapPanel
          prefs={swapping.look.prefs}
          itemIds={swapping.look.pieces.map((p) => p.item.id)}
          piece={swapping.piece}
          onPick={swapPiece}
          onClose={() => setSwapping(null)}
        />
      )}
    </>
  );
}
