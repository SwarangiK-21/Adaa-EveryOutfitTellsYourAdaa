# Put Adaa online

**Adaa runs at https://adaa-every-outfit-tells-your-adaa.eastasia.cloudapp.azure.com** (Azure for Students, set up on 7 Nov 2026).

Two routes, both ₹0: **Azure for Students** (no card needed: what Adaa uses) or **Oracle Cloud Always Free** (needs a Visa/Mastercard that allows international transactions; many Indian debit cards are declined). After the server exists, both use the same install script.

## Route A: Azure for Students (no credit card)

What it gives: US$100 credit and free services for 12 months, renewable every year while you're a student (verify with your college email or student ID). The B2ats_v2 / B1s server (750 hours a month: enough for 24/7) and a 64 GB P6 SSD are in the free services; the public IP comes out of the credit (a few dollars a month). With no card on file nothing is ever charged: when the credit or year ends, Microsoft emails and the services stop until you choose.

1. Sign up at **azure.microsoft.com/free/students** with your college email (or student ID). Done when the portal's *Education* page shows "US$100 out of US$100".
2. On your laptop, make the server key (once): `ssh-keygen -t ed25519 -f $HOME\.ssh\adaa_azure -N '""' -C adaa-azure-server` (create `C:\Users\<you>\.ssh` first if it doesn't exist). Keep `adaa_azure` private; `adaa_azure.pub` is the public half.
3. In the portal, open **Cloud Shell** (`>_` icon, Bash, "No storage account required"), upload or paste `deploy/azure-create-vm.sh`, and run it with the public key:
   `bash azure-create-vm.sh "<contents of adaa_azure.pub>"`
   Student subscriptions may only use some regions (Adaa's could use East Asia, India South Central, Korea Central, Malaysia West and UAE North; not Central/South India): the script reads the allowed list and tries the closest first. It ends with **Done!** and the public IP.
4. Free web address from Azure (instead of DuckDNS): `az network public-ip update -g adaa-rg -n adaa-ip-<region> --dns-name <name> --query dnsSettings.fqdn -o tsv` → `<name>.<region>.cloudapp.azure.com` (lowercase letters, digits and hyphens only).
5. Connect: `ssh -i $HOME\.ssh\adaa_azure azureuser@<public IP>`. Then follow **steps 5–10 below** (deploy key, install with your Azure address, wardrobe, email, off-site backups, uptime alerts). Ports 80/443 are already open (the script did step 2).
6. **Budget alert:** portal → *Cost Management → Budgets → Add*, amount US$10/month, alert at 50 % to your email, so any unexpected use shows up early.

## Route B: Oracle Cloud Always Free


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

The repository is public, so the server can download it directly:

```bash
sudo git clone https://github.com/SwarangiK-21/Adaa-EveryOutfitTellsYourAdaa.git /opt/adaa
```

*(For a private copy instead: make a read-only deploy key on the server with `sudo ssh-keygen -t ed25519 -f /root/.ssh/id_ed25519 -N "" -C adaa-server`, add `/root/.ssh/id_ed25519.pub` under the repository's **Settings → Deploy keys** with write access unticked, and clone with `git@github.com:<you>/<repo>.git`.)*

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

Until this is set, password-reset and email-confirmation emails only go to the server log (`sudo journalctl -u adaa`), so people can't confirm their email or reset passwords. **Set this up before inviting people.**

With Gmail (free):
1. Google Account → **Security** → turn on **2-Step Verification** → **App passwords** → create one called `Adaa`. Copy the 16 letters.
2. On the server: `sudo bash /opt/adaa/deploy/email-setup.sh`. It asks for the Gmail address and the app password (typed in hidden), saves them in `/etc/adaa.env`, sends a test email and restarts Adaa.
3. Try **Forgot password?** on the log-in screen.

Gmail allows about 500 emails a day, plenty for password resets. (Brevo's free plan works the same way with its SMTP details.)

## 9. Off-site backups (Backblaze B2, free, no card)

The nightly backup is on the server's own disk. If the server is lost, so are those backups. Backblaze B2 keeps a copy elsewhere: 10 GB free, no credit card. (Cloudflare R2 also works, but asks for a card.)

1. Sign up at [backblaze.com/sign-up/s3](https://www.backblaze.com/sign-up/s3).
2. **Buckets → Create a Bucket** → a unique name (e.g. `adaa-backups-yourname`), **Private**, encryption **Enable** → Create. Note its **Endpoint** (e.g. `s3.us-west-004.backblazeb2.com`).
3. On the bucket → **Lifecycle Settings → custom rules**: days till hide `14`, days till delete `1` (keeps two weeks).
4. **Application Keys → Add a New Application Key** → only that bucket, **Read and Write** → Create. Keep the **keyID** and **applicationKey** on screen (shown once).
5. On the server: `sudo bash /opt/adaa/deploy/backup-setup.sh`. It asks for the endpoint, bucket, keyID and applicationKey (typed in hidden), saves them in `/etc/adaa.env` and runs one backup to check it ends with **Copied off-site**.

## 10. Get told when Adaa is down (UptimeRobot, free)

1. Sign up at [uptimerobot.com](https://uptimerobot.com) (free plan).
2. **New monitor** → type **HTTP(s)** → URL `https://YOUR-ADDRESS/api/health` → every 5 minutes → alert to your email.
3. If Adaa (or the server) stops, you get an email within minutes.

## Before you invite people

- [ ] Opens on `https://` with the padlock, on a phone and a laptop
- [ ] Email settings work: sign up a test account and receive the confirmation email; try **Forgot password?**
- [ ] `ADAA_CONTACT_EMAIL` set (it's shown in the privacy note and terms)
- [ ] `sudo systemctl start adaa-backup` → "Copied off-site"
- [ ] UptimeRobot monitor is green
- [ ] Delete any test accounts (Preferences → Delete my account)

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
