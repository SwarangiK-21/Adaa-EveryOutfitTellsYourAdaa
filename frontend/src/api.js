import { preparePhoto } from './photo.js';
// Small helpers for talking to the Peheraav backend (proxied by Vite to port 8000).

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.status = status; // HTTP status, 0 if the server couldn't be reached
  }
}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(path, options);
  } catch {
    throw new ApiError("Can't reach the Peheraav server. Is the backend running?");
  }
  if (res.status === 204) return null;

  const body = await res.json().catch(() => null);
  // Signed out (session ended): let the app show the sign-in screen. Auth calls handle their own 401s.
  if (res.status === 401 && !path.startsWith('/api/auth/')) {
    window.dispatchEvent(new Event('peheraav-signed-out'));
  }
  if (!res.ok) {
    if (res.status >= 500 && !body) {
      throw new ApiError("Can't reach the Peheraav server. Is the backend running?");
    }
    const detail = body?.detail;
    const message = Array.isArray(detail)
      ? detail.map((d) => (typeof d === 'string' ? d : String(d.msg).replace(/^Value error, /, ''))).join(' · ')
      : detail || `Something went wrong (error ${res.status}).`;
    throw new ApiError(message, res.status);
  }
  return body;
}

// Turn item details (+ optional photo File) into multipart form data.
function toFormData(fields, photo) {
  const data = new FormData();
  for (const [key, value] of Object.entries(fields)) {
    if (Array.isArray(value)) value.forEach((v) => data.append(key, v));
    else data.append(key, value);
  }
  if (photo) data.append('photo', photo);
  return data;
}

const postJson = (path, body, method = 'POST') =>
  request(path, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

export const api = {
  // ---- Accounts ----
  signup: (fields) => postJson('/api/auth/signup', fields),        // { name, email, phone, password, accept_privacy }
  login: (fields) => postJson('/api/auth/login', fields),          // { email, password }
  logout: () => request('/api/auth/logout', { method: 'POST' }),
  me: () => request('/api/auth/me'),
  updateMe: (fields) => postJson('/api/auth/me', fields, 'PUT'),   // { name, phone }
  about: () => request('/api/auth/about'),
  getStyleProfile: () => request('/api/profile/style'),
  saveStyleProfile: (changes) => postJson('/api/profile/style', changes, 'PATCH'),   // only the fields sent change                          // { contact_email, max_items, max_looks }
  changePassword: (current, next) => postJson('/api/auth/password', { current_password: current, new_password: next }, 'PUT'),
  forgotPassword: (email) => postJson('/api/auth/forgot', { email }),
  verifyEmail: (token) => postJson('/api/auth/verify', { token }),
  resendVerification: () => request('/api/auth/verify/resend', { method: 'POST' }),
  resetPassword: (token, password) => postJson('/api/auth/reset', { token, password }),
  deleteAccount: (password) => postJson('/api/auth/me', { password }, 'DELETE'),

  getOptions: () => request('/api/options'),

  listItems: ({ search = '', category = '' } = {}) => {
    const params = new URLSearchParams();
    if (search.trim()) params.set('search', search.trim());
    if (category) params.set('category', category);
    const query = params.toString();
    return request(`/api/items${query ? `?${query}` : ''}`);
  },

  // Photos are shrunk and cleaned of hidden metadata (e.g. GPS location) before they leave the browser.
  createItem: async (fields, photo) =>
    request('/api/items', { method: 'POST', body: toFormData(fields, photo && await preparePhoto(photo)) }),

  updateItem: async (id, fields, photo) =>
    request(`/api/items/${id}`, { method: 'PUT', body: toFormData(fields, photo && await preparePhoto(photo)) }),

  deleteItem: (id) => request(`/api/items/${id}`, { method: 'DELETE' }),

  // The garment with its background removed (made in the browser by cutout.js).
  saveCutout: (id, pngBlob, version = '1') => {
    const data = new FormData();
    data.append('cutout', pngBlob, 'cutout.png');
    data.append('version', version);
    return request(`/api/items/${id}/cutout`, { method: 'PUT', body: data });
  },

  // Read a typed request ("Style my black crop top for a party") into filters.
  parseRequest: (text) =>
    request('/api/stylist/parse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    }),

  // preferences: { occasion, style, colour, colour_mood, comfort, anchor_item_id }
  recommend: (preferences) =>
    request('/api/recommendations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(preferences),
    }),

  // ---- Phase 5: swaps, saved looks, history ----
  // prefs: { occasion, style, colour, colour_mood, comfort }
  swapOptions: (prefs, itemIds, replaceId) =>
    postJson('/api/outfits/alternatives', { prefs, item_ids: itemIds, replace_item_id: replaceId }),
  evaluateOutfit: (prefs, itemIds) => postJson('/api/outfits/evaluate', { prefs, item_ids: itemIds }),

  getLooks: () => request('/api/looks'),
  saveLook: (prefs, itemIds, name) => postJson('/api/looks', { prefs, item_ids: itemIds, name }),
  updateLook: (id, changes) => postJson(`/api/looks/${id}`, changes, 'PUT'),
  deleteLook: (id) => request(`/api/looks/${id}`, { method: 'DELETE' }),
  wearLook: (id) => postJson(`/api/looks/${id}/wear`, {}),

  uploadLookPhoto: async (id, photo) => {
    const data = new FormData();
    data.append('photo', await preparePhoto(photo));
    return request(`/api/looks/${id}/photo`, { method: 'POST', body: data });
  },
  deleteLookPhoto: (id) => request(`/api/looks/${id}/photo`, { method: 'DELETE' }),

  // ---- Planning ----
  getGaps: () => request('/api/insights/gaps'),
  // days: the occasion for each day, e.g. ['Travel', 'Casual', 'Party']; style: optional
  planTrip: (days, style) => postJson('/api/trips/plan', { days, style: style || null }),
  getEventFunctions: () => request('/api/events/functions'),
  // Today's festival (Navratri: today's colour) or the next one within 3 weeks, or null
  getFestivalNow: () => request('/api/festivals/now'),
  // functions: e.g. ['haldi', 'mehendi', 'wedding']; style: optional
  planEvent: (functions, style) => postJson('/api/events/plan', { functions, style: style || null }),

  // Wear stats: not worn in N days, most worn, cost per wear
  getWearStats: (days = 30) => request(`/api/insights/wear?days=${days}`),
  // Record wearing an outfit that isn't saved (e.g. straight from the stylist)
  wearOutfit: (itemIds, occasion) => postJson('/api/history', { item_ids: itemIds, occasion }),

  getHistory: () => request('/api/history'),
  deleteHistoryEntry: (id) => request(`/api/history/${id}`, { method: 'DELETE' }),
};
