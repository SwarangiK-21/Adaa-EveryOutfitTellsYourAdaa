import React, { useState } from 'react';
import { MapPin, Search, RefreshCw, X } from 'lucide-react';
import { searchPlaces, savePlace, useTodayWeather } from '../weather.js';

// Preferences section: the city used for today's weather in styling.
export default function WeatherSettings({ notify }) {
  const { place, weather, error } = useTodayWeather();
  const [text, setText] = useState('');
  const [results, setResults] = useState(null);
  const [busy, setBusy] = useState(false);
  const [searchError, setSearchError] = useState('');

  const search = async (e) => {
    e.preventDefault();
    if (text.trim().length < 2) return;
    setBusy(true);
    setSearchError('');
    try {
      const found = await searchPlaces(text.trim());
      setResults(found);
      if (!found.length) setSearchError('No places found. Try the nearest city.');
    } catch (err) {
      setSearchError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const choose = (p) => {
    notify(savePlace(p) ? `Weather will be for ${p.name}.` : "Couldn't save the city in this browser.");
    setResults(null);
    setText('');
  };

  return (
    <section className="weather-settings">
      <h3>Your city, for today's weather</h3>
      {place ? (
        <div className="weather-now">
          <MapPin size={15} />
          <span>
            <b>{place.name}</b>{place.region ? `, ${place.region}` : ''}{place.country ? `, ${place.country}` : ''}
            <small>{weather ? weather.label : error || 'Checking today\'s weather…'}</small>
          </span>
          <button type="button" className="text-btn" onClick={() => { savePlace(null); notify('Weather turned off.'); }}><X size={12} /> Remove</button>
        </div>
      ) : <p className="muted">Add your city and the stylist will dress you for the weather: light pieces on hot days, warm layers when it's cold.</p>}
      <form className="weather-search" onSubmit={search}>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder={place ? 'Change city…' : 'e.g. Pune'} maxLength={60} aria-label="City" />
        <button className="secondary" disabled={busy || text.trim().length < 2}>
          {busy ? <RefreshCw size={13} className="spin" /> : <Search size={13} />} Search
        </button>
      </form>
      {searchError && <p className="muted">{searchError}</p>}
      {results?.length > 0 && (
        <ul className="place-results">
          {results.map((p) => (
            <li key={`${p.latitude},${p.longitude}`}>
              <button type="button" onClick={() => choose(p)}>
                <MapPin size={12} /> <b>{p.name}</b> {[p.region, p.country].filter(Boolean).join(', ')}
              </button>
            </li>
          ))}
        </ul>
      )}
      <p className="muted small">Uses Open-Meteo (free, no account). Only your city's location is sent to get the forecast.</p>
    </section>
  );
}
