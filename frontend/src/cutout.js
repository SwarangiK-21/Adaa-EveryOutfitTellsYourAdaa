// Cuts a garment out of its photo (removes the background), in a background thread.
// The work happens in cutout.worker.js so the page stays responsive, even in a hidden tab.
// The model (~179 MB) is served by the Adaa backend and downloaded by the browser once.

let worker = null;
let nextId = 0;
const waiting = new Map();

function getWorker() {
  if (!worker) {
    worker = new Worker(new URL('./cutout.worker.js', import.meta.url), { type: 'module' });
    worker.onmessage = ({ data: { id, blob, error } }) => {
      const job = waiting.get(id);
      waiting.delete(id);
      if (!job) return;
      if (error) job.reject(new Error(error));
      else job.resolve(blob);
    };
    worker.onerror = (e) => {
      waiting.forEach((job) => job.reject(new Error(e.message || 'The cut-out helper stopped.')));
      waiting.clear();
      worker = null;
    };
  }
  return worker;
}

// crop: optional { x, y, w, h } in 0..1 of the photo, to keep only part of it.
// parts: clothes-parser labels to keep (see partsFor in cutoutQueue.js), or null for background removal only.
// Resolves to a PNG Blob with a transparent background, trimmed to the garment.
export function makeCutout(imageUrl, crop = null, parts = null) {
  const url = new URL(imageUrl, window.location.href).href; // the worker needs a full address
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    waiting.set(id, { resolve, reject });
    getWorker().postMessage({ id, url, crop, parts });
  });
}
