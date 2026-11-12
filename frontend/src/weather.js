// Today's weather from Open-Meteo (free, no account, no key), fetched by the browser.
// Only your saved city's coordinates are sent to Open-Meteo; nothing else leaves your device.
import { useEffect, useState } from 'react';
import { storageKey } from './user.js';

const PLACE_KEY = 'peheraav.place';
const CACHE_KEY = 'peheraav.weather';
const CACHE_MS = 60 * 60 * 1000;   // refresh at most once an hour

export function loadPlace() {
  try { return JSON.parse(localStorage.getItem(storageKey(PLACE_KEY))) || null; } catch { return null; }
}

export function savePlace(place) {
  try {
    if (place) localStorage.setItem(storageKey(PLACE_KEY), JSON.stringify(place));
    else localStorage.removeItem(storageKey(PLACE_KEY));
    sessionStorage.removeItem(CACHE_KEY);
    window.dispatchEvent(new Event('peheraav-place'));
    return true;
  } catch {
    return false;
  }
}

// Find places by name: [{ name, region, country, latitude, longitude }]
export async function searchPlaces(text) {
  const url = `https://geocoding-api.open-meteo.com/v1/search?count=6&language=en&format=json&name=${encodeURIComponent(text)}`;
  let res;
  try { res = await fetch(url); } catch { throw new Error("Couldn't reach the weather service. Are you online?"); }
  if (!res.ok) throw new Error('The weather service is busy. Please try again.');
  const data = await res.json();
  return (data.results || []).map((r) => ({
    name: r.name, region: r.admin1 || '', country: r.country || '', latitude: r.latitude, longitude: r.longitude,
  }));
}

// WMO weather codes -> a few words.
function describe(code) {
  if (code === 0) return 'clear';
  if (code <= 3) return 'partly cloudy';
  if (code <= 48) return 'foggy';
  if (code <= 57) return 'drizzle';
  if (code <= 67) return 'rain';
  if (code <= 77) return 'snow';
  if (code <= 82) return 'showers';
  return 'thunderstorms';
}

// Today's forecast for a place: { temp_c (today's high), low_c, rain, summary, label }
export async function getWeather(place) {
  const key = `${place.latitude},${place.longitude}`;
  try {
    const cached = JSON.parse(sessionStorage.getItem(CACHE_KEY));
    if (cached && cached.key === key && Date.now() - cached.at < CACHE_MS) return cached.weather;
  } catch { /* no cache */ }
  const url = 'https://api.open-meteo.com/v1/forecast'
    + `?latitude=${place.latitude}&longitude=${place.longitude}`
    + '&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code'
    + '&timezone=auto&forecast_days=1';
  let res;
  try { res = await fetch(url); } catch { throw new Error("Couldn't reach the weather service."); }
  if (!res.ok) throw new Error('The weather service is busy right now.');
  const d = (await res.json()).daily;
  const code = d.weather_code[0];
  const high = d.temperature_2m_max[0];
  const rainChance = d.precipitation_probability_max?.[0] ?? 0;
  const rain = rainChance >= 50 || (code >= 51 && code <= 99 && code !== 71 && code !== 73 && code !== 75 && code !== 77);
  const summary = rain && code < 51 ? `${describe(code)}, rain likely` : describe(code);
  const weather = {
    temp_c: Math.round(high * 10) / 10,
    low_c: Math.round(d.temperature_2m_min[0]),
    rain,
    summary,
    label: `${Math.round(high)}°C, ${summary} in ${place.name}`.slice(0, 80),
  };
  try { sessionStorage.setItem(CACHE_KEY, JSON.stringify({ key, at: Date.now(), weather })); } catch { /* fine */ }
  return weather;
}

// How Peheraav will dress you for it, in a few words.
export function styleHint(weather) {
  if (!weather) return '';
  const parts = [];
  if (weather.temp_c >= 30) parts.push('light, breezy pieces');
  else if (weather.temp_c <= 17) parts.push('warm layers');
  if (weather.rain) parts.push('rain-friendly shoes');
  return parts.length ? `Styling for ${parts.join(' and ')}` : 'Mild day: no weather changes needed';
}

// React hook: { place, weather, error } for the saved city (weather is null until loaded).
export function useTodayWeather() {
  const [place, setPlace] = useState(loadPlace);
  const [weather, setWeather] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    const onChange = () => setPlace(loadPlace());
    window.addEventListener('peheraav-place', onChange);
    return () => window.removeEventListener('peheraav-place', onChange);
  }, []);
  useEffect(() => {
    let alive = true;
    setWeather(null);
    setError('');
    if (!place) return undefined;
    getWeather(place).then((w) => alive && setWeather(w)).catch((err) => alive && setError(err.message));
    return () => { alive = false; };
  }, [place]);
  return { place, weather, error };
}
