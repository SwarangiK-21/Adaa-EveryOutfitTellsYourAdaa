import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { api } from '../api.js';

// Shared by the privacy note and the terms: a pop-up over the whole page (Esc or "Got it" closes it).
// children(contact) gets the contact line: the email set by whoever runs this Adaa, or a fallback.
export default function LegalDialog({ title, updated, onClose, children }) {
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

  // On top of the whole page (not inside the section that opened it), so no outside styles leak in.
  return createPortal(
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <article className="modal privacy" role="dialog" aria-modal="true" aria-labelledby="legal-title">
        <div className="modal-head">
          <div>
            <small>UPDATED {updated.toUpperCase()}</small>
            <h2 id="legal-title">{title}</h2>
          </div>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close"><X size={18} /></button>
        </div>
        <div className="privacy-body">{children(contact)}</div>
        <div className="modal-actions"><button type="button" className="primary" onClick={onClose}>Got it</button></div>
      </article>
    </div>,
    document.body,
  );
}
