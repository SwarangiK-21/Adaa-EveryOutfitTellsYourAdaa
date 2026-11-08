import React, { useEffect, useRef, useState } from 'react';
import { Eye, EyeOff, RefreshCw, Sparkles, Heart, Lock, MailCheck } from 'lucide-react';
import { api } from '../api.js';
import PrivacyNote from './PrivacyNote.jsx';
import TermsNote from './TermsNote.jsx';

const HAS_ACCOUNT = 'adaa.hasAccount';   // this browser has signed in before: start on "Log in"
const hadAccount = () => { try { return localStorage.getItem(HAS_ACCOUNT) === '1'; } catch { return false; } };

const TEXT = {
  signup: { eyebrow: 'WELCOME TO ADAA', title: <>Let's get to <em>know you</em></>, sub: 'Tell us a little about you. Adaa will call you by your name.', button: 'Create my account' },
  login: { eyebrow: 'WELCOME BACK', title: <>Good to see you <em>again</em></>, sub: 'Log in to your wardrobe.', button: 'Log in' },
  forgot: { eyebrow: 'FORGOT YOUR PASSWORD?', title: <>Let's get you <em>back in</em></>, sub: "Enter your account's email and we'll send you a link to choose a new password.", button: 'Send me a link' },
  reset: { eyebrow: 'ALMOST THERE', title: <>Choose a <em>new password</em></>, sub: 'Pick something you haven’t used for Adaa before, at least 8 characters.', button: 'Save my new password' },
};

/*
  Sign up (name, email, phone, password, privacy consent), log in, ask for a reset link, or choose a
  new password from an emailed link (resetToken). On sign-in, onSignedIn(user, mode) is called.
*/
export default function AuthScreen({ onSignedIn, resetToken, onResetDone, initialNotice = '' }) {
  const [mode, setMode] = useState(resetToken ? 'reset' : hadAccount() ? 'login' : 'signup');
  const [fields, setFields] = useState({ name: '', email: '', phone: '', password: '' });
  const [agreed, setAgreed] = useState(false);
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState(initialNotice);
  const [sent, setSent] = useState('');
  const [privacy, setPrivacy] = useState(false);
  const [terms, setTerms] = useState(false);
  const first = useRef(null);
  useEffect(() => { first.current?.focus(); setError(''); }, [mode]);
  useEffect(() => { if (initialNotice) setNotice(initialNotice); }, [initialNotice]);

  const set = (key) => (e) => setFields((f) => ({ ...f, [key]: e.target.value }));
  const go = (next) => { setMode(next); setSent(''); setNotice(''); };

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    if ((mode === 'signup' || mode === 'reset') && fields.password.length < 8) return setError('Please choose a password of at least 8 characters.');
    if (mode === 'signup' && !agreed) return setError('Please confirm you’re 18 or older and agree to the terms of use and privacy note.');
    setBusy(true);
    try {
      if (mode === 'forgot') {
        setSent((await api.forgotPassword(fields.email)).detail);
      } else if (mode === 'reset') {
        await api.resetPassword(resetToken, fields.password);
        onResetDone(true);
        setFields((f) => ({ ...f, password: '' }));
        setMode('login');
        setNotice('Your password is changed. Log in with your new password.');
      } else {
        const user = mode === 'signup'
          ? await api.signup({ ...fields, accept_privacy: agreed })
          : await api.login({ email: fields.email, password: fields.password });
        try { localStorage.setItem(HAS_ACCOUNT, '1'); } catch { /* fine */ }
        onSignedIn(user, mode);
        return;
      }
    } catch (err) {
      setError(err.message);
    }
    setBusy(false);
  };

  const t = TEXT[mode];
  const needsPassword = mode !== 'forgot';
  return (
    <div className="auth">
      <section className="auth-brand">
        <img src="/brand/adaa-logo-dark.svg" alt="Adaa — every outfit tells your adaa" />
        <ul>
          <li><Sparkles size={15} /> A personal stylist for the clothes you already own</li>
          <li><Heart size={15} /> Saree, kurta or crop top: looks made for you, by name</li>
          <li><Lock size={15} /> Your wardrobe is private to your account. No ads, no tracking</li>
        </ul>
      </section>

      <form className="auth-card" onSubmit={submit} noValidate>
        <small>{t.eyebrow}</small>
        <h1>{t.title}</h1>
        <p className="muted">{t.sub}</p>
        {notice && <p className="form-success" role="status">{notice}</p>}

        {sent ? (
          <p className="auth-sent" role="status"><MailCheck size={18} /> {sent} Check your spam folder too.</p>
        ) : (
          <>
            {mode === 'signup' && (
              <label className="field"><span>Your name</span>
                <input ref={first} value={fields.name} onChange={set('name')} maxLength={60} autoComplete="name" placeholder="Type your name" required />
              </label>
            )}
            {mode !== 'reset' && (
              <label className="field"><span>Email</span>
                <input ref={mode === 'signup' ? null : first} type="email" value={fields.email} onChange={set('email')} maxLength={120} autoComplete="email" placeholder="Type your email address" required />
              </label>
            )}
            {mode === 'signup' && (
              <label className="field"><span>Phone number</span>
                <input type="tel" value={fields.phone} onChange={set('phone')} maxLength={25} autoComplete="tel" placeholder="Type your phone number" required />
              </label>
            )}
            {needsPassword && (
              <label className="field"><span>{mode === 'reset' ? 'New password' : 'Password'}</span>
                <span className="password">
                  <input ref={mode === 'reset' ? first : null} type={show ? 'text' : 'password'} value={fields.password} onChange={set('password')} maxLength={128}
                    autoComplete={mode === 'login' ? 'current-password' : 'new-password'} placeholder={mode === 'login' ? 'Type your password' : mode === 'reset' ? 'Type a new password (at least 8 characters)' : 'Type a password (at least 8 characters)'} required />
                  <button type="button" className="icon-btn" onClick={() => setShow((s) => !s)} aria-label={show ? 'Hide password' : 'Show password'}>
                    {show ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </span>
              </label>
            )}
            {mode === 'login' && (
              <button type="button" className="text-btn forgot-link" onClick={() => go('forgot')}>Forgot password?</button>
            )}
            {mode === 'signup' && (
              <label className="consent">
                <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} aria-label="I'm 18 or older and agree to the terms of use and privacy note" />
                <span>I'm 18 or older and agree to the{' '}
                  <button type="button" className="text-btn" onClick={() => setTerms(true)}>terms of use</button> and{' '}
                  <button type="button" className="text-btn" onClick={() => setPrivacy(true)}>privacy note</button>.</span>
              </label>
            )}

            {error && <p className="form-error" role="alert">{error}</p>}
            <button className="primary" disabled={busy}>
              {busy ? <><RefreshCw size={15} className="spin" /> Just a moment…</> : t.button}
            </button>
          </>
        )}

        <p className="auth-switch">
          {mode === 'signup' && <>Already have an account? <button type="button" className="text-btn" onClick={() => go('login')}>Log in</button></>}
          {mode === 'login' && <>New to Adaa? <button type="button" className="text-btn" onClick={() => go('signup')}>Create an account</button></>}
          {(mode === 'forgot' || mode === 'reset') && <button type="button" className="text-btn" onClick={() => { if (mode === 'reset') onResetDone(false); go('login'); }}>Back to log in</button>}
        </p>
        <p className="auth-switch legal-links">
          <button type="button" className="text-btn" onClick={() => setTerms(true)}>Terms of use</button>
          <span aria-hidden="true"> · </span>
          <button type="button" className="text-btn" onClick={() => setPrivacy(true)}>Privacy note</button>
        </p>
      </form>
      {privacy && <PrivacyNote onClose={() => setPrivacy(false)} />}
      {terms && <TermsNote onClose={() => setTerms(false)} />}
    </div>
  );
}
