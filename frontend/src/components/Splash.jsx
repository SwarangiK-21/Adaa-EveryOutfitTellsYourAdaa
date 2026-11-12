import React, { useEffect, useState } from 'react';
import logo from '../assets/peheraav-splash.svg?raw';

const SHOW_MS = 6200;   // the logo animation (see .splash in styles.css)
const LEAVE_MS = 900;   // the curtain lifting away
const SPECKS = [[14, 22], [82, 16], [24, 74], [88, 66], [50, 10], [8, 50], [70, 86], [93, 40]];

/*
  The opening animation, once per visit: the ribbon P comes into focus, a glint runs over it,
  "Peheraav" writes itself, the gold thread draws, the tagline appears, then it lifts away like a
  curtain. A tap or key press skips it; with "reduce motion" switched on it's a short, still fade.
*/
export default function Splash({ name, onDone }) {
  const [leaving, setLeaving] = useState(false);
  const calm = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

  useEffect(() => {
    const t = window.setTimeout(() => setLeaving(true), calm ? 2000 : SHOW_MS);
    const skip = () => setLeaving(true);
    window.addEventListener('keydown', skip);
    return () => { window.clearTimeout(t); window.removeEventListener('keydown', skip); };
  }, [calm]);

  useEffect(() => {
    if (!leaving) return undefined;
    const t = window.setTimeout(onDone, calm ? 300 : LEAVE_MS);
    return () => window.clearTimeout(t);
  }, [leaving, calm, onDone]);

  return (
    <div className={`splash${leaving ? ' leaving' : ''}${calm ? ' calm' : ''}`} onClick={() => setLeaving(true)}
      role="img" aria-label="Peheraav AI — your wardrobe, styled by AI">
      {SPECKS.map(([x, y], i) => (
        <span key={i} className="splash-speck" style={{ left: `${x}%`, top: `${y}%`, animationDelay: `${0.4 + i * 0.4}s` }} />
      ))}
      <div className="splash-inner" dangerouslySetInnerHTML={{ __html: logo }} />
      <p className="splash-hello">{name ? `Hi, ${name}` : ' '}</p>
    </div>
  );
}
