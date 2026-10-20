import React, { useEffect, useState } from 'react';
import { RefreshCw, Sparkles, Info, BarChart3, IndianRupee, Coins } from 'lucide-react';
import { api } from '../api.js';
import Heading from '../components/Heading.jsx';
import { useUser } from '../user.js';
import { PieceImage } from '../components/OutfitPreview.jsx';

const WINDOWS = [30, 60, 90];
const rupees = (n) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);
const lastWorn = (r) => (r.days_since == null ? 'Not worn yet'
  : r.days_since === 0 ? 'Worn today' : `Last worn ${r.days_since} day${r.days_since === 1 ? '' : 's'} ago`);

/*
  Wear stats: which pieces you haven't worn lately (with a quick "Style it"), what you wear most,
  and cost per wear for pieces with a price. Counts come from your outfit history.
*/
export default function WearStats({ onStyle, goToWardrobe }) {
  const { first } = useUser();
  const [days, setDays] = useState(30);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState('');

  const load = () => {
    setError('');
    setStats(null);
    api.getWearStats(days).then(setStats).catch((err) => setError(err.message));
  };
  useEffect(load, [days]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      <Heading
        eyebrow="WEAR MORE OF WHAT YOU OWN"
        title={<>{first}'s <em>wear stats</em></>}
        sub="Which pieces are waiting to be worn, what you reach for most, and what each piece really costs you per wear."
      />
      <div className="chips stat-window" role="group" aria-label="Time window">
        {WINDOWS.map((d) => (
          <button type="button" key={d} className={days === d ? 'chosen' : ''} aria-pressed={days === d} onClick={() => setDays(d)}>Last {d} days</button>
        ))}
      </div>
      {error && <p className="form-error">{error} <button type="button" className="text-btn" onClick={load}>Try again</button></p>}
      {!stats && !error && <p className="muted"><RefreshCw size={13} className="spin" /> Counting your outfits…</p>}
      {stats && stats.total_items === 0 && (
        <div className="empty">
          <div><BarChart3 /></div>
          <h3>No pieces yet</h3>
          <p>Add your clothes first; stats appear as you wear them.</p>
          <button type="button" className="primary" onClick={goToWardrobe}>Go to My Wardrobe</button>
        </div>
      )}
      {stats && stats.total_items > 0 && (
        <>
          <div className="stats wear-tiles">
            <div className="stat"><span className="sage"><BarChart3 size={16} /></span><strong>{stats.worn_recently}<small> / {stats.total_items}</small></strong><b>pieces worn in the last {stats.days} days</b></div>
            <div className="stat"><span className="peach"><IndianRupee size={16} /></span><strong>{stats.total_spent != null ? rupees(stats.total_spent) : '–'}</strong><b>{stats.priced_items ? `spent on ${stats.priced_items} piece${stats.priced_items === 1 ? '' : 's'} with a price` : 'add prices to see what you spent'}</b></div>
            <div className="stat"><span className="rose"><Coins size={16} /></span><strong>{stats.average_cost_per_wear != null ? rupees(stats.average_cost_per_wear) : '–'}</strong><b>average cost per wear</b></div>
          </div>

          <section className="wear-section">
            <h2>Not worn in {stats.days} days <small>{stats.not_worn.length} piece{stats.not_worn.length === 1 ? '' : 's'}</small></h2>
            {stats.not_worn.length === 0 ? <p className="muted">You've worn everything lately. Lovely!</p> : (
              <div className="wear-grid">
                {stats.not_worn.map((r) => (
                  <article key={r.item.id} className="wear-card">
                    <PieceImage item={r.item} />
                    <div><b>{r.item.name}</b><small>{lastWorn(r)}{r.wears ? ` · worn ${r.wears}×` : ''}</small></div>
                    <button type="button" className="secondary" onClick={() => onStyle(r.item)}><Sparkles size={13} /> Style it</button>
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className="wear-section">
            <h2>Most worn</h2>
            {stats.most_worn.length === 0 ? <p className="muted">Nothing worn yet. Press <b>Wore it today</b> on a stylist outfit or a saved look to start counting.</p> : (
              <ol className="wear-list">
                {stats.most_worn.map((r) => (
                  <li key={r.item.id}><PieceImage item={r.item} /><span><b>{r.item.name}</b><small>{lastWorn(r)}</small></span><em>{r.wears}×</em></li>
                ))}
              </ol>
            )}
          </section>

          <section className="wear-section">
            <h2>Cost per wear <small>price divided by times worn</small></h2>
            {stats.cost_per_wear.length === 0 ? (
              <p className="muted">Add a price when you edit a piece in My Wardrobe to see what each wear really costs.</p>
            ) : (
              <div className="cpw-table" role="table">
                <div className="cpw-row head" role="row"><span role="columnheader">Piece</span><span role="columnheader">Price</span><span role="columnheader">Worn</span><span role="columnheader">Per wear</span></div>
                {stats.cost_per_wear.map((r) => (
                  <div className="cpw-row" role="row" key={r.item.id}>
                    <span role="cell" className="cpw-piece"><PieceImage item={r.item} /><b>{r.item.name}</b></span>
                    <span role="cell">{rupees(r.item.price)}</span>
                    <span role="cell">{r.wears}×</span>
                    <span role="cell"><b className={r.wears === 0 ? 'cpw-high' : ''}>{rupees(r.cost_per_wear)}</b></span>
                  </div>
                ))}
              </div>
            )}
          </section>
          <p className="disclaimer"><Info size={11} /> Wears are counted from your outfit history: <b>Wore it today</b> on a stylist outfit or a saved look. A piece never worn shows its full price as its cost per wear.</p>
        </>
      )}
    </>
  );
}
