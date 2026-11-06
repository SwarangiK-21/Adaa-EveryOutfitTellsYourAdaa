import React, { useState } from 'react';
import { Check, LogOut, RefreshCw, KeyRound, Trash2, ShieldCheck, FileText } from 'lucide-react';
import { api } from '../api.js';
import { useUser } from '../user.js';
import PrivacyNote from './PrivacyNote.jsx';
import TermsNote from './TermsNote.jsx';

// Forget this account's browser storage (preferences, city, ...) once the account is deleted.
function forgetLocalData(uid) {
  try {
    Object.keys(localStorage).filter((k) => k.endsWith(`.u${uid}`)).forEach((k) => localStorage.removeItem(k));
  } catch { /* fine */ }
}

/*
  Preferences section: your name and phone (your email is how you sign in), change your password,
  the privacy note, log out, and delete your account.
*/
export default function AccountSettings({ notify }) {
  const { user, setUser, logout } = useUser();
  const [name, setName] = useState(user.name);
  const [phone, setPhone] = useState(user.phone);
  const [busy, setBusy] = useState('');
  const [pw, setPw] = useState({ current: '', next: '' });
  const [pwError, setPwError] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [deletePw, setDeletePw] = useState('');
  const [deleteError, setDeleteError] = useState('');
  const [privacy, setPrivacy] = useState(false);
  const [terms, setTerms] = useState(false);
  const changed = name.trim() !== user.name || phone.trim() !== user.phone;

  const save = async (e) => {
    e.preventDefault();
    setBusy('details');
    try {
      const updated = await api.updateMe({ name, phone });
      setUser(updated);
      notify(`Saved. Nice to meet you properly, ${updated.first_name}!`);
    } catch (err) {
      notify(err.message);
    } finally {
      setBusy('');
    }
  };

  const changePassword = async (e) => {
    e.preventDefault();
    setPwError('');
    if (pw.next.length < 8) return setPwError('Please choose a new password of at least 8 characters.');
    setBusy('password');
    try {
      await api.changePassword(pw.current, pw.next);
      setPw({ current: '', next: '' });
      notify(`Password changed, ${user.first_name}. Other devices are signed out.`);
    } catch (err) {
      setPwError(err.message);
    } finally {
      setBusy('');
    }
  };

  const deleteAccount = async (e) => {
    e.preventDefault();
    setDeleteError('');
    setBusy('delete');
    try {
      await api.deleteAccount(deletePw);
      forgetLocalData(user.id);
      window.location.reload();
    } catch (err) {
      setDeleteError(err.message);
      setBusy('');
    }
  };

  return (
    <section className="account-settings">
      <h3>Your account</h3>
      <form onSubmit={save}>
        <label className="field"><span>Name <i>(Adaa calls you {name.trim().split(/\s+/)[0] || '…'})</i></span>
          <input value={name} onChange={(e) => setName(e.target.value)} maxLength={60} autoComplete="name" />
        </label>
        <label className="field"><span>Phone number</span>
          <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} maxLength={25} autoComplete="tel" />
        </label>
        <label className="field"><span>Email <i>(your sign-in)</i></span>
          <input value={user.email} disabled />
        </label>
        <div className="account-actions">
          <button className="primary" disabled={busy === 'details' || !changed}>
            {busy === 'details' ? <RefreshCw size={14} className="spin" /> : <Check size={14} />} Save
          </button>
          <button type="button" className="secondary" onClick={logout}><LogOut size={14} /> Log out</button>
        </div>
      </form>

      <h4><KeyRound size={14} /> Change password</h4>
      <form onSubmit={changePassword}>
        <label className="field"><span>Current password</span>
          <input type="password" value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} maxLength={128} autoComplete="current-password" />
        </label>
        <label className="field"><span>New password <i>(8+ characters)</i></span>
          <input type="password" value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} maxLength={128} autoComplete="new-password" />
        </label>
        <div className="account-actions">
          <button className="secondary" disabled={busy === 'password' || !pw.current || !pw.next}>
            {busy === 'password' ? <RefreshCw size={14} className="spin" /> : <KeyRound size={14} />} Change password
          </button>
        </div>
        {pwError && <p className="form-error account-wide" role="alert">{pwError}</p>}
      </form>

      <div className="account-footer">
        <span className="legal-links">
          <button type="button" className="text-btn" onClick={() => setPrivacy(true)}><ShieldCheck size={13} /> Privacy note</button>
          <button type="button" className="text-btn" onClick={() => setTerms(true)}><FileText size={13} /> Terms of use</button>
        </span>
        {!deleting && (
          <button type="button" className="text-btn danger-link" onClick={() => setDeleting(true)}><Trash2 size={13} /> Delete my account</button>
        )}
      </div>

      {deleting && (
        <form className="danger-zone" onSubmit={deleteAccount}>
          <p><b>Delete your account for good?</b> Your details, every piece and photo, your saved looks and your outfit history are erased straight away. This can't be undone.</p>
          <label className="field"><span>Type your password to confirm</span>
            <input type="password" value={deletePw} onChange={(e) => setDeletePw(e.target.value)} maxLength={128} autoComplete="current-password" autoFocus />
          </label>
          {deleteError && <p className="form-error" role="alert">{deleteError}</p>}
          <div className="account-actions">
            <button className="danger" disabled={busy === 'delete' || !deletePw}>
              {busy === 'delete' ? <RefreshCw size={14} className="spin" /> : <Trash2 size={14} />} Delete everything
            </button>
            <button type="button" className="secondary" onClick={() => { setDeleting(false); setDeletePw(''); setDeleteError(''); }}>Keep my account</button>
          </div>
        </form>
      )}
      {privacy && <PrivacyNote onClose={() => setPrivacy(false)} />}
      {terms && <TermsNote onClose={() => setTerms(false)} />}
    </section>
  );
}
