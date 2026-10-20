# Adaa: mentor demo script

About **10 minutes**, plus questions. Suggested words to say are in *italics*.

---

## The day before

1. **Back up your data:** stop the backend, then copy `backend/data` to somewhere safe (e.g. `Desktop\adaa-backup`).
2. **Build a demo wardrobe of about 15 pieces**, covering both styles you want to show:
   - **Western:** your crop top, short skirt, gown, short frock, heels, sandals, silver jewellery, bag, watch.
   - **Traditional:** add at least one **kurta**, a **churidar/salwar/palazzo**, a **dupatta**, **jhumkas**, and **juttis or kolhapuris**. Without traditional bottoms, Adaa will honestly say it can't build a full traditional look.
   - **Tag occasions carefully.** The engine relies on them (e.g. kurta → Festive, Traditional function, Wedding).
3. **Rehearse your three requests** (below) and check the results look good with *your* pieces. Adjust occasion tags if a result surprises you.
4. Run the tests once: `python -m pytest` → **68 passed**.
5. Optional: on one saved look, press the camera button and add a photo of yourself wearing it, to show a **Verified** preview.

## 10 minutes before

1. **Close other projects using port 8000**, e.g. EduFlow-ERP. (Or use the alternate-port tip in the README.)
2. Start both servers:
   ```powershell
   # Terminal 1
   cd backend; .\.venv\Scripts\Activate.ps1; uvicorn main:app --reload
   # Terminal 2
   cd frontend; npm run dev
   ```
3. Open http://localhost:5173. Check the Overview shows your piece count.
4. Optional: on **Preferences**, choose "A little bit of everything", "A balance of both" and "No preference", so the demo starts neutral.
5. Zoom the browser to 110–125% so everyone can read it.
6. Keep a photo of one new piece ready on your desktop (JPEG, under 5 MB) to add live.

---

## The demo

### 1. The problem (30 s): Overview page
*"We all own lots of clothes but still struggle to put outfits together, and fashion inspiration usually shows clothes we don't own. Adaa is a personal stylist that only ever uses what's actually in your wardrobe."*

Point at: the piece count and saved looks on the Overview. These are live numbers from the database.

### 2. The wardrobe (1.5 min): My Wardrobe
1. Click **Add a piece**, choose your prepared photo, fill in name, category, type, colour, style and occasions, then press **Add to wardrobe**.
   *"Each piece is stored with its photo in a local SQLite database. Nothing goes to the cloud."*
2. Optional: try to add a non-photo file to show validation.
   *"Uploads are checked by their real file type, not just the name."*
3. Type a colour in **Search**, then click a category filter.

### 3. Ask in your own words (2 min): AI Stylist
Type your first rehearsed request, e.g. **"Style my black crop top for a party"**.
- Point at **"Here's what I understood"**: occasion, and the piece it's building around.
  *"This is a rule-based parser that runs locally. It matches 'my crop top' against my actual items."*
- Point at the **full-body preview**.
  *"This is an outfit board made from my own garment photos. Adaa removed the backgrounds and arranged them as if worn, so it shows exactly my pieces, with no AI guessing."*
- Scroll through the looks. Point at the **reasons** on one card.
  *"Every look explains itself: the occasion tags, the colour harmony, the pairing."*
- Point at any **note**, e.g. "Only 1 distinct outfit…".
  *"When my wardrobe can't support more, it says so instead of inventing pieces."*

### 4. Honesty (1 min)
Type a request for a piece you **don't** own, e.g. **"Style my green kurta for a wedding"**, if you have no green kurta.
*"It tells me it couldn't find a green kurta, and styles me with what I do have. This is the core rule of the project."*

### 5. Follow-up (30 s)
Type **"make it more comfortable"**.
*"It keeps the occasion and only changes comfort, so the heels get swapped for flats."*

### 6. Traditional look (1 min)
Type **"Traditional look for a family function"**, or use **✦ Style this** on your kurta in My Wardrobe and pick *Traditional function*.
Point at: kurta + bottom + dupatta + jhumkas + juttis, and *"A classic kurta and churidar pairing"*.

### 7. Swap and save (1 min)
On a look, press **⇄** on the footwear or earrings.
*"The alternatives come from my wardrobe and keep the outfit wearable. Pieces not tagged for this occasion are clearly labelled."*
Pick one: the preview and the reasons update. Then press **Save look**.

### 8. Lookbook and history (1 min): Saved Looks
Press **Wore it today**, then open **Outfit history**.
*"Saved looks and history are stored in the database. If I delete a piece from my wardrobe, the look keeps the rest and says a piece was removed, so the data never breaks."*

### 9. Under the hood (1 min)
Show the terminal: `python -m pytest` → **68 passed**.
*"The engine is plain Python rules, so it's predictable and fully tested: pairing rules, honesty, parsing, saved looks and a full end-to-end journey."*
Optionally open `docs/ARCHITECTURE.md` and show the diagram.

---

## Likely questions, and short answers

| Question | Answer |
|---|---|
| *Why not use ChatGPT or another AI?* | Cost, privacy and honesty. An AI model can invent clothes; this engine can only pick from real records, explains its reasons, runs free and offline, and is fully testable. A free local model could later polish the chat, but the rules would still choose the clothes. |
| *How does it decide what goes together?* | Garment pairing rules (kurta + salwar, top + jeans…), occasion tags, style compatibility (Indo-Western bridges Traditional and Western), colour harmony (neutrals, tonal, complementary, clashes), comfort, then it picks 4 *different* looks. |
| *Can it show the outfit on a real body (virtual try-on)?* | Not with free tools on this laptop: open-source try-on models need an NVIDIA GPU with 8 GB or more, and free online demos would upload my photos to someone else's server. I tried one on a free Colab GPU, but it took a minute per look and got shapes wrong, so I removed it. Adaa shows an outfit board made from my own garment photos, and a **verified** preview when I add my own photo of a saved look. If I later get a suitable GPU, a try-on model could plug into the same preview slot. |
| *What if my wardrobe is small?* | It returns fewer looks and says why, e.g. "you haven't added any bags yet". |
| *Does it recognise clothes from photos?* | Not yet: details are entered by hand. Automatic recognition was deliberately left out of the first version to keep it free and reliable. |
| *Where is my data?* | In `backend/data` on this computer: the SQLite file plus photos. Git ignores it, so it's never pushed to GitHub. |
| *What's next?* | Using wear history to suggest less-worn pieces, makeup suggestions, optional body-type-aware styling, and an optional local language model for friendlier chat. |

## If something goes wrong

| Problem | What to do |
|---|---|
| Page says "Can't reach the Adaa server" | The backend stopped. In Terminal 1: `uvicorn main:app --reload`, then press **Try again** |
| Backend won't start: port 8000 in use | Another project is running. Stop it, or use port 8001 (see the README troubleshooting table) |
| A result looks odd | Say: *"This depends on my occasion tags. Let me show why,"* then open the piece in My Wardrobe and point to its tags. It's a good moment to explain that the rules are transparent. |
| Photos missing | Check the backend terminal for errors; restart both servers |
| Data got messed up during practice | Stop the backend, replace `backend/data` with your backup copy, start again |
