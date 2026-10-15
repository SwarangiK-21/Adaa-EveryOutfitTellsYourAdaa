import React, { useState } from 'react';
import { Send } from 'lucide-react';

// Type a request in your own words; Adaa shows what it understood.
export default function AskBox({ items, chat, asking, onAsk, onPick }) {
  const [text, setText] = useState('');

  const send = (value) => {
    const message = value.trim();
    if (!message || asking) return;
    onAsk(message);
    setText('');
  };

  const firstClothing = items.find((i) => i.category === 'Clothing');
  const examples = [
    firstClothing ? `Style my ${firstClothing.name.toLowerCase()} for a party` : 'Something to wear to a party',
    'Something comfy for college',
    'Elegant traditional look for a wedding',
    'Dinner date, something black',
  ];

  return (
    <section className="ask">
      <form className="compose" onSubmit={(e) => { e.preventDefault(); send(text); }}>
        <input
          value={text}
          maxLength={300}
          onChange={(e) => setText(e.target.value)}
          placeholder="Tell Adaa what you need, e.g. Style my black crop top for a party"
          aria-label="Tell Adaa what you need"
        />
        <button aria-label="Send" disabled={asking}><Send size={17} /></button>
      </form>

      {!chat && (
        <div className="prompts">
          <small>TRY SAYING</small>
          {examples.map((s) => <button type="button" key={s} onClick={() => send(s)}>{s} ↗</button>)}
        </div>
      )}

      {chat && (
        <div className="ask-thread">
          <div className="user-bubble">{chat.text}</div>
          <div className="bubble">
            <small>ADAA</small>
            {chat.error ? <p>{chat.error}</p> : <Understanding chat={chat} onPick={onPick} />}
          </div>
        </div>
      )}
    </section>
  );
}

function Understanding({ chat, onPick }) {
  const { parsed, refining, keptOccasion, picked } = chat;
  const understood = picked ? [...parsed.understood, `Building around your ${picked}`] : parsed.understood;

  return (
    <>
      {understood.length > 0 ? (
        <p>
          {refining ? `Keeping ${keptOccasion} and updating: ` : 'Here’s what I understood: '}
          {understood.map((u) => <span className="tag" key={u}>{u}</span>)}
        </p>
      ) : (
        <p>I couldn’t pick out any details from that. Try naming an occasion, a piece you own, a colour or a style.</p>
      )}

      {parsed.not_found.map((piece) => (
        <p key={piece} className="warn">
          I couldn’t find a <b>{piece}</b> in your wardrobe, so I’ll style you with pieces you do have.
          You can add it in My Wardrobe.
        </p>
      ))}

      {parsed.ambiguous.length > 0 && (
        <div className="which">
          <p>Which one did you mean?</p>
          {parsed.ambiguous.map((a) => (
            <button type="button" className="secondary" key={a.id} onClick={() => onPick(a.id)}>{a.name}</button>
          ))}
        </div>
      )}

      {parsed.missing.includes('occasion') && !refining && (
        <p><b>Where are you going?</b> Pick an occasion in the form below and press Style me.</p>
      )}
    </>
  );
}
