import React, { useEffect, useRef, useState } from 'react';
import { LayoutDashboard, Shirt, MessageCircle, Heart, SlidersHorizontal, Sparkles, ArrowUpRight, ChevronRight, Menu, X, Check, Luggage, ShoppingBag, BarChart3, Clock, Gem, LogOut } from 'lucide-react';
import { api } from './api.js';
import Heading from './components/Heading.jsx';
import Wardrobe from './pages/Wardrobe.jsx';
import Stylist from './pages/Stylist.jsx';
import SavedLooks from './pages/SavedLooks.jsx';
import TripPlanner from './pages/TripPlanner.jsx';
import WeddingPlanner from './pages/WeddingPlanner.jsx';
import ShopSmart from './pages/ShopSmart.jsx';
import WearStats from './pages/WearStats.jsx';
import { queueMissingCutouts } from './cutoutQueue.js';
import WeatherSettings from './components/WeatherSettings.jsx';
import AccountSettings from './components/AccountSettings.jsx';
import PrivacyNote from './components/PrivacyNote.jsx';
import TermsNote from './components/TermsNote.jsx';
import { StyleProfileSetup, StyleProfileSettings } from './components/StyleProfile.jsx';
import { useUser, initials } from './user.js';
import { swatchFor } from './components/OutfitPreview.jsx';
import { PREFERENCE_CHOICES, DEFAULT_PREFERENCES, loadPreferences, savePreferences, syncPreferences, toAccount } from './preferences.js';

const nav = [{name:'Overview',Icon:LayoutDashboard},{name:'My Wardrobe',Icon:Shirt},{name:'AI Stylist',Icon:MessageCircle},{name:'Saved Looks',Icon:Heart},{name:'Wedding Planner',Icon:Gem},{name:'Trip Planner',Icon:Luggage},{name:'Wear Stats',Icon:BarChart3},{name:'Shop Smart',Icon:ShoppingBag},{name:'Preferences',Icon:SlidersHorizontal}];

export default function App({hello}){
 const {user,first,logout}=useUser();
 const [legal,setLegal]=useState(null);   // 'terms' | 'privacy': the footer links
 const [page,setPage]=useState('Overview'),[itemCount,setItemCount]=useState(null),[anchorId,setAnchorId]=useState(null),[preset,setPreset]=useState(null),[mobile,setMobile]=useState(false),[toast,setToast]=useState(''),[lookCount,setLookCount]=useState(0);
 // Show a message briefly. A new message restarts the timer, so it isn't cut short by an older one.
 const toastTimer=useRef(null);
 // Garments without a clean cut-out yet get one in the background (once each).
 useEffect(()=>{api.listItems().then(queueMissingCutouts).catch(()=>{})},[page]);
 const notify=(s,ms=3000)=>{setToast(s);window.clearTimeout(toastTimer.current);toastTimer.current=window.setTimeout(()=>setToast(''),ms)};
 // A warm hello after signing in ("Welcome back, <first name>!").
 useEffect(()=>{if(hello)notify(hello,5000)},[]); // eslint-disable-line react-hooks/exhaustive-deps
 // The optional style profile questions, once per account (skippable; editable later in Preferences).
 const [setup,setSetup]=useState(null);
 useEffect(()=>{api.getStyleProfile().then(p=>{syncPreferences(p,api);if(!p.onboarded)setSetup(p)}).catch(()=>{})},[]);
 // Show the real number of wardrobe pieces on the Overview page.
 useEffect(()=>{if(page!=='Overview')return;api.listItems().then(list=>setItemCount(list.length)).catch(()=>setItemCount(null))},[page]);
 // Keep the Saved Looks count (sidebar badge, Overview) in step with the database.
 useEffect(()=>{api.getLooks().then(l=>setLookCount(l.length)).catch(()=>setLookCount(null))},[page]);
 // Pieces not worn in 30 days, for the Overview nudge.
 const [resting,setResting]=useState(null);
 useEffect(()=>{if(page!=='Overview')return;api.getWearStats(30).then(s=>setResting(s)).catch(()=>setResting(null))},[page]);
 // anchor: a wardrobe item to build the outfit around (from "Style this" on a wardrobe card).
 // preset: stylist settings to start from (e.g. today's festival colour); styling starts at once.
 const change=(p,anchor=null,stylistPreset=null)=>{setPage(p);setAnchorId(anchor);setPreset(stylistPreset);setMobile(false)};
 // Today's festival (or the next one within 3 weeks), from Peheraav's festival table.
 const [festival,setFestival]=useState(null);
 useEffect(()=>{if(page!=='Overview')return;api.getFestivalNow().then(setFestival).catch(()=>setFestival(null))},[page]);
 const festivalPreset=(f)=>({occasion:f.occasion,style:f.style??'',festival:f.key,colour:f.today?f.colour:'',reason:f.title});
 return <div className="shell">
  <aside className={'sidebar '+(mobile?'open':'')}><div className="brand"><img className="brand-logo" src="/brand/peheraav-logo-horizontal.svg" alt="Peheraav AI — your wardrobe, styled by AI"/><button className="close mobile" onClick={()=>setMobile(false)}><X/></button></div>
   <p className="nav-label">WORKSPACE</p>{nav.map(({name,Icon})=><button key={name} className={'nav '+(page===name?'active':'')} onClick={()=>change(name)}><Icon size={18}/>{name}{name==='Saved Looks'&&lookCount>0?<span className="count">{lookCount}</span>:null}</button>)}
   <div className="side-bottom"><div className="note"><Sparkles size={17}/><h3>A little style goes a long way.</h3><p>Build new looks from pieces you already love.</p><button onClick={()=>change('AI Stylist')}>Meet your stylist ↗</button></div><div className="profile"><span>{initials(user.name)}</span><div><b>{user.name}</b><small>{user.email}</small></div><button className="icon-btn logout" onClick={logout} aria-label="Log out" title="Log out"><LogOut size={15}/></button></div></div>
  </aside>{mobile&&<button className="scrim" onClick={()=>setMobile(false)} aria-label="Close menu"/>}
  <main><header><button className="menu mobile" aria-label="Open menu" onClick={()=>setMobile(true)}><Menu/></button><div className="crumb">Workspace <ChevronRight size={14}/><b>{page}</b></div><span className="user" title={user.name}>{initials(user.name)}</span></header>
   <div className="content"><VerifyBanner/>
    {page==='Overview'&&<><Heading eyebrow="YOUR STYLE, SIMPLIFIED" title={<>{greeting()}, {first}. <em>What feels like you today?</em></>} sub="A calmer way to get dressed, using the pieces you already own." action={<button className="primary" onClick={()=>change('AI Stylist')}><Sparkles size={16}/> Ask my stylist</button>}/>
     <section className="hero"><div className="hero-copy"><label>✦ YOUR DAILY STYLE NOTE</label><h2>Wear what you love.<br/><em>See it differently.</em></h2><p>Tell me where you're going and how you want to feel, {first}, and I'll find fresh combinations from your own wardrobe.</p><button className="light" onClick={()=>change('AI Stylist')}>Find my outfit ↗</button><small>● Your wardrobe, styled by AI.</small></div><div className="hero-art"><div className="sun"></div><span className="art-title">THE ART OF<br/>GETTING DRESSED</span><div className="garment g1"></div><div className="garment g2"></div><div className="garment g3"></div><span className="sticker">LESS, BUT<br/><b>LOVELY</b></span></div></section>
     {festival&&<section className="festival-card"><div className="festival-swatches">{festival.colours.slice(0,4).map(c=><span key={c} style={{background:swatchFor(c)}} title={c}/>)}</div><div className="festival-copy"><small>{festival.today?'✦ TODAY\'S FESTIVAL COLOUR':'✦ COMING UP'}</small><h3>{festival.title}</h3><p>{festival.day_label?`${festival.day_label}. `:''}{festival.tip}</p><p className="festival-note">Festival dates can differ by a day in your region.</p></div><button className="primary" onClick={()=>change('AI Stylist',null,festivalPreset(festival))}><Sparkles size={15}/> {festival.colours.length===1?`Style me in ${festival.colour}`:`Style me for ${festival.name}`}</button></section>}
     <SectionTitle title="A little look inside" eyebrow="YOUR COLLECTION" action={<button className="text-btn" onClick={()=>change('My Wardrobe')}>View wardrobe ↗</button>}/><div className="stats"><Stat icon={<Shirt/>} value={itemCount??'–'} label="Pieces in your wardrobe" color="peach"/><Stat icon={<Heart/>} value={lookCount??'–'} label="Saved looks" color="rose"/><Stat icon={<Sparkles/>} value="∞" label="Ways to re-style" color="sage"/></div>
     {resting&&resting.total_items>0&&resting.not_worn.length>0&&<button className="resting-nudge" onClick={()=>change('Wear Stats')}><Clock size={18}/><span><b>{resting.not_worn.length} piece{resting.not_worn.length===1?'':'s'} not worn in 30 days</b><small>{resting.not_worn.slice(0,3).map(r=>r.item.name).join(', ')}{resting.not_worn.length>3?'…':''}: give them a day out</small></span><span className="resting-photos">{resting.not_worn.slice(0,4).map(r=><img key={r.item.id} src={r.item.image_url} alt=""/>)}</span><ArrowUpRight size={16}/></button>}
     <SectionTitle title="Little things, lovely possibilities" eyebrow="START EXPLORING"/><div className="quick">{[['♡','Ask your stylist','Tell us the occasion, colour or mood.','Get styled','AI Stylist'],['♧','Organise your wardrobe','Keep your favourite pieces in one place.','Explore your pieces','My Wardrobe'],['✧','Keep the good looks','Save combinations you want to wear again.','See saved looks','Saved Looks']].map(a=><button className="quick-card" key={a[1]} onClick={()=>change(a[4])}><span>{a[0]}</span><h3>{a[1]}</h3><p>{a[2]}</p><b>{a[3]} ↗</b></button>)}</div><p className="disclaimer">ⓘ Peheraav only styles you with pieces you have added to My Wardrobe.</p>
    </>}
    {page==='My Wardrobe'&&<Wardrobe notify={notify} onStyle={(item)=>change('AI Stylist',item.id)}/>}
    {page==='AI Stylist'&&<Stylist key={`${anchorId??'none'}-${preset?.reason??''}`} anchorId={anchorId} preset={preset} goToWardrobe={()=>change('My Wardrobe')} goToPreferences={()=>change('Preferences')} notify={notify} onLookSaved={()=>setLookCount(c=>c+1)}/>}
    {page==='Saved Looks'&&<SavedLooks notify={notify} goToStylist={()=>change('AI Stylist')} onCountChange={setLookCount}/>}
    {page==='Wedding Planner'&&<WeddingPlanner goToWardrobe={()=>change('My Wardrobe')}/>}
    {page==='Trip Planner'&&<TripPlanner goToWardrobe={()=>change('My Wardrobe')}/>}
    {page==='Wear Stats'&&<WearStats onStyle={(item)=>change('AI Stylist',item.id)} goToWardrobe={()=>change('My Wardrobe')}/>}
    {page==='Shop Smart'&&<ShopSmart goToWardrobe={()=>change('My Wardrobe')}/>}
    {page==='Preferences'&&<><Heading eyebrow="MADE TO FEEL LIKE YOU" title={<>Your style, <em>your choices, {first}.</em></>} sub="Your account, and optional preferences that help personalise future recommendations."/><Preferences notify={notify}/></>}
   </div><footer><span>Made for your wardrobe, not your shopping cart.</span><span className="legal-links"><button className="text-btn" onClick={()=>setLegal('terms')}>Terms of use</button> · <button className="text-btn" onClick={()=>setLegal('privacy')}>Privacy note</button> · PEHERAAV 1.0</span></footer>{legal==='terms'&&<TermsNote onClose={()=>setLegal(null)}/>}{legal==='privacy'&&<PrivacyNote onClose={()=>setLegal(null)}/>}
  </main>{toast&&<div className="toast"><Check size={16}/>{toast}</div>}{setup&&<StyleProfileSetup initial={setup} notify={notify} onDone={()=>setSetup(null)}/>}
 </div>
}
function greeting(){const h=new Date().getHours();return h<12?'Good morning':h<17?'Good afternoon':'Good evening'}
function SectionTitle({title,eyebrow,action}){return <div className="section-title"><div><small>{eyebrow}</small><h2>{title}</h2></div>{action}</div>}
function Stat({icon,value,label,color}){return <div className="stat"><span className={color}>{icon}</span><strong>{value}</strong><b>{label}</b></div>}
function Preferences({notify}){
 const [prefs,setPrefs]=useState(()=>loadPreferences()??DEFAULT_PREFERENCES);
 const set=(k,v)=>setPrefs(p=>({...p,[k]:v}));
 const save=async()=>{savePreferences(prefs);try{await api.saveStyleProfile(toAccount(prefs));notify('Preferences saved to your account. Your stylist will start with these on any device.')}catch(e){notify(e.message)}};
 return <div className="prefs"><AccountSettings notify={notify}/><StyleProfileSettings notify={notify}/><WeatherSettings notify={notify}/>{[['Personal style','style'],['What matters most?','comfort'],['Colours you gravitate toward','colour']].map(([title,key])=><section key={key}><h3>{title}</h3><div>{PREFERENCE_CHOICES[key].map(o=><button className={prefs[key]===o?'chosen':''} aria-pressed={prefs[key]===o} key={o} onClick={()=>set(key,o)}>{o}{prefs[key]===o?' ✓':''}</button>)}</div></section>)}<button className="primary" onClick={save}>Save preferences <Check size={15}/></button><p className="muted">Saved with your account, so they follow you to any device. The AI Stylist form starts with these choices, and you can still change them for any request.</p></div>}

// Until the email is confirmed: a gentle reminder with a resend button (nothing is blocked meanwhile).
function VerifyBanner(){
 const {user,setUser,first}=useUser();
 const [state,setState]=useState({busy:false,text:''});
 if(!user||user.email_verified)return null;
 const resend=async()=>{setState({busy:true,text:''});try{const r=await api.resendVerification();setState({busy:false,text:r.detail});if(/already confirmed/.test(r.detail))setUser({...user,email_verified:true})}catch(e){setState({busy:false,text:e.message})}};
 return <div className="verify-banner" role="status"><span>Please confirm your email, {first} (<b>{user.email}</b>): open the link we email you.{state.text&&<> {state.text}</>}</span><button className="text-btn" onClick={resend} disabled={state.busy}>{state.busy?'Sending…':'Email me a link'}</button></div>
}

