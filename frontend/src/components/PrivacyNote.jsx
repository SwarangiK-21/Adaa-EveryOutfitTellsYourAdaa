import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { api } from '../api.js';

export const PRIVACY_UPDATED = '20 October 2026';

/* The privacy note, in plain words: what Adaa keeps, why, who else is involved, and how to delete it. */
export default function PrivacyNote({ onClose }) {
  const [about, setAbout] = useState(null);
  useEffect(() => { api.about().then(setAbout).catch(() => setAbout(null)); }, []);
  useEffect(() => {
    const esc = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', esc);
    return () => window.removeEventListener('keydown', esc);
  }, [onClose]);

  const contact = about?.contact_email
    ? <a href={`mailto:${about.contact_email}`}>{about.contact_email}</a>
    : 'the person who runs this Adaa';

  // Shown on top of the whole page (not inside the section that opened it), so no outside styles leak in.
  return createPortal(
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <article className="modal privacy" role="dialog" aria-modal="true" aria-labelledby="privacy-title">
        <div className="modal-head">
          <div>
            <small>UPDATED {PRIVACY_UPDATED.toUpperCase()}</small>
            <h2 id="privacy-title">Privacy note</h2>
          </div>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close"><X size={18} /></button>
        </div>
        <div className="privacy-body">
          <h3>What Adaa keeps</h3>
          <ul>
            <li><b>Your account:</b> name, email, phone number, and your password as a scrambled hash (nobody can read it, not even Adaa).</li>
            <li><b>Your wardrobe:</b> photos and details of your clothes, saved looks, what you wore and when, and any photos you add of yourself in a look.</li>
            <li><b>One sign-in cookie</b>, so you stay logged in. No ads, no tracking, no analytics.</li>
          </ul>

          <h3>Why</h3>
          <p>Only to run your account and style outfits from your own clothes. Your name is used to talk to you; your email to sign in and reset your password; your phone number only to contact you about your account. Adaa never sells or shares your details, and never sends marketing.</p>

          <h3>Where it's kept</h3>
          <p>On the computer or server that runs this Adaa. Only you can see your wardrobe. Cleaning up photo backgrounds and auto-fill happen inside your own browser.</p>

          <h3>Other services, only if you use them</h3>
          <ul>
            <li><b>Weather:</b> if you add a city, your browser asks Open-Meteo for its forecast (only the city's location is sent).</li>
            <li><b>Voice requests:</b> your browser turns speech into text; Chrome uses Google's speech service for this.</li>
            <li><b>Password reset:</b> the email is sent through an email service.</li>
          </ul>

          <h3>Your choices</h3>
          <ul>
            <li>See and change your name and phone in <b>Preferences → Your account</b>.</li>
            <li><b>Delete your account</b> there at any time: your details, photos, looks and history are erased straight away. Any backup copies are cleared within 30 days.</li>
            <li>Questions about your data: {contact}.</li>
          </ul>

          <h3>Age</h3>
          <p>Adaa is for people aged 18 or older.</p>
        </div>
        <div className="modal-actions"><button type="button" className="primary" onClick={onClose}>Got it</button></div>
      </article>
    </div>,
    document.body,
  );
}
