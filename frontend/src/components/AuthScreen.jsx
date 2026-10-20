import React, { useEffect, useRef, useState } from 'react';
import { Eye, EyeOff, RefreshCw, Sparkles, Heart, Lock } from 'lucide-react';
import { api } from '../api.js';

const HAS_ACCOUNT = 'adaa.hasAccount';   // this browser has signed in before: start on "Log in"
const hadAccount = () => { try { return localStorage.getItem(HAS_ACCOUNT) === '1'; } catch { return false; } };

/*
  Sign up (name, email, phone, password) or log in. On success, onSignedIn(user) is called.
  Passwords go to the local Adaa backend only, where they are stored as salted hashes.
*/
export default function AuthScreen({ onSignedIn }) {
  const [mode, setMode] = useState(hadAccount() ? 'login' : 'signup');
  const [fields, setFields] = useState({ name: '', email: '', phone: '', password: '' });
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const first = useRef(null);
  useEffect(() => { first.current?.focus(); setError(''); }, [mode]);

  const set = (key) => (e) => setFields((f) => ({ ...f, [key]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    if (mode === 'signup' && fields.password.length < 8) return setError('Please choose a password of at least 8 characters.');
    setBusy(true);
    try {
      const user = mode === 'signup'
        ? await api.signup(fields)
        : await api.login({ email: fields.email, password: fields.password });
      try { localStorage.setItem(HAS_ACCOUNT, '1'); } catch { /* fine */ }
      onSignedIn(user, mode);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <div className="auth">
      <section className="auth-brand">
        <img src="/brand/adaa-logo-dark.svg" alt="Adaa — every outfit tells your adaa" />
        <ul>
          <li><Sparkles size={15} /> A personal stylist for the clothes you already own</li>
          <li><Heart size={15} /> Saree, kurta or crop top: looks made for you, by name</li>
          <li><Lock size={15} /> Your wardrobe stays private to your account, on this computer</li>
        </ul>
      </section>

      <form className="auth-card" onSubmit={submit} noValidate>
        <small>{mode === 'signup' ? 'WELCOME TO ADAA' : 'WELCOME BACK'}</small>
        <h1>{mode === 'signup' ? <>Let's get to <em>know you</em></> : <>Good to see you <em>again</em></>}</h1>
        <p className="muted">{mode === 'signup'
          ? "Tell us a little about you. Adaa will call you by your name."
          : 'Log in to your wardrobe.'}</p>

        {mode === 'signup' && (
          <label className="field"><span>Your name</span>
            <input ref={first} value={fields.name} onChange={set('name')} maxLength={60} autoComplete="name" placeholder="e.g. Swarangi Kothawade" required />
          </label>
        )}
        <label className="field"><span>Email</span>
          <input ref={mode === 'login' ? first : null} type="email" value={fields.email} onChange={set('email')} maxLength={120} autoComplete="email" placeholder="you@example.com" required />
        </label>
        {mode === 'signup' && (
          <label className="field"><span>Phone number</span>
            <input type="tel" value={fields.phone} onChange={set('phone')} maxLength={25} autoComplete="tel" placeholder="+91 98765 43210" required />
          </label>
        )}
        <label className="field"><span>Password</span>
          <span className="password">
            <input type={show ? 'text' : 'password'} value={fields.password} onChange={set('password')} maxLength={128}
              autoComplete={mode === 'signup' ? 'new-password' : 'current-password'} placeholder={mode === 'signup' ? 'At least 8 characters' : ''} required />
            <button type="button" className="icon-btn" onClick={() => setShow((s) => !s)} aria-label={show ? 'Hide password' : 'Show password'}>
              {show ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          </span>
        </label>

        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="primary" disabled={busy}>
          {busy ? <><RefreshCw size={15} className="spin" /> Just a moment…</> : mode === 'signup' ? 'Create my account' : 'Log in'}
        </button>
        <p className="auth-switch">
          {mode === 'signup' ? 'Already have an account?' : 'New to Adaa?'}{' '}
          <button type="button" className="text-btn" onClick={() => setMode(mode === 'signup' ? 'login' : 'signup')}>
            {mode === 'signup' ? 'Log in' : 'Create an account'}
          </button>
        </p>
      </form>
    </div>
  );
}
