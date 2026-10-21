# Put Adaa online (free Oracle Cloud server)

This puts Adaa on a server that's always on, at a free `https://your-name.duckdns.org` address, so anyone with the link can sign up from anywhere. It takes about an hour the first time. Everything here is free.

**How it fits together:** one small Ubuntu server runs Adaa (the backend also serves the app), Caddy in front of it for https, and a nightly backup. Your laptop is no longer needed for others to use Adaa.

```
phone / laptop ──https──► Caddy (free certificate) ──► Adaa (port 8000, private) ──► /var/lib/adaa (database + photos)
                                                                              nightly ──► /var/backups/adaa (newest 7)
```

You'll need:
- An **Oracle Cloud** account ("Always Free"). Sign-up asks for a debit/credit card to check you're a real person; Always Free resources aren't charged.
- A free **DuckDNS** address.
- Your laptop with PowerShell (for `ssh`, already built into Windows).

> Any other Ubuntu 24.04 server (a paid VPS from DigitalOcean, Hetzner, AWS Lightsail...) works the same way: skip steps 1–2 and open ports 80 and 443 in that provider's firewall instead.

---

## 1. Create the server

1. Sign in at [cloud.oracle.com](https://cloud.oracle.com) → **☰ → Compute → Instances → Create instance**.
2. **Name:** `adaa`.
3. **Image and shape → Edit:**
   - Image: **Canonical Ubuntu 24.04**.
   - Shape: **Ampere → VM.Standard.A1.Flex**, 1 OCPU and 6 GB memory (marked *Always Free-eligible*).
     If Oracle says **"Out of capacity"**, try another *Availability domain*, try again later, or pick **VM.Standard.E2.1.Micro** (also free; smaller, but enough for friends).
4. **Networking:** keep *Create new virtual cloud network* and *Assign a public IPv4 address*.
5. **Add SSH keys:** *Generate a key pair for me* → **Save private key**. Move the file to `C:\Users\<you>\.ssh\adaa.key`.
6. **Create**. When it says *Running*, copy the **Public IP address** (e.g. `141.148.x.x`).

## 2. Open the web ports (80 and 443)

Oracle blocks everything except SSH by default.

1. On the instance page → **Primary VNIC → Subnet** → **Security Lists** → *Default Security List* → **Add Ingress Rules**.
2. Add a rule: Source CIDR `0.0.0.0/0`, IP Protocol **TCP**, Destination Port Range **80**.
3. Add another the same way with port **443**.

(The server's own firewall is opened by the install script in step 6.)

## 3. Get a free web address

1. Go to [duckdns.org](https://www.duckdns.org) and sign in (GitHub or Google).
2. Add a sub domain, e.g. `adaa-swarangi` → you get `adaa-swarangi.duckdns.org`.
3. In its **current ip** box, paste the server's **Public IP** → **update ip**.

## 4. Connect to the server from your laptop

In PowerShell (first time only, make the key private to you, or ssh refuses it):
```powershell
icacls "$HOME\.ssh\adaa.key" /inheritance:r /grant:r "$($env:USERNAME):R"
```
Then connect (replace the IP):
```powershell
ssh -i "$HOME\.ssh\adaa.key" ubuntu@141.148.x.x
```
Type `yes` the first time. You're now typing on the server (the prompt shows `ubuntu@adaa`). Steps 5–8 run there.

## 5. Let the server download Adaa from GitHub

The repository is private, so give the server a **read-only deploy key** (it can read this one repository and nothing else).

```bash
sudo ssh-keygen -t ed25519 -f /root/.ssh/id_ed25519 -N "" -C "adaa-server"
sudo cat /root/.ssh/id_ed25519.pub
```
Copy the line it prints. On GitHub: **SwarangiK-21/Adaa- → Settings → Deploy keys → Add deploy key** → title `adaa-server`, paste, leave *Allow write access* **unticked** → **Add key**.

Back on the server:
```bash
sudo ssh -o StrictHostKeyChecking=accept-new -T git@github.com
sudo git clone git@github.com:SwarangiK-21/Adaa-.git /opt/adaa
```
The first command should say *"You've successfully authenticated"*.

## 6. Install Adaa (one command)

Use your DuckDNS address:
```bash
sudo bash /opt/adaa/deploy/install.sh adaa-swarangi.duckdns.org
```
It installs Python, Node.js and Caddy, builds the app, starts Adaa and the nightly backup, turns on https and opens ports 80/443 on the server. It takes about 5–10 minutes and ends with **Done!**

Open **https://adaa-swarangi.duckdns.org** on your phone. The first visit can take a minute while the certificate is made.

## 7. Your wardrobe on the server

Choose one:

- **Start fresh:** just sign up. Everyone, you included, starts with an empty wardrobe.
- **Move your laptop wardrobe over** (your account, pieces, looks and history; you then log in with your laptop password):
  1. On your **laptop** (PowerShell, in the `Adaa` folder):
     ```powershell
     cd backend
     .\.venv\Scripts\python.exe backup.py
     scp -i "$HOME\.ssh\adaa.key" backups\adaa-XXXXXXXX-XXXXXX.tar.gz ubuntu@141.148.x.x:/tmp/
     ```
     (Use the file name `backup.py` printed.)
  2. On the **server**:
     ```bash
     sudo systemctl stop adaa
     cd /opt/adaa/backend
     sudo -u adaa env ADAA_DATA_DIR=/var/lib/adaa .venv/bin/python backup.py --restore /tmp/adaa-XXXXXXXX-XXXXXX.tar.gz --force
     sudo systemctl start adaa
     rm /tmp/adaa-*.tar.gz
     ```
  Do this **before** friends sign up: a restore replaces everything on the server.

## 8. Email for "Forgot password?" (and your contact email)

Until this is set, reset emails only go to the server log (`sudo journalctl -u adaa`).

With Gmail (free):
1. Google Account → **Security** → turn on **2-Step Verification** → **App passwords** → create one called `Adaa`. Copy the 16 letters.
2. On the server: `sudo nano /etc/adaa.env` and fill in:
   ```
   ADAA_CONTACT_EMAIL=your.address@gmail.com
   ADAA_SMTP_HOST=smtp.gmail.com
   ADAA_SMTP_PORT=587
   ADAA_SMTP_USER=your.address@gmail.com
   ADAA_SMTP_PASSWORD=the16letterapppassword
   ADAA_MAIL_FROM=your.address@gmail.com
   ```
   Save with `Ctrl+O`, `Enter`, exit with `Ctrl+X`.
3. `sudo systemctl restart adaa`, then try **Forgot password?** on the log-in screen.

Gmail allows about 500 emails a day, plenty for password resets. (Brevo's free plan works the same way with its SMTP details.)

---

## Everyday

| To... | Run on the server |
|---|---|
| Put the newest Adaa online (after you push from your laptop) | `sudo bash /opt/adaa/deploy/update.sh` (backs up first) |
| See if Adaa is running | `systemctl status adaa` |
| See what went wrong | `sudo journalctl -u adaa -n 100` |
| Restart Adaa | `sudo systemctl restart adaa` |
| Make a backup now | `sudo systemctl start adaa-backup` |
| List backups | `sudo ls -lh /var/backups/adaa` |
| Change settings (limits, email...) | `sudo nano /etc/adaa.env`, then `sudo systemctl restart adaa` |

**Copy a backup to your laptop** now and then (the server keeps 7, all on the same disk):
```bash
# on the server
sudo cp "$(sudo ls -1t /var/backups/adaa/*.tar.gz | head -1)" /tmp/latest-adaa.tar.gz && sudo chown ubuntu /tmp/latest-adaa.tar.gz
```
```powershell
# on the laptop
scp -i "$HOME\.ssh\adaa.key" ubuntu@141.148.x.x:/tmp/latest-adaa.tar.gz .
```

**Restore a backup on the server:** `sudo systemctl stop adaa`, then the `backup.py --restore ... --force` command from step 7, then `sudo systemctl start adaa`. The replaced data is kept beside it as `adaa.db.before-restore`.

## If something's wrong

| Problem | Try |
|---|---|
| The address doesn't open at all | Ports 80 and 443 in Oracle's security list (step 2); the DuckDNS IP matches the server's Public IP (step 3). |
| Certificate / "not secure" error | Wait a minute and reload. Still failing: `sudo journalctl -u caddy -n 50` (usually the DuckDNS IP or closed ports). |
| "502" or a blank error page | Adaa isn't running: `sudo journalctl -u adaa -n 50`, then `sudo systemctl restart adaa`. |
| Reset emails don't arrive | Check spam; check `/etc/adaa.env`; `sudo journalctl -u adaa` shows "Couldn't send email" with the reason. |
| `update.sh` says "Not possible to fast-forward" | Someone edited files on the server. `sudo git -C /opt/adaa status` shows which. |

## Good to know

- **Always Free:** Oracle may stop an Always Free server that sits almost idle for a week. A few people using Adaa normally keeps it active; if it's stopped, start it again from the console (your data stays on its disk).
- **You look after people's data now.** Your contact email appears in the privacy note; people can delete their own accounts in Preferences. Deleted accounts disappear from backups within 7 days, as the oldest backup is removed.
- **Limits** (in `/etc/adaa.env`): 50 accounts, 300 pieces and 200 looks per person by default. Photos are at most 5 MB each.
- **Licences:** the clothes-recognition model used for clean cut-outs (SegFormer) is licensed for **non-commercial use only**. A free Adaa for friends is fine; it would have to be replaced before charging money.
- **The AI models** (about 200 MB) download to the server by themselves the first time someone adds a piece on a computer.
