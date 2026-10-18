// Virtual try-on requests, shared by every outfit card.
// The free Colab GPU can only make one image at a time, so requests wait in a queue.
// Finished results are remembered for this visit, so swapping back is instant.
import { createContext } from 'react';
import { api } from './api.js';

// { profile, refreshProfile } — provided by App.jsx
export const TryOnContext = createContext({ profile: null, refreshProfile: () => {} });

const results = new Map(); // "3,7,9" -> Promise<{ url, garments, skipped }>
let queue = Promise.resolve();
let offlineUntil = 0;
let offlineMessage = '';

export function requestTryOn(itemIds, { retry = false } = {}) {
  if (retry) offlineUntil = 0; // the user asked to try again: really try
  const key = [...itemIds].sort((a, b) => a - b).join(',');
  if (results.has(key)) return results.get(key);

  const job = queue.then(async () => {
    // If the server was just found to be offline, don't make every card wait for the same error.
    if (Date.now() < offlineUntil) throw new Error(offlineMessage);
    try {
      return await api.tryOn(itemIds);
    } catch (err) {
      if (err.status === 503 || err.status === 0) {
        offlineUntil = Date.now() + 30_000;
        offlineMessage = err.message;
      }
      throw err;
    }
  });
  queue = job.catch(() => {});
  results.set(key, job);
  job.catch(() => results.delete(key)); // failed: allow a retry later
  return job;
}

// Call after the photo or the server settings change.
export function forgetTryOns() {
  results.clear();
  offlineUntil = 0;
}
