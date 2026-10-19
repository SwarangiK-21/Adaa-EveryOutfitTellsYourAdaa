import React, { useEffect, useRef, useState } from 'react';
import { LayoutDashboard, Shirt, MessageCircle, Heart, SlidersHorizontal, Sparkles, ArrowUpRight, ChevronRight, Menu, X, Check, Luggage, ShoppingBag, BarChart3, Clock } from 'lucide-react';
import { api } from './api.js';
import Heading from './components/Heading.jsx';
import Wardrobe from './pages/Wardrobe.jsx';
import Stylist from './pages/Stylist.jsx';
import SavedLooks from './pages/SavedLooks.jsx';
import TripPlanner from './pages/TripPlanner.jsx';
import ShopSmart from './pages/ShopSmart.jsx';
import WearStats from './pages/WearStats.jsx';
import { TryOnContext } from './tryon.js';
import { queueMissingCutouts } from './cutoutQueue.js';
import { WelcomeSetup, YourPhotoSettings } from './components/YourPhoto.jsx';
import WeatherSettings from './components/WeatherSettings.jsx';
import { PREFERENCE_CHOICES, DEFAULT_PREFERENCES, loadPreferences, savePreferences } from './preferences.js';

const nav = [{name:'Overview',Icon:LayoutDashboard},{name:'My Wardrobe',Icon:Shirt},{name:'AI Stylist',Icon:MessageCircle},{name:'Saved Looks',Icon:Heart},{name:'Trip Planner',Icon:Luggage},{name:'Wear Stats',Icon:BarChart3},{name:'Shop Smart',Icon:ShoppingBag},{name:'Preferences',Icon:SlidersHorizontal}];

export default function App(){
 const [page,setPage]=useState('Overview'),[itemCount,setItemCount]=useState(null),[anchorId,setAnchorId]=useState(null),[mobile,setMobile]=useState(false),[toast,setToast]=useState(''),[lookCount,setLookCount]=useState(0);
 // Show a message briefly. A new message restarts the timer, so it isn't cut short by an older one.
 const toastTimer=useRef(null);
 // Your photo + try-on server (shared with every outfit preview), and the first-run welcome step.
 const [profile,setProfile]=useState(null),[welcome,setWelcome]=useState(false);
 const refreshProfile=async()=>{try{const p=await api.getProfile();setProfile(p);return p}catch{return null}};
 const welcomeSeen=()=>{try{return localStorage.getItem('adaa.welcomeDone')==='1'}catch{return true}};
 const finishWelcome=()=>{try{localStorage.setItem('adaa.welcomeDone','1')}catch{}setWelcome(false)};
 useEffect(()=>{refreshProfile().then(p=>{if(p&&!p.photo_url&&!welcomeSeen())setWelcome(true)})},[]); // eslint-disable-line react-hooks/exhaustive-deps
 // Garments without a clean cut-out yet get one in the background (once each).
 useEffect(()=>{api.listItems().then(queueMissingCutouts).catch(()=>{})},[page]);
 const notify=(s)=>{setToast(s);window.clearTimeout(toastTimer.current);toastTimer.current=window.setTimeout(()=>setToast(''),3000)};
 // Show the real number of wardrobe pieces on the Overview page.
 useEffect(()=>{if(page!=='Overview')return;api.listItems().then(list=>setItemCount(list.length)).catch(()=>setItemCount(null))},[page]);
 // Keep the Saved Looks count (sidebar badge, Overview) in step with the database.
 useEffect(()=>{api.getLooks().then(l=>setLookCount(l.length)).catch(()=>setLookCount(null))},[page]);
 // Pieces not worn in 30 days, for the Overview nudge.
 const [resting,setResting]=useState(null);
 useEffect(()=>{if(page!=='Overview')return;api.getWearStats(30).then(s=>setResting(s)).catch(()=>setResting(null))},[page]);
 // anchor: a wardrobe item to build the outfit around (from "Style this" on a wardrobe card).
 const change=(p,anchor=null)=>{setPage(p);setAnchorId(anchor);setMobile(false)};
 return <TryOnContext.Provider value={{profile,refreshProfile}}><div className="shell">
  <aside className={'sidebar '+(mobile?'open':'')}><div className="brand"><div className="brand-icon"><Sparkles/></div><div><b>Adaa</b><small>YOUR PERSONAL STYLIST</small></div><button className="close mobile" onClick={()=>setMobile(false)}><X/></button></div>
   <p className="nav-label">WORKSPACE</p>{nav.map(({name,Icon})=><button key={name} className={'nav '+(page===name?'active':'')} onClick={()=>change(name)}><Icon size={18}/>{name}{name==='Saved Looks'&&lookCount>0?<span className="count">{lookCount}</span>:null}</button>)}
   <div className="side-bottom"><div className="note"><Sparkles size={17}/><h3>A little style goes a long way.</h3><p>Build new looks from pieces you already love.</p><button onClick={()=>change('AI Stylist')}>Meet your stylist ↗</button></div><div className="profile"><span>S</span><div><b>Your wardrobe</b><small>Local prototype</small></div></div></div>
  </aside>{mobile&&<button className="scrim" onClick={()=>setMobile(false)} aria-label="Close menu"/>}
  <main><header><button className="menu mobile" onClick={()=>setMobile(true)}><Menu/></button><div className="crumb">Workspace <ChevronRight size={14}/><b>{page}</b></div><span className="mode">● Prototype mode</span><span className="user">S</span></header>
   <div className="content">
    {page==='Overview'&&<><Heading eyebrow="YOUR STYLE, SIMPLIFIED" title={<>{greeting()}. <em>What feels like you today?</em></>} sub="A calmer way to get dressed, using the pieces you already own." action={<button className="primary" onClick={()=>change('AI Stylist')}><Sparkles size={16}/> Ask my stylist</button>}/>
     <section className="hero"><div className="hero-copy"><label>✦ YOUR DAILY STYLE NOTE</label><h2>Wear what you love.<br/><em>See it differently.</em></h2><p>Tell your stylist where you're going and how you want to feel. Explore fresh combinations from your wardrobe.</p><button className="light" onClick={()=>change('AI Stylist')}>Find my outfit ↗</button><small>● Your wardrobe. Your world. Your Adaa.</small></div><div className="hero-art"><div className="sun"></div><span className="art-title">THE ART OF<br/>GETTING DRESSED</span><div className="garment g1"></div><div className="garment g2"></div><div className="garment g3"></div><span className="sticker">LESS, BUT<br/><b>LOVELY</b></span></div></section>
     <SectionTitle title="A little look inside" eyebrow="YOUR COLLECTION" action={<button className="text-btn" onClick={()=>change('My Wardrobe')}>View wardrobe ↗</button>}/><div className="stats"><Stat icon={<Shirt/>} value={itemCount??'–'} label="Pieces in your wardrobe" color="peach"/><Stat icon={<Heart/>} value={lookCount??'–'} label="Saved looks" color="rose"/><Stat icon={<Sparkles/>} value="∞" label="Ways to re-style" color="sage"/></div>
     {resting&&resting.total_items>0&&resting.not_worn.length>0&&<button className="resting-nudge" onClick={()=>change('Wear Stats')}><Clock size={18}/><span><b>{resting.not_worn.length} piece{resting.not_worn.length===1?'':'s'} not worn in 30 days</b><small>{resting.not_worn.slice(0,3).map(r=>r.item.name).join(', ')}{resting.not_worn.length>3?'…':''}: give them a day out</small></span><span className="resting-photos">{resting.not_worn.slice(0,4).map(r=><img key={r.item.id} src={r.item.image_url} alt=""/>)}</span><ArrowUpRight size={16}/></button>}
     <SectionTitle title="Little things, lovely possibilities" eyebrow="START EXPLORING"/><div className="quick">{[['♡','Ask your stylist','Tell us the occasion, colour or mood.','Get styled','AI Stylist'],['♧','Organise your wardrobe','Keep your favourite pieces in one place.','Explore your pieces','My Wardrobe'],['✧','Keep the good looks','Save combinations you want to wear again.','See saved looks','Saved Looks']].map(a=><button className="quick-card" key={a[1]} onClick={()=>change(a[4])}><span>{a[0]}</span><h3>{a[1]}</h3><p>{a[2]}</p><b>{a[3]} ↗</b></button>)}</div><p className="disclaimer">ⓘ Adaa only styles you with pieces you have added to My Wardrobe.</p>
    </>}
    {page==='My Wardrobe'&&<Wardrobe notify={notify} onStyle={(item)=>change('AI Stylist',item.id)}/>}
    {page==='AI Stylist'&&<Stylist key={anchorId??'none'} anchorId={anchorId} goToWardrobe={()=>change('My Wardrobe')} goToPreferences={()=>change('Preferences')} notify={notify} onLookSaved={()=>setLookCount(c=>c+1)}/>}
    {page==='Saved Looks'&&<SavedLooks notify={notify} goToStylist={()=>change('AI Stylist')} onCountChange={setLookCount}/>}
    {page==='Trip Planner'&&<TripPlanner goToWardrobe={()=>change('My Wardrobe')}/>}
    {page==='Wear Stats'&&<WearStats onStyle={(item)=>change('AI Stylist',item.id)} goToWardrobe={()=>change('My Wardrobe')}/>}
    {page==='Shop Smart'&&<ShopSmart goToWardrobe={()=>change('My Wardrobe')}/>}
    {page==='Preferences'&&<><Heading eyebrow="MADE TO FEEL LIKE YOU" title={<>Your style, <em>your choices.</em></>} sub="These optional preferences help personalise future recommendations."/><Preferences notify={notify}/></>}
   </div><footer><span>Made for your wardrobe, not your shopping cart.</span><span>ADAA 1.0 · LOCAL PROTOTYPE</span></footer>
  </main>{toast&&<div className="toast"><Check size={16}/>{toast}</div>}
  {welcome&&<WelcomeSetup notify={notify} onDone={finishWelcome}/>}
 </div></TryOnContext.Provider>
}
function greeting(){const h=new Date().getHours();return h<12?'Good morning':h<17?'Good afternoon':'Good evening'}
function SectionTitle({title,eyebrow,action}){return <div className="section-title"><div><small>{eyebrow}</small><h2>{title}</h2></div>{action}</div>}
function Stat({icon,value,label,color}){return <div className="stat"><span className={color}>{icon}</span><strong>{value}</strong><b>{label}</b></div>}
function Preferences({notify}){
 const [prefs,setPrefs]=useState(()=>loadPreferences()??DEFAULT_PREFERENCES);
 const set=(k,v)=>setPrefs(p=>({...p,[k]:v}));
 const save=()=>notify(savePreferences(prefs)?'Preferences saved. Your stylist will start with these.':'Could not save preferences in this browser.');
 return <div className="prefs"><WeatherSettings notify={notify}/><YourPhotoSettings notify={notify}/>{[['Personal style','style'],['What matters most?','comfort'],['Colours you gravitate toward','colour']].map(([title,key])=><section key={key}><h3>{title}</h3><div>{PREFERENCE_CHOICES[key].map(o=><button className={prefs[key]===o?'chosen':''} aria-pressed={prefs[key]===o} key={o} onClick={()=>set(key,o)}>{o}{prefs[key]===o?' ✓':''}</button>)}</div></section>)}<button className="primary" onClick={save}>Save preferences <Check size={15}/></button><p className="muted">Saved in this browser. The AI Stylist form starts with these choices, and you can still change them for any request.</p></div>}
