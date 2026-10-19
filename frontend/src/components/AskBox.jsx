import React, { useEffect, useRef, useState } from 'react';
import { Send, Mic, MicOff } from 'lucide-react';

// The browser's own speech-to-text (Chrome and Edge). Chrome sends the audio to Google's speech
// service to turn it into text; nothing is recorded or kept by Adaa.
const SpeechRecognition = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition);

// Type (or say) a request in your own words, in English or Hinglish; Adaa shows what it understood.
export default function AskBox({ items, chat, asking, onAsk, onPick }) {
  const [text, setText] = useState('');
  const [listening, setListening] = useState(false);
  const [voiceNote, setVoiceNote] = useState('');
  const recogniser = useRef(null);
  useEffect(() => () => recogniser.current?.abort(), []);

  const send = (value) => {
    const message = value.trim();
    if (!message || asking) return;
    onAsk(message);
    setText('');
  };

  const listen = () => {
    if (listening) { recogniser.current?.stop(); return; }
    const r = new SpeechRecognition();
    r.lang = 'en-IN';             // Indian English: understands Hinglish like "kuch comfy"
    r.interimResults = true;
    r.maxAlternatives = 1;
    let heard = '';
    r.onresult = (e) => {
      heard = Array.from(e.results).map((res) => res[0].transcript).join(' ');
      setText(heard);
    };
    r.onerror = (e) => {
      setVoiceNote(e.error === 'not-allowed' || e.error === 'service-not-allowed'
        ? 'Microphone access was blocked. Allow it in the browser to speak to Adaa.'
        : e.error === 'no-speech' ? "I didn't hear anything. Try again?" : "Voice input didn't work this time. You can type instead.");
    };
    r.onend = () => {
      setListening(false);
      if (heard.trim()) send(heard);
    };
    recogniser.current = r;
    setVoiceNote('');
    setListening(true);
    r.start();
  };

  const firstClothing = items.find((i) => i.category === 'Clothing');
  const examples = [
    firstClothing ? `Style my ${firstClothing.name.toLowerCase()} for a party` : 'Something to wear to a party',
    'Aaj college ke liye kuch comfy',
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
          placeholder={listening ? 'Listening… say it in English or Hinglish' : 'Tell Adaa what you need, e.g. Style my black crop top for a party'}
          aria-label="Tell Adaa what you need"
        />
        {SpeechRecognition && (
          <button type="button" className={`mic ${listening ? 'on' : ''}`} onClick={listen} disabled={asking}
            aria-label={listening ? 'Stop listening' : 'Speak your request'} title={listening ? 'Stop listening' : 'Speak your request'}>
            {listening ? <MicOff size={17} /> : <Mic size={17} />}
          </button>
        )}
        <button aria-label="Send" disabled={asking}><Send size={17} /></button>
      </form>
      {listening && <p className="voice-note">Listening… Chrome turns your voice into text using Google's speech service.</p>}
      {!listening && voiceNote && <p className="voice-note">{voiceNote}</p>}

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
