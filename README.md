<p align="center">
  <img src="brand/adaa-logo-cream.svg" alt="Adaa logo: a plum ribbon A" width="240">
</p>

<h1 align="center">Adaa</h1>

<p align="center"><b>Every outfit tells your Adaa.</b><br>
A personal wardrobe stylist that builds complete outfits from the clothes you already own.</p>

<p align="center">
  <a href="https://adaa-every-outfit-tells-your-adaa.eastasia.cloudapp.azure.com"><img alt="Live app" src="https://img.shields.io/badge/live-open%20Adaa-5B1F3F?style=flat-square"></a>
  <img alt="Google Play: coming soon" src="https://img.shields.io/badge/Google%20Play-coming%20soon-C9A45C?style=flat-square">
  <img alt="Tests: 258 passing" src="https://img.shields.io/badge/tests-258%20passing-2E7D32?style=flat-square">
  <img alt="React 18" src="https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-Python-009688?style=flat-square&logo=fastapi&logoColor=white">
  <img alt="SQLite" src="https://img.shields.io/badge/SQLite-database-003B57?style=flat-square&logo=sqlite&logoColor=white">
</p>

<p align="center">
  <img src="docs/screenshots/stylist-outfit.png" alt="An Adaa outfit: the user's own crop top, skirt, shoes, bag and jewellery arranged as one look, with the reasons it works" width="720">
</p>

---

## Contents

[Problem and solution](#the-problem) · [Features](#features) · [Screenshots](#screenshots) · [Tech stack](#tech-stack) · [How it works](#how-it-works) · [Run it locally](#run-it-locally) · [Project structure](#project-structure) · [Security and privacy](#security-and-privacy) · [Links](#links) · [Roadmap](#roadmap) · [Credits](#credits-and-contributing)

## The problem

Most of us have a full wardrobe and still feel we have "nothing to wear". We forget what we own, repeat the same few outfits, and buy new clothes that don't go with anything. Generic fashion apps don't help much: they suggest clothes you don't have, or ignore Indian wear like sarees, kurtas and lehengas.

## The solution

Adaa is a stylist for **your own** wardrobe. You add photos of your clothes, jewellery, shoes and bags once. Then you ask in plain words (*"Aaj college ke liye kuch comfy"*) and Adaa puts together complete looks, **only from pieces you really own**, and explains why each one works.

> **The core rule:** Adaa never invents a piece. If something is missing (no bag, nothing tagged for a wedding, "my green kurta" when you don't have one), it says so and shows the best real combination instead.

## Features

| Feature | What it does |
|---|---|
| 👗 **My Wardrobe** | Add pieces with a photo and details; search, filter, edit, delete. **Auto-fill** reads the photo and suggests the category, type and colour |
| ✨ **AI Stylist** | Ask by typing or **voice**, in English or **Hinglish**, or pick occasion, style and colours. Get up to 4 different outfits, each with reasons and honest cautions |
| 🖼️ **Outfit boards** | Each look is shown as a board of your **own garment photos**, with backgrounds removed in your browser (no AI-generated images). Download it as a picture to share |
| 🔁 **Swap and save** | Swap any piece for another that still works, save looks, add your own photo wearing a look, mark *"Wore it today"* |
| 💍 **Wedding Planner** | A different look for each function (haldi, mehendi, sangeet, wedding, reception…) following the usual dress codes, with no garment repeated, plus a get-ready list |
| 🪔 **Festivals** | About 30 festivals and national days with their colours (*"Style me for Diwali"*, Navratri's colour of the day) |
| 🧳 **Trip Planner** | One outfit per day of a trip with no garment worn twice, and a packing list |
| ☀️ **Weather-aware** | Uses today's forecast for your city: lighter pieces when it's hot, layers when it's cold, a caution about heels in the rain |
| 📊 **Wear Stats** | Pieces not worn in 30/60/90 days, most worn, and cost per wear |
| 🛍️ **Shop Smart** | The few new pieces that would unlock the most outfits with what you already own (ideas only; Adaa never sells) |
| 💜 **Style profile** | Optional height, body shape, fit, undertone and colours you love or avoid. Each look then explains **"Why it suits you"** |
| 🔐 **Accounts** | Email + password, a private wardrobe per person, email confirmation, password reset, delete account. Adaa greets you by name |
| 📱 **Phone-friendly** | Works in any modern browser and can be added to the home screen like an app |

## Screenshots

> All screenshots are of the real app, taken from a copy of a real wardrobe. Nothing is mocked up or AI-generated.

| Overview | My Wardrobe |
|---|---|
| ![Overview page with a greeting, the daily style note and today's festival colours](docs/screenshots/overview.png) | ![Wardrobe page showing clothing photos with category filters](docs/screenshots/wardrobe.png) |
| **Ask the stylist** | **Saved look (outfit board)** |
| ![The AI Stylist after a typed request, showing what Adaa understood and the first look](docs/screenshots/stylist-request.png) | ![A saved look shown as an outfit board with its pieces and reasons](docs/screenshots/saved-look.png) |
| **Wedding Planner** | **Shop Smart** |
| ![Wedding planner with a different look for haldi, mehendi and sangeet](docs/screenshots/wedding-planner.png) | ![Shop Smart ideas such as gold juttis and beige trousers, with how many new outfits each unlocks](docs/screenshots/shop-smart.png) |
| **Wear Stats** | **Sign up** |
| ![Wear stats showing pieces not worn in 30 days](docs/screenshots/wear-stats.png) | ![Sign-up screen with name, email, phone and password](docs/screenshots/sign-up.png) |

<p align="center"><b>On a phone</b><br><img src="docs/screenshots/phone-saved-look.png" alt="A saved look on a phone screen" width="300"></p>

## Tech stack

| Layer | Technology | Used for |
|---|---|---|
| Frontend | **React 18 + Vite**, plain CSS, Lucide icons | The screens; one API file (`api.js`) talks to the backend |
| Backend | **Python + FastAPI** (Uvicorn) | The API, accounts, photo checks and the styling rules |
| Database | **SQLite** (one file, WAL mode) | Accounts, wardrobe, looks, history, style profiles |
| Styling "brain" | **Rule-based Python** (`backend/recommender/`) | Outfits, request understanding, planners, festivals, weather. No paid AI service |
| In-browser AI | **onnxruntime-web** with **IS-Net** and a **SegFormer-B2** clothes parser | Removing photo backgrounds and auto-fill, inside the user's browser |
| Weather | **Open-Meteo** (free, no key) | Today's forecast for the user's city |
| Voice | Browser **Web Speech API** | Speaking a request |
| Hosting | Ubuntu server on **Azure for Students**, **Caddy** (https), **systemd** | Running the live app |
| Backups | Nightly `backup.py` + off-site copy to **Backblaze B2** | Keeping data safe |
| Email | Any SMTP service (Gmail app password in production) | Email confirmation and password reset |
| Tests | **pytest** (258 tests) | Checking the backend and styling rules |

## How it works

```mermaid
flowchart LR
    U["📱 Browser<br/>React app"] -- "https" --> C["Caddy<br/>(https, security headers)"]
    C --> A["FastAPI backend<br/>(Python)"]
    A --> R["Rule-based stylist<br/>backend/recommender"]
    A --> D[("SQLite<br/>database")]
    A --> F["Photo files<br/>on disk"]
    U -. "city forecast" .-> W["Open-Meteo"]
    U -. "background removal<br/>runs in the browser" .-> M["IS-Net + clothes<br/>parser (ONNX)"]
    B["Nightly backup"] --> D
    B --> F
    B --> S["Backblaze B2<br/>(off-site copy)"]
```

**A typical visit:**

```mermaid
flowchart LR
    A["Sign up / log in"] --> B["Add clothes<br/>(photo + details)"]
    B --> C["Browser cleans up<br/>photo backgrounds"]
    C --> D["Ask the stylist<br/>(type, voice or chips)"]
    D --> E["Up to 4 looks,<br/>with reasons"]
    E --> F["Swap pieces,<br/>save the look"]
    F --> G["Wore it today<br/>→ Wear Stats"]
```

- **How outfits are chosen:** every piece is classified (kurta → top, palazzo → bottom, jhumkas → earrings). Adaa builds every sensible top + bottom pair or one-piece, scores it (occasion tags, style, colour harmony, weather, style profile), adds shoes, jewellery and a bag, then picks up to 4 looks that really differ.
- **Why rules instead of a chatbot:** it can only pick from your items, so it can't "hallucinate" a piece. Every suggestion comes with the real reasons, it's free to run, and it gives the same answer every time, so it can be tested.

More detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · Project report (PDF): [docs/ADAA_Project_Report.pdf](docs/ADAA_Project_Report.pdf)

## Run it locally

**You need:** Python 3.11+ and Node.js 18+ (tested with Python 3.15 and Node 24).

**1. Backend** (terminal 1):

```bash
cd backend
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1     macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Check http://127.0.0.1:8000/api/health shows `"status":"ok"`.

**2. Frontend** (terminal 2):

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** and create an account. Without email settings, confirmation and reset emails are printed in the backend terminal.

**3. Tests:**

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest        # expected: 258 passed
```

<details>
<summary><b>Troubleshooting</b></summary>

| Problem | Fix |
|---|---|
| *"running scripts is disabled"* (Windows) | Run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` once |
| App says *"Can't reach the Adaa server"* | The backend isn't running; start terminal 1 |
| Port 8000 is already in use | Start the backend with `--port 8001`, and the frontend with `ADAA_API_URL=http://127.0.0.1:8001` set (PowerShell: `$env:ADAA_API_URL="http://127.0.0.1:8001"; npm run dev`) |
| iPhone photo refused | HEIC isn't supported; share the photo as JPEG |

</details>

<details>
<summary><b>Share on home Wi-Fi</b> (friends try it on their phones)</summary>

Run `npm run share` instead of `npm run dev` in the `frontend` folder and share the **Network** address it prints (e.g. `http://192.168.1.20:4173`). Everyone creates their own account. Over plain `http` the microphone button is hidden, and Android may show the browser bar.
</details>

<details>
<summary><b>Put it on a server</b></summary>

[docs/DEPLOY.md](docs/DEPLOY.md) walks through a free **Azure for Students** (no card) or Oracle Cloud server: one install command (`deploy/install.sh`) sets up https (Caddy), the service, nightly backups and log retention. Helper scripts set up email (`deploy/email-setup.sh`) and off-site backups (`deploy/backup-setup.sh`); `deploy/update.sh` updates from GitHub. On a server the backend also serves the built app, so only one program runs.
</details>

<details>
<summary><b>Settings</b> (environment variables, all optional)</summary>

| Setting | What it does | Default |
|---|---|---|
| `ADAA_PUBLIC_URL` | The address people open Adaa at (used in email links) | `http://localhost:5173` |
| `ADAA_CONTACT_EMAIL` | Shown in the privacy note | none |
| `ADAA_SECURE_COOKIES` | `1` behind https, so the sign-in cookie is only sent encrypted | off |
| `ADAA_MAX_ITEMS` / `ADAA_MAX_LOOKS` / `ADAA_MAX_USERS` | Limits per person / total accounts (`0` = no cap) | 300 / 200 / 0 |
| `ADAA_SMTP_HOST`, `_PORT`, `_USER`, `_PASSWORD`, `ADAA_MAIL_FROM` | Email service for confirmation and reset emails | none: printed in the terminal |
| `ADAA_BACKUP_S3_ENDPOINT`, `_BUCKET`, `_KEY_ID`, `_SECRET`, `_REGION` | Off-site copy of each nightly backup (Backblaze B2 or any S3-compatible storage) | none: backups stay on the server |
| `ADAA_RATE_LIMITS` | `0` switches request limits off (never on a public server) | on |
| `ADAA_DATA_DIR`, `ADAA_BACKUP_DIR`, `ADAA_FRONTEND_DIR` | Where data, backups and the built app live | inside `backend/` and `frontend/dist` |

The full list with comments is in [`deploy/adaa.env.example`](deploy/adaa.env.example).
</details>

<details>
<summary><b>API overview</b></summary>

Interactive docs at http://127.0.0.1:8000/docs while the backend runs. Every route needs a logged-in user, except health, options, sign-up/log-in/reset, festivals and the cut-out models.

| Area | Routes |
|---|---|
| Accounts | `POST /api/auth/signup`, `/login`, `/logout`, `/forgot`, `/reset`, `/verify`, `/verify/resend` · `GET/PUT/DELETE /api/auth/me` · `PUT /api/auth/password` · `GET /api/auth/about` |
| Style profile | `GET/PATCH /api/profile/style` |
| Wardrobe | `GET/POST /api/items` · `GET/PUT/DELETE /api/items/{id}` · `GET /api/items/{id}/photo` · `PUT/GET/DELETE /api/items/{id}/cutout` |
| Stylist | `POST /api/stylist/parse` · `POST /api/recommendations` · `POST /api/outfits/evaluate` · `POST /api/outfits/alternatives` |
| Looks and history | `GET/POST /api/looks` · `PUT/DELETE /api/looks/{id}` · `POST /api/looks/{id}/wear` · `POST/GET/DELETE /api/looks/{id}/photo` · `GET/POST /api/history` · `DELETE /api/history/{id}` |
| Planners and insights | `POST /api/trips/plan` · `GET /api/events/functions` · `POST /api/events/plan` · `GET /api/festivals/now` · `GET /api/insights/gaps` · `GET /api/insights/wear?days=30` |
| Other | `GET /api/health` · `GET /api/options` · `GET /api/models/{isnet\|clothes}` · `POST /api/client-error` |

</details>

## Project structure

```
Adaa/
├─ backend/                  Python + FastAPI
│  ├─ main.py                App setup, middleware, serves the built app on a server
│  ├─ config.py              All settings (paths, limits, email, backups)
│  ├─ auth.py, routes/auth.py  Accounts: password hashing, sessions, email links
│  ├─ routes/                API routes: items, recommendations, looks, planner, profile
│  ├─ recommender/           The rule-based stylist: engine, parser, colours, garments,
│  │                         planner, events (weddings), festivals, weather, profile_fit
│  ├─ database.py, looks_db.py  SQLite tables and queries
│  ├─ storage.py, image_meta.py  Photo checks, saving, removing hidden photo data
│  ├─ ratelimit.py, security.py  Request limits, cross-site check, Content Security Policy
│  ├─ backup.py, offsite.py  Nightly backup and off-site copy
│  ├─ mailer.py              Sends emails (or prints them when no email is set up)
│  └─ tests/                 258 pytest tests
├─ frontend/                 React + Vite
│  ├─ public/                Icons, logo files, web app manifest, robots.txt
│  └─ src/
│     ├─ App.jsx, Root.jsx   Layout, navigation, opening animation, log-in screen
│     ├─ api.js              Every call to the backend
│     ├─ pages/              Wardrobe, Stylist, SavedLooks, WeddingPlanner, TripPlanner, WearStats, ShopSmart
│     ├─ components/         Outfit board and cards, forms, account and legal dialogs…
│     └─ cutout*.js          Background removal in a Web Worker (onnxruntime-web)
├─ deploy/                   Server install/update scripts, systemd services, Caddyfile, settings example
├─ brand/                    Logo files, colours and fonts
└─ docs/                     Architecture, deploy guide, testing log, demo script,
                             project report (PDF) and screenshots
```

## Security and privacy

| Area | What Adaa does |
|---|---|
| Passwords | Never stored; only a salted **scrypt** hash |
| Sign-in | A random session token in an **HttpOnly, SameSite** cookie (Secure on https); the database stores only its SHA-256 |
| Brute force | 5 wrong passwords per email in 15 minutes, plus per-address limits on sign-up, log-in, reset emails and uploads |
| Data separation | Every query is filtered by the logged-in user, so one account can never see another's wardrobe |
| Photos | Real file type checked, random file names, shrunk in the browser, hidden location data removed on the server too |
| Web attacks | Cross-site write requests blocked, strict **Content Security Policy**, no third-party scripts or fonts |
| Email links | One-use, short-lived, hashed; sent after `#` so they never appear in server logs |
| Data | Delete your account any time; nightly backups with an off-site copy; server logs kept 30 days |

Details: the *Launch hardening* section of [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Links

| | |
|---|---|
| 🌐 **Live app** | https://adaa-every-outfit-tells-your-adaa.eastasia.cloudapp.azure.com |
| 📱 **Google Play** | Coming soon |
| 📄 **Project report** | [docs/ADAA_Project_Report.pdf](docs/ADAA_Project_Report.pdf) |
| 🏗️ **Architecture** | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| 🚀 **Deploy guide** | [docs/DEPLOY.md](docs/DEPLOY.md) |
| 🧪 **Testing log** | [docs/TESTING.md](docs/TESTING.md) |
| 🎤 **Demo script** | [docs/DEMO.md](docs/DEMO.md) |
| 🎨 **Brand** | [brand/README.md](brand/README.md) |

## Roadmap

**Planned**
- 📱 Android app on **Google Play** (the web app wrapped as a Trusted Web Activity)
- 🌐 Own domain and a transactional email service, so emails reach the inbox instead of spam
- 📴 An offline screen when there's no internet

**Ideas**
- Rank pieces you haven't worn lately higher in the stylist
- Makeup suggestions to go with a look
- An optional free local language model for friendlier chat (the rules would still choose the clothes)

**Known limitations**
- Requests are understood by keyword rules: clear sentences work best, and Adaa shows what it understood.
- Auto-fill is a suggestion: on 28 real photos it got the category right every time, the type about 9 in 10 and the colour about 3 in 4.
- Phones skip automatic background removal (the model is about 200 MB); those pieces get a clean cut-out the next time the account is opened on a computer.
- One server and one SQLite file: right for friends and early users, not for very large numbers.
- The clothes-parser model's licence (NVIDIA) allows **non-commercial use only**; a commercial version would need a differently licensed model.

## Credits and contributing

**Created by** [Swarangi Kothawade](https://github.com/SwarangiK-21).

**Built on open source:** [FastAPI](https://fastapi.tiangolo.com), [React](https://react.dev), [Vite](https://vite.dev), [onnxruntime-web](https://onnxruntime.ai) (MIT), [IS-Net](https://github.com/xuebinqin/DIS) via the [rembg](https://github.com/danielgatis/rembg) project (Apache 2.0), [SegFormer-B2 clothes parser](https://huggingface.co/Xenova/segformer_b2_clothes) (NVIDIA licence, non-commercial), [Open-Meteo](https://open-meteo.com), [Lucide](https://lucide.dev) icons, and DM Sans and Playfair Display fonts via [Fontsource](https://fontsource.org) (SIL Open Font License).

**Contributing:** this is a student project. Ideas and bug reports are welcome as GitHub issues. For code changes, please open an issue first, keep changes small, and make sure `python -m pytest` and `npm run build` pass.

**Licence:** no open-source licence has been chosen yet, so all rights are reserved by the author.
