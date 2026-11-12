import React, { useCallback, useEffect, useRef, useState } from 'react';
import { api } from './api.js';
import App from './App.jsx';
import AuthScreen from './components/AuthScreen.jsx';
import Splash from './components/Splash.jsx';
import { UserContext, setStorageUser } from './user.js';

const HELLO = 'peheraav.hello';   // a welcome message to show once, after a reload
const SPLASH = 'peheraav.splashSeen';   // the opening animation plays once per visit (per tab)

/* Shows the sign-in screen until someone is signed in, then the app (which knows who you are). */
export default function Root() {
  const [user, setUser] = useState(undefined);   // undefined = still checking
  const [hello, setHello] = useState(() => {
    try { const m = sessionStorage.getItem(HELLO); sessionStorage.removeItem(HELLO); return m || ''; } catch { return ''; }
  });
  const hadUser = useRef(false);
  // Opened from a "choose a new password" email: https://.../#reset=<token> (the part after # never reaches the server)
  const [resetToken, setResetToken] = useState(() => new URLSearchParams(window.location.hash.slice(1)).get('reset')
    || new URLSearchParams(window.location.search).get('reset'));
  const resetDone = (changed) => {
    window.history.replaceState(null, '', window.location.pathname);   // the link works once; drop it from the address bar and history
    setResetToken(null);
    if (changed) setUser(null);   // a new password signs out every browser, this one too
  };
  const [splash, setSplash] = useState(() => { try { return sessionStorage.getItem(SPLASH) !== '1'; } catch { return false; } });
  const endSplash = useCallback(() => { try { sessionStorage.setItem(SPLASH, '1'); } catch { /* fine */ } setSplash(false); }, []);

  // Opened from a "confirm your email" link (#verify=<token>): confirm first, then load the account.
  const [verified, setVerified] = useState('');
  useEffect(() => {
    const verifyToken = new URLSearchParams(window.location.hash.slice(1)).get('verify');
    let confirm = Promise.resolve();
    if (verifyToken) {
      window.history.replaceState(null, '', window.location.pathname);   // the link works once
      confirm = api.verifyEmail(verifyToken)
        .then(() => setVerified('Your email is confirmed. Thank you!'))
        .catch((err) => setVerified(err.message));
    }
    confirm.finally(() => api.me()
      .then((u) => { setStorageUser(u.id); hadUser.current = true; setUser(u); })
      .catch(() => setUser(null)));
    // A session that ended (logged out elsewhere, or expired) shows the sign-in screen again.
    const signedOut = () => setUser(null);
    window.addEventListener('peheraav-signed-out', signedOut);
    return () => window.removeEventListener('peheraav-signed-out', signedOut);
  }, []);

  const signedIn = (u, mode) => {
    const message = mode === 'signup'
      ? (u.moved_items ? `Welcome to Peheraav, ${u.first_name}! Your ${u.moved_items} pieces are now safely in your account.`
        : `Welcome to Peheraav, ${u.first_name}! Let's start with your first piece.`)
      : `Welcome back, ${u.first_name}!`;
    if (hadUser.current) {
      // Someone was signed in earlier on this page: start fresh so nothing of theirs lingers.
      try { sessionStorage.setItem(HELLO, message); } catch { /* fine */ }
      window.location.reload();
      return;
    }
    setStorageUser(u.id);
    hadUser.current = true;
    setHello(message);
    setUser(u);
  };

  const logout = async () => {
    try { await api.logout(); } catch { /* signed out anyway */ }
    window.location.reload();   // clears everything of this account from the page
  };

  let page;
  if (user === undefined) page = splash ? null : <div className="auth-loading"><img src="/brand/peheraav-mark.svg" alt="Peheraav" /></div>;
  else if (!user || resetToken) page = <AuthScreen onSignedIn={signedIn} resetToken={resetToken} onResetDone={resetDone} initialNotice={verified} />;
  else page = <UserContext.Provider value={{ user, setUser, logout }}><App hello={verified || hello} /></UserContext.Provider>;
  // The opening animation stays in the same place while the page underneath changes, so it plays once, smoothly.
  return <>{splash && <Splash name={user?.first_name} onDone={endSplash} />}{page}</>;
}
