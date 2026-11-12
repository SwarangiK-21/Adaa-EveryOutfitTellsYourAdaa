// The user's saved style preferences: kept with their account (style profile), with a copy in this
// browser (localStorage) so the Style me form can start from them straight away.
// They become the starting values of the Style me form.

import { storageKey } from './user.js';

const KEY = 'peheraav.preferences';   // stored per account: see storageKey

export const PREFERENCE_CHOICES = {
  style: ['Traditional Indian', 'Minimal & elegant', 'Western', 'Indo-western', 'A little bit of everything'],
  comfort: ['Comfort first', 'A polished look', 'A balance of both'],
  colour: ['Neutrals & earth tones', 'Bright & playful', 'Pastels', 'Dark & dramatic', 'No preference'],
};

export const DEFAULT_PREFERENCES = {
  style: 'A little bit of everything', comfort: 'A balance of both', colour: 'No preference',
};

export function loadPreferences() {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey(KEY)));
    return saved ? { ...DEFAULT_PREFERENCES, ...saved } : null;
  } catch {
    return null; // storage blocked or unreadable: just use no preferences
  }
}

export function savePreferences(prefs) {
  try {
    localStorage.setItem(storageKey(KEY), JSON.stringify(prefs));
    return true;
  } catch {
    return false;
  }
}

// Preferences page wording -> the values the stylist engine understands ('' = Any).
const STYLE_MAP = { 'Traditional Indian': 'Traditional', Western: 'Western', 'Indo-western': 'Indo-Western' };

export function toStylistDefaults(prefs) {
  if (!prefs) return {};
  return {
    style: STYLE_MAP[prefs.style] ?? '',
    comfort: prefs.comfort === 'A balance of both' ? '' : prefs.comfort,
    colour_mood: prefs.colour === 'No preference' ? '' : prefs.colour,
  };
}

// ---- keeping them with the account, so they follow you to other devices ----

export const toAccount = (prefs) => ({ style: prefs.style, comfort: prefs.comfort, colour_mood: prefs.colour });

// On start: the account's copy wins; a browser that has preferences the account doesn't yet uploads them once.
export function syncPreferences(profile, api) {
  const local = loadPreferences();
  if (profile && (profile.style || profile.comfort || profile.colour_mood)) {
    savePreferences({
      style: profile.style || DEFAULT_PREFERENCES.style,
      comfort: profile.comfort || DEFAULT_PREFERENCES.comfort,
      colour: profile.colour_mood || DEFAULT_PREFERENCES.colour,
    });
  } else if (local) {
    api.saveStyleProfile(toAccount(local)).catch(() => {});
  }
}

