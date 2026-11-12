import React from 'react';
import LegalDialog from './LegalDialog.jsx';

export const TERMS_UPDATED = '6 November 2026';

/* Terms of use, in plain words, for a free personal styling app. */
export default function TermsNote({ onClose }) {
  return (
    <LegalDialog title="Terms of use" updated={TERMS_UPDATED} onClose={onClose}>
      {(contact) => (
        <>
          <p>By creating an account you agree to these terms and to the privacy note. They're short on purpose.</p>

          <h3>Who can use Peheraav</h3>
          <p>People aged 18 or older. One account per person; keep your password to yourself. You're responsible for what happens in your account.</p>

          <h3>Your photos and details</h3>
          <ul>
            <li>Everything you add stays <b>yours</b>. You let Peheraav store and process it only to run the app for you (show your wardrobe, style outfits, make backups).</li>
            <li>Only upload photos you have the right to use. Photos of other people need their permission.</li>
            <li>No illegal, hateful, sexual or otherwise harmful content. Accounts that break this may be removed.</li>
          </ul>

          <h3>Styling suggestions</h3>
          <p>Peheraav's suggestions are friendly ideas made by simple rules from the clothes you add. They aren't professional advice, and every look is your choice.</p>

          <h3>The service</h3>
          <ul>
            <li>Peheraav is free and offered <b>as it is</b>. We try to keep it running and your data safe and backed up, but can't promise it will never be unavailable or lose data.</li>
            <li>Peheraav may change, or stop. If it's going to stop, we'll try to tell you in advance so you can keep what you need.</li>
            <li>You can stop using Peheraav and delete your account at any time in Preferences.</li>
          </ul>

          <h3>Limits</h3>
          <p>To keep things fair on a small server, there are limits (for example on pieces, saved looks and how often some actions can be repeated).</p>

          <h3>Law and contact</h3>
          <p>These terms follow the laws of India. Questions: {contact}.</p>
        </>
      )}
    </LegalDialog>
  );
}
