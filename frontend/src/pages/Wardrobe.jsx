import React, { useEffect, useState } from 'react';
import { Plus, Search, Pencil, Trash2, Shirt, RefreshCw, Sparkles } from 'lucide-react';
import { api } from '../api.js';
import Heading from '../components/Heading.jsx';
import { useUser } from '../user.js';
import ItemForm from '../components/ItemForm.jsx';
import { queueMissingCutouts } from '../cutoutQueue.js';

export default function Wardrobe({ notify, onStyle }) {
  const { first } = useUser();
  const [options, setOptions] = useState(null);
  const [items, setItems] = useState([]);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [status, setStatus] = useState('loading'); // 'loading' | 'ready' | 'error'
  const [error, setError] = useState('');
  const [editing, setEditing] = useState(null); // null, 'new', or the item being edited
  const [reloadKey, setReloadKey] = useState(0);

  const reload = () => setReloadKey((k) => k + 1);

  // Load items whenever the search, category or reloadKey changes.
  // Typing in search waits 250 ms so we don't call the server on every keystroke.
  useEffect(() => {
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const [opts, list] = await Promise.all([
          options ?? api.getOptions(),
          api.listItems({ search, category }),
        ]);
        if (cancelled) return;
        setOptions(opts);
        setItems(list);
        queueMissingCutouts(list);
        setStatus('ready');
      } catch (err) {
        if (cancelled) return;
        setError(err.message);
        setStatus('error');
      }
    }, search ? 250 : 0);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [search, category, reloadKey]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSaved = (item, isNew) => {
    setEditing(null);
    notify(isNew ? `Nice one, ${first}! "${item.name}" is in your wardrobe.` : `"${item.name}" updated.`);
    reload();
  };

  const handleDelete = async (item) => {
    if (!window.confirm(`Delete "${item.name}" and its photo? This can't be undone.`)) return;
    try {
      await api.deleteItem(item.id);
      notify(`"${item.name}" deleted.`);
      reload();
    } catch (err) {
      notify(err.message);
    }
  };

  const filtering = search.trim() !== '' || category !== '';

  return (
    <>
      <Heading
        eyebrow="THE PIECES THAT MAKE YOU"
        title={<>{first}'s <em>wardrobe.</em></>}
        sub="A home for everything you wear, treasure and style your own way."
        action={<button className="primary" disabled={!options} onClick={() => setEditing('new')}><Plus size={16} /> Add a piece</button>}
      />

      <div className="toolbar">
        <div className="search">
          <Search size={17} />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search pieces, colours, occasions..." aria-label="Search wardrobe" />
        </div>
        {options && (
          <div className="chips filter-chips" aria-label="Filter by category">
            {['', ...options.categories].map((c) => (
              <button key={c || 'all'} className={category === c ? 'chosen' : ''} aria-pressed={category === c} onClick={() => setCategory(c)}>
                {c || 'All'}
              </button>
            ))}
          </div>
        )}
      </div>

      {status === 'loading' && <p className="muted">Loading your wardrobe…</p>}

      {status === 'error' && (
        <div className="empty">
          <div>!</div>
          <h3>Couldn't load your wardrobe</h3>
          <p>{error}</p>
          <button className="primary" onClick={() => { setStatus('loading'); reload(); }}><RefreshCw size={15} /> Try again</button>
        </div>
      )}

      {status === 'ready' && items.length === 0 && !filtering && (
        <div className="empty">
          <div><Shirt size={34} /></div>
          <h3>Your wardrobe is waiting</h3>
          <p>Add your first piece: a kurta, a pair of jhumkas, your favourite juttis. Adaa only ever styles you with pieces you add here.</p>
          <button className="primary" onClick={() => setEditing('new')}><Plus size={15} /> Add your first piece</button>
        </div>
      )}

      {status === 'ready' && items.length === 0 && filtering && (
        <p className="muted">No pieces match your search. Try another word or category.</p>
      )}

      {status === 'ready' && items.length > 0 && (
        <>
          <p className="muted">{items.length} {items.length === 1 ? 'piece' : 'pieces'}{filtering ? ' found' : ' in your wardrobe'}</p>
          <div className="items">
            {items.map((i) => (
              <article className="item" key={i.id}>
                <div className="item-photo">
                  <img src={i.image_url} alt={i.name} loading="lazy" />
                  <small>{i.item_type}</small>
                  <div className="item-actions">
                    <button className="icon-btn" onClick={() => onStyle(i)} aria-label={`Style ${i.name}`} title="Style this piece"><Sparkles size={15} /></button>
                    <button className="icon-btn" onClick={() => setEditing(i)} aria-label={`Edit ${i.name}`} title="Edit"><Pencil size={15} /></button>
                    <button className="icon-btn danger" onClick={() => handleDelete(i)} aria-label={`Delete ${i.name}`} title="Delete"><Trash2 size={15} /></button>
                  </div>
                </div>
                <div className="item-info">
                  <b>{i.name}</b>
                  <p>{i.category} · {i.colour} · {i.style}</p>
                </div>
              </article>
            ))}
          </div>
        </>
      )}

      {editing && options && (
        <ItemForm
          options={options}
          item={editing === 'new' ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={handleSaved}
          notify={notify}
        />
      )}
    </>
  );
}
