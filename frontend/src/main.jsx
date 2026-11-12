import React from 'react';
import { createRoot } from 'react-dom/client';
import Root from './Root.jsx';
import ErrorBoundary from './components/ErrorBoundary.jsx';
// Fonts are served by Peheraav itself (no request to Google): DM Sans and Playfair Display, OFL licence.
import '@fontsource/dm-sans/400.css';
import '@fontsource/dm-sans/500.css';
import '@fontsource/dm-sans/600.css';
import '@fontsource/dm-sans/700.css';
import '@fontsource/playfair-display/500.css';
import '@fontsource/playfair-display/600.css';
import '@fontsource/playfair-display/500-italic.css';
import './styles.css';

// The app used to be called "Adaa": move this browser's saved settings (preferences, city, weather)
// from the old "adaa." keys to the new "peheraav." ones, once, so nobody loses them.
try {
  for (const key of Object.keys(localStorage)) {
    if (!key.startsWith('adaa.')) continue;
    const renamed = 'peheraav.' + key.slice(5);
    if (localStorage.getItem(renamed) === null) localStorage.setItem(renamed, localStorage.getItem(key));
    localStorage.removeItem(key);
  }
} catch { /* storage blocked (private mode): nothing to move */ }

createRoot(document.getElementById('root')).render(<React.StrictMode><ErrorBoundary><Root /></ErrorBoundary></React.StrictMode>);