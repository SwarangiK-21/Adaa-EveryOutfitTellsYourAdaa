# Seeing outfits on yourself (virtual try-on)

Adaa can show **you** wearing the outfits it suggests. It uses an open-source AI model (**CatVTON**) running on a **free Google Colab GPU in your own Google account**. Your laptop doesn't need a graphics card.

## How it works

1. Adaa keeps your full-length photo on your laptop (`backend/data/`).
2. When you ask for outfits, Adaa sends your photo and the garment photo to **your** Colab notebook.
3. The notebook puts the garment on you and sends the picture back. Adaa saves it, so seeing the same look again is instant.
4. Bottoms are put on first, then tops; dresses, gowns and sarees go on in one step. Shoes go on last (experimental, can be switched off).
5. **For accuracy**, each garment photo is cleaned first:
   - If the photo shows someone wearing it, only that garment is kept.
   - Otherwise its background (hanger, wall) is removed.
   - Everything outside the changed area of *your* photo (face, hair, background) is kept exactly as it was.

## One-time setup in Adaa

1. **Add your photo.** Adaa asks for it the first time you open the app. You can also add it later in **Preferences → Your photo**.
   - full length, head to feet
   - standing straight, facing the camera
   - fitted, plain clothes
   - good light, plain background
   - JPEG/PNG/WebP up to 5 MB (iPhone HEIC: export as JPEG)

## Every time you want try-on

### 1. Start the notebook (about 5–10 minutes the first time, 3–5 minutes after that)

1. Go to https://colab.research.google.com and sign in with your Google account.
2. **File → Upload notebook** → choose `tryon/Adaa_TryOn_Colab.ipynb` from this project.
3. **Runtime → Change runtime type → T4 GPU → Save**.
4. **Runtime → Run all**. If Colab warns that the notebook isn't from Google, click **Run anyway**: it's this project's notebook.
5. Wait for the last cell to print:
   ```
   Paste these into Adaa > Preferences > Try-on server:
     Server link : https://something-random.trycloudflare.com
     Token       : AbC123...
   ```

### 2. Connect Adaa

1. Start Adaa as usual (backend + frontend).
2. Go to **Preferences → Try-on server**, paste the **Server link** and **Token**, then press **Save**.
3. Press **Test connection**. You should see **"Connected: CatVTON on Tesla T4."**

### 3. Use it

- **AI Stylist:** each look first shows the drawn model with *"Putting this look on you…"*, then switches to **you**, labelled **AI try-on · approximation**. Looks are made one at a time, roughly **30–90 seconds each** on the free GPU.
- **Swap** a top, bottom or dress: the picture fades with *"Updating for your swap…"* and then updates. Swapping back to an earlier combination is instant.
- **Saved Looks:** press **Show it on me** on any look.

**Keep the Colab tab open** while you use Adaa. Each time Colab restarts, the **link and token change**: paste the new ones in Preferences.

## Good to know

| | |
|---|---|
| **What's shown on you** | Tops, bottoms and dresses/gowns/sarees, and **shoes (experimental)**. Jewellery, watches, bags, dupattas and jackets **aren't** drawn on you; the caption lists them, and their real photos stay in the product cards. |
| **Quality setting** (Preferences) | **High** = 50 steps, sharper, about 1.5× slower (default). **Standard** = 30 steps, faster. |
| **Shoes setting** (Preferences) | On by default. CatVTON is trained on clothes, so shoes can look rough. If your feet can't be found, you keep the clothes result and see a note. |
| **Why not jewellery or watches?** | They're only a few pixels big in a full-length photo, and no free try-on model handles them. Pasting product photos onto you would look fake, so they stay as product cards. |
| **Accuracy** | It's an AI approximation: details like prints, fit and length can be off. That's why it's always labelled. |
| **Best garment photos** | Garment laid flat or on a hanger, plain background, whole garment visible. Photos of the garment on another person work less well. |
| **Free limits** | Colab's free GPU has daily usage limits and disconnects after idle time. When that happens, Adaa falls back to the drawn model and says why. |
| **Privacy** | Photos go only from your laptop to your own Colab session. The tunnel link is random and protected by the token. Nothing is kept in Colab after the session ends. |
| **Licence** | CatVTON is CC BY-NC-SA 4.0: **non-commercial use only**. Fine for this student project; a commercial Adaa would need a different model or a licence. |
| **Colab's rules** | Colab's free tier is meant for interactive use. Running this service while you're actively using Adaa is that, but Google can still disconnect sessions at any time. |

## If something goes wrong

| What you see | What to do |
|---|---|
| *"Can't reach your try-on server…"* | Colab disconnected or was restarted. Run the notebook again (**Runtime → Run all**), paste the new link and token, then press **Try again** on the look. |
| *"The token was rejected"* | Copy the token again from the last Colab cell (no spaces). |
| *"…couldn't find you clearly in your photo"* | Use a clearer full-length, front-facing photo (Preferences → Your photo → Replace). |
| An error while the notebook installs or loads | Colab updates its software often. Copy the red error text and ask for help; usually one version number needs changing. |
| *"…safety filter blocked this picture…"* | The model's built-in safety filter sometimes blocks ordinary outfits by mistake (short skirts, crop tops, bare shoulders). Adaa shows the drawing for that look instead. It's left on on purpose, so the tool can't be misused on other people's photos. A photo with plainer, more covered clothing underneath can help. |
| A big "NSFW" warning picture instead of you | You're running an **older copy** of the notebook. Upload the current `tryon/Adaa_TryOn_Colab.ipynb` again and *Run all*. |
| Very slow first image | The first try-on after starting warms up the GPU; later ones are faster. |
