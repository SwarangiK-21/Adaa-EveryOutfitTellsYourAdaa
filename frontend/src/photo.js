// Photos are re-drawn in the browser before upload: upright, at most 1600 px on the long side,
// and without hidden metadata (camera details, the GPS location where they were taken).
// Smaller files upload faster and load faster on phones; the server strips metadata again anyway.

const MAX_SIDE = 1600;
export const MAX_ORIGINAL_MB = 25;   // what you can pick; it's shrunk well under the server's 5 MB

const canvasBlob = (canvas, type, quality) => new Promise((resolve) => canvas.toBlob(resolve, type, quality));

export async function preparePhoto(file) {
  if (!(file instanceof Blob) || !/^image\/(jpeg|png|webp)$/.test(file.type)) return file;
  try {
    const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
    const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
    const width = Math.max(1, Math.round(bitmap.width * scale));
    const height = Math.max(1, Math.round(bitmap.height * scale));
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    const isJpeg = file.type === 'image/jpeg';
    if (isJpeg) { ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, width, height); }
    ctx.drawImage(bitmap, 0, 0, width, height);
    bitmap.close?.();

    // JPEG stays JPEG. PNG / WebP may be see-through: WebP keeps that and is small; PNG if WebP isn't supported.
    let blob = await canvasBlob(canvas, isJpeg ? 'image/jpeg' : 'image/webp', 0.86);
    if (blob && !isJpeg && blob.type !== 'image/webp') blob = await canvasBlob(canvas, 'image/png');
    if (!blob) return file;
    // A small PNG/WebP that didn't need shrinking can stay as it is (the server still removes its metadata).
    // JPEGs are always replaced: phones store their rotation in the metadata that gets removed.
    if (!isJpeg && scale === 1 && blob.size >= file.size) return file;
    const ext = { 'image/jpeg': 'jpg', 'image/webp': 'webp', 'image/png': 'png' }[blob.type] || 'jpg';
    const base = (file.name || 'photo').replace(/\.[^.]+$/, '');
    return new File([blob], `${base}.${ext}`, { type: blob.type });
  } catch {
    return file;   // the browser couldn't read it here; the server still checks and cleans it
  }
}
