// Who is signed in, for any component: const { user, first } = useUser();
// Also keeps each person's browser settings (preferences, weather city...) separate.
import { createContext, useContext } from 'react';

export const UserContext = createContext({ user: null, setUser: () => {}, logout: () => {} });

export function useUser() {
  const ctx = useContext(UserContext);
  return { ...ctx, first: ctx.user?.first_name || '' };
}

export const initials = (name) =>
  (name || '').split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join('') || '?';

// Browser settings are stored per account: "peheraav.preferences" becomes "peheraav.preferences.u3".
let userId = null;
export function setStorageUser(id) {
  userId = id;
  // The first account inherits settings saved before accounts existed.
  if (id === 1) {
    try {
      for (const base of ['peheraav.preferences', 'peheraav.place']) {
        const old = localStorage.getItem(base);
        if (old !== null && localStorage.getItem(storageKey(base)) === null) localStorage.setItem(storageKey(base), old);
      }
    } catch { /* storage blocked: nothing to carry over */ }
  }
}
export const storageKey = (base) => (userId ? `${base}.u${userId}` : base);

// A friendly line for each suggested look, so the stylist talks to you by name.
const LINES = [
  (n) => `${n}, this one would look lovely on you.`,
  (n) => `Easy and elegant, ${n}: a look you can count on.`,
  (n) => `${n}, try this when you want something a little different.`,
  (n) => `A fresh mix from your own wardrobe, ${n}.`,
];
export const personalLine = (first, rank) => (first ? LINES[(rank - 1) % LINES.length](first) : '');
