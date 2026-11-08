import React from 'react';
import LegalDialog from './LegalDialog.jsx';

export const PRIVACY_UPDATED = '8 November 2026';

/* The privacy note, in plain words: what Adaa keeps, why, who else is involved, and how to delete it. */
export default function PrivacyNote({ onClose }) {
  return (
    <LegalDialog title="Privacy note" updated={PRIVACY_UPDATED} onClose={onClose}>
      {(contact) => (
        <>
          <h3>What Adaa keeps</h3>
          <ul>
            <li><b>Your account:</b> name, email, phone number, and your password as a scrambled hash (nobody can read it, not even Adaa).</li>
            <li><b>Your wardrobe:</b> photos and details of your clothes, saved looks, what you wore and when, and any photos you add of yourself in a look. Photos are shrunk and their hidden details (such as the place they were taken) are removed before they're saved.</li>
            <li><b>One sign-in cookie</b>, so you stay logged in. No ads, no tracking, no analytics.</li>
            <li><b>Server logs:</b> the time, your internet address and the page requested, to keep Adaa secure and fix problems. Deleted after 30 days.</li>
          </ul>

          <h3>Why</h3>
          <p>Only to run your account and style outfits from your own clothes. Your name is used to talk to you; your email to sign in and reset your password; your phone number only to contact you about your account. Adaa never sells or shares your details, and never sends marketing.</p>

          <h3>Where it's kept</h3>
          <p>On the server that runs this Adaa, with a nightly backup copy kept with a storage service (Backblaze B2). Only you can see your wardrobe. Cleaning up photo backgrounds and auto-fill happen inside your own browser.</p>

          <h3>Other services, only if you use them</h3>
          <ul>
            <li><b>Weather:</b> if you add a city, your browser asks Open-Meteo for its forecast (only the city's location is sent).</li>
            <li><b>Voice requests:</b> your browser turns speech into text; Chrome uses Google's speech service for this.</li>
            <li><b>Password reset:</b> the email is sent through an email service.</li>
          </ul>

          <h3>Your choices</h3>
          <ul>
            <li>See and change your details in <b>Preferences → Your account</b>.</li>
            <li><b>Delete your account</b> there at any time: your details, photos, looks and history are erased straight away. Backup copies are cleared within 30 days.</li>
            <li>Questions about your data: {contact}.</li>
          </ul>

          <h3>Age</h3>
          <p>Adaa is for people aged 18 or older.</p>
        </>
      )}
    </LegalDialog>
  );
}
