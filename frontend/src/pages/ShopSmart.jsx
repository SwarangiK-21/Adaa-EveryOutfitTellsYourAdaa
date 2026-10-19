import React, { useEffect, useState } from 'react';
import { RefreshCw, ShoppingBag, Info } from 'lucide-react';
import { api } from '../api.js';
import Heading from '../components/Heading.jsx';
import { PieceImage, swatchFor } from '../components/OutfitPreview.jsx';

/*
  "Shop smart": which one new piece would unlock the most new outfits with what you already own.
  These are ideas, not products: Adaa never links to a shop or buys anything.
*/
export default function ShopSmart({ goToWardrobe }) {
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');

  const load = () => {
    setError('');
    setReport(null);
    api.getGaps().then(setReport).catch((err) => setError(err.message));
  };
  useEffect(load, []);

  return (
    <>
      <Heading
        eyebrow="BUY LESS, WEAR MORE"
        title={<>What would unlock <em>the most?</em></>}
        sub="Ideas for one new piece that creates the most new outfits with clothes you already own. Adaa never shops or buys for you."
      />
      {error && <p className="form-error">{error} <button type="button" className="text-btn" onClick={load}>Try again</button></p>}
      {!report && !error && <p className="muted"><RefreshCw size={13} className="spin" /> Looking through your wardrobe…</p>}
      {report && (
        <>
          <div className="gap-summary">
            <div><strong>{report.outfits_now}</strong><span>complete outfit{report.outfits_now === 1 ? '' : 's'} your wardrobe makes today</span></div>
            {report.notes.map((n) => <p key={n}><Info size={13} /> {n}</p>)}
          </div>
          {report.suggestions.length === 0 ? (
            <div className="empty">
              <div><ShoppingBag /></div>
              <h3>Nothing obvious is missing</h3>
              <p>None of Adaa's go-to pieces would add new outfits right now. Add more of your clothes and their occasions to get ideas.</p>
              <button type="button" className="primary" onClick={goToWardrobe}>Go to My Wardrobe</button>
            </div>
          ) : (
            <div className="gap-grid">
              {report.suggestions.map((s) => (
                <article className="gap-card" key={s.name}>
                  <header>
                    <span className="gap-swatch" style={{ background: swatchFor(s.colour) }} aria-hidden="true" />
                    <div><small>{s.category.toUpperCase()}</small><h3>{s.name}</h3></div>
                    <b className="gap-count">+{s.new_outfits}<small>outfit{s.new_outfits === 1 ? '' : 's'}</small></b>
                  </header>
                  <p>{s.reason}.</p>
                  <div className="gap-occasions">{s.occasions.map((o) => <span key={o}>{o}</span>)}</div>
                  {s.pairs_with.length > 0 && (
                    <div className="gap-pairs">
                      <small>Goes with your</small>
                      <div>{s.pairs_with.map((item) => (
                        <figure key={item.id} title={item.name}><PieceImage item={item} /><figcaption>{item.name}</figcaption></figure>
                      ))}</div>
                    </div>
                  )}
                </article>
              ))}
            </div>
          )}
          <p className="disclaimer">ⓘ Counts use the same rules as your stylist: pieces must suit each other and be tagged for the occasion.</p>
        </>
      )}
    </>
  );
}
