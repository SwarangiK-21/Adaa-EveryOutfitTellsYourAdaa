import React, { useState } from 'react';
import { Check, LogOut, RefreshCw } from 'lucide-react';
import { api } from '../api.js';
import { useUser } from '../user.js';

// Preferences section: your name and phone (your email is how you sign in), and log out.
export default function AccountSettings({ notify }) {
  const { user, setUser, logout } = useUser();
  const [name, setName] = useState(user.name);
  const [phone, setPhone] = useState(user.phone);
  const [busy, setBusy] = useState(false);
  const changed = name.trim() !== user.name || phone.trim() !== user.phone;

  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const updated = await api.updateMe({ name, phone });
      setUser(updated);
      notify(`Saved. Nice to meet you properly, ${updated.first_name}!`);
    } catch (err) {
      notify(err.message);
    } finally {
      setBusy(false);
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
          <button className="primary" disabled={busy || !changed}>
            {busy ? <RefreshCw size={14} className="spin" /> : <Check size={14} />} Save
          </button>
          <button type="button" className="secondary" onClick={logout}><LogOut size={14} /> Log out</button>
        </div>
      </form>
    </section>
  );
}
