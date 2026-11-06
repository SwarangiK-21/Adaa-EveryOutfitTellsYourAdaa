import React from 'react';
import { createRoot } from 'react-dom/client';
import Root from './Root.jsx';
import ErrorBoundary from './components/ErrorBoundary.jsx';
// Fonts are served by Adaa itself (no request to Google): DM Sans and Playfair Display, OFL licence.
import '@fontsource/dm-sans/400.css';
import '@fontsource/dm-sans/500.css';
import '@fontsource/dm-sans/600.css';
import '@fontsource/dm-sans/700.css';
import '@fontsource/playfair-display/500.css';
import '@fontsource/playfair-display/600.css';
import '@fontsource/playfair-display/500-italic.css';
import './styles.css';
createRoot(document.getElementById('root')).render(<React.StrictMode><ErrorBoundary><Root /></ErrorBoundary></React.StrictMode>);