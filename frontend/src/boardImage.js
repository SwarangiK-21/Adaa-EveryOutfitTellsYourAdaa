// Saves an outfit board as a PNG, drawn from the pictures exactly where they appear on screen,
// with Adaa's cream background and the look's name at the bottom. Nothing leaves the device.

const W = 900;
const H = 1500;   // the board's 3:5 shape

function slug(text) {
  return (text || 'look').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60) || 'look';
}

async function ready(img) {
  if (!img.complete) await new Promise((resolve) => { img.onload = resolve; img.onerror = resolve; });
  try { await img.decode(); } catch { /* drawn as far as it loaded */ }
}

export async function downloadBoard(frame, title) {
  const board = frame.querySelector('.board');
  if (!board) throw new Error('Nothing to save yet.');
  const area = frame.getBoundingClientRect();
  const scale = W / area.width;
  const canvas = document.createElement('canvas');
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d');

  // Background: the same soft cream as the board.
  const bg = ctx.createRadialGradient(W / 2, H * 0.3, 0, W / 2, H * 0.3, H * 0.85);
  bg.addColorStop(0, '#fff9fc');
  bg.addColorStop(0.6, '#f6e7ef');
  bg.addColorStop(1, '#ecd6e2');
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, W, H);

  // Pieces, back to front, each with the soft shadow it has on screen.
  const slots = [...board.querySelectorAll('.board-slot')]
    .sort((a, b) => (Number(a.style.zIndex) || 0) - (Number(b.style.zIndex) || 0));
  for (const slot of slots) {
    const img = slot.querySelector('img');
    if (!img) continue;
    await ready(img);
    if (!img.naturalWidth) continue;
    const r = img.getBoundingClientRect();
    ctx.save();
    ctx.shadowColor = 'rgba(0, 0, 0, 0.12)';
    ctx.shadowBlur = 10 * scale;
    ctx.shadowOffsetY = 6 * scale;
    ctx.drawImage(img, (r.left - area.left) * scale, (r.top - area.top) * scale, r.width * scale, r.height * scale);
    ctx.restore();
  }

  // The look's name, small, at the bottom.
  ctx.fillStyle = '#5B1F3F';   // logo plum
  ctx.textAlign = 'center';
  ctx.font = `600 ${Math.round(W * 0.03)}px "Playfair Display", Georgia, serif`;
  // Capitalised, as shown on screen.
  const name = (title || 'My look').replace(/(^|\s)(\p{L})/gu, (m, space, letter) => space + letter.toUpperCase());
  ctx.fillText(name, W / 2, H - W * 0.075);
  ctx.fillStyle = '#94712F';   // brand gold
  ctx.font = `${Math.round(W * 0.019)}px "DM Sans", Arial, sans-serif`;
  ctx.fillText('Styled from my own wardrobe · Adaa', W / 2, H - W * 0.04);

  const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
  if (!blob) throw new Error("Couldn't make the image.");
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `adaa-${slug(title)}.png`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
