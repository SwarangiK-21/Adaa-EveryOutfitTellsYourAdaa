// Small helpers for talking to the Adaa backend (proxied by Vite to port 8000).

export class ApiError extends Error {}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(path, options);
  } catch {
    throw new ApiError("Can't reach the Adaa server. Is the backend running?");
  }
  if (res.status === 204) return null;

  const body = await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status >= 500 && !body) {
      throw new ApiError("Can't reach the Adaa server. Is the backend running?");
    }
    const detail = body?.detail;
    const message = Array.isArray(detail)
      ? detail.map((d) => (typeof d === 'string' ? d : d.msg)).join(' · ')
      : detail || `Something went wrong (error ${res.status}).`;
    throw new ApiError(message);
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
  getOptions: () => request('/api/options'),

  listItems: ({ search = '', category = '' } = {}) => {
    const params = new URLSearchParams();
    if (search.trim()) params.set('search', search.trim());
    if (category) params.set('category', category);
    const query = params.toString();
    return request(`/api/items${query ? `?${query}` : ''}`);
  },

  createItem: (fields, photo) =>
    request('/api/items', { method: 'POST', body: toFormData(fields, photo) }),

  updateItem: (id, fields, photo) =>
    request(`/api/items/${id}`, { method: 'PUT', body: toFormData(fields, photo) }),

  deleteItem: (id) => request(`/api/items/${id}`, { method: 'DELETE' }),

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

  getHistory: () => request('/api/history'),
  deleteHistoryEntry: (id) => request(`/api/history/${id}`, { method: 'DELETE' }),
};
