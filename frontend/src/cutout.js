// Cuts a garment out of its photo (removes the background), in a background thread.
// The work happens in cutout.worker.js so the page stays responsive, even in a hidden tab.
// The model (~179 MB) is served by the Peheraav backend and downloaded by the browser once.

const workers = {};   // 'cutout' (background queue) and 'analyse' (reading a new photo right away)
let nextId = 0;
const waiting = new Map();

function getWorker(name) {
  if (!workers[name]) {
    const worker = new Worker(new URL('./cutout.worker.js', import.meta.url), { type: 'module' });
    worker.onmessage = ({ data: { id, blob, result, error } }) => {
      const job = waiting.get(id);
      waiting.delete(id);
      if (!job) return;
      if (error) job.reject(new Error(error));
      else job.resolve(result !== undefined ? result : blob);
    };
    worker.onerror = (e) => {
      waiting.forEach((job) => job.worker === name && job.reject(new Error(e.message || 'The cut-out helper stopped.')));
      waiting.forEach((job, id) => job.worker === name && waiting.delete(id));
      delete workers[name];
    };
    workers[name] = worker;
  }
  return workers[name];
}

function send(name, message) {
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    waiting.set(id, { resolve, reject, worker: name });
    getWorker(name).postMessage({ id, ...message });
  });
}

// crop: optional { x, y, w, h } in 0..1 of the photo, to keep only part of it.
// parts: clothes-parser labels to keep (see partsFor in cutoutQueue.js), or null for background removal only.
// Resolves to a PNG Blob with a transparent background, trimmed to the garment.
export function makeCutout(imageUrl, crop = null, parts = null) {
  const url = new URL(imageUrl, window.location.href).href; // the worker needs a full address
  return send('cutout', { url, crop, parts });
}

// Reads a new photo: { category, item_type, style?, colour } or null if it isn't a garment the
// clothes parser knows (jewellery, watches...). Uses its own helper so it never waits behind the
// background cut-outs.
export function analysePhoto(imageUrl) {
  const url = new URL(imageUrl, window.location.href).href;
  return send('analyse', { url, task: 'analyse' });
}
