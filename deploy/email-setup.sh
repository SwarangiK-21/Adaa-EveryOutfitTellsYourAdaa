#!/usr/bin/env bash
# Sets up Peheraav's email (Gmail app password) on the server, then sends a test email.
#
#   sudo bash /opt/peheraav/deploy/email-setup.sh
#
# It asks for Peheraav's Gmail address and its 16-letter app password (typed in hidden, never shown or
# logged), writes them into /etc/peheraav.env (readable only by root and Peheraav), restarts Peheraav and
# checks that Gmail accepts the login by sending a test email to that address.
set -euo pipefail
[ "$(id -u)" = 0 ] || exec sudo bash "$0" "$@"
ENV=/etc/peheraav.env
[ -f "$ENV" ] || { echo "No $ENV yet: run deploy/install.sh first."; exit 1; }

read -rp "Peheraav's Gmail address: " ADDR
ADDR="$(echo "$ADDR" | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')"
[[ "$ADDR" =~ ^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]+$ ]] || { echo "That doesn't look like an email address. Run me again."; exit 1; }

echo "Next: the 16-letter app password. Paste it with Ctrl+V (or Ctrl+Shift+V), or type it."
echo "Nothing shows while you paste or type: that's normal, it keeps it secret."
for attempt in 1 2 3; do
  read -rsp "App password, then Enter: " PASS; echo
  PASS="$(echo "$PASS" | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')"
  [[ "$PASS" =~ ^[a-z]{16}$ ]] && break
  echo "Received ${#PASS} letters, but an app password has 16 (spaces don't matter). Try again ($attempt of 3)."
  PASS=""
done
[ -n "$PASS" ] || { echo "No valid app password after 3 tries. Run me again when you have it."; exit 1; }

set_var() {   # replace KEY=... in the settings file, or add it
  if grep -q "^$1=" "$ENV"; then sed -i "s|^$1=.*|$1=$2|" "$ENV"; else echo "$1=$2" >> "$ENV"; fi
}
set_var PEHERAAV_CONTACT_EMAIL "$ADDR"
set_var PEHERAAV_SMTP_HOST smtp.gmail.com
set_var PEHERAAV_SMTP_PORT 587
set_var PEHERAAV_SMTP_USER "$ADDR"
set_var PEHERAAV_SMTP_PASSWORD "$PASS"
set_var PEHERAAV_MAIL_FROM "$ADDR"
chown root:peheraav "$ENV"; chmod 640 "$ENV"
echo "Saved the email settings."

echo "Checking that Gmail accepts them (sending a test email to $ADDR)..."
if ADDR="$ADDR" PASS="$PASS" /opt/peheraav/backend/.venv/bin/python - <<'PY'
import os, smtplib, ssl, sys
from email.message import EmailMessage
addr, password = os.environ["ADDR"], os.environ["PASS"]
msg = EmailMessage()
msg["From"], msg["To"], msg["Subject"] = f"Peheraav <{addr}>", addr, "Peheraav can send emails"
msg.set_content("This is a test from your Peheraav server. Confirmation and password-reset emails will come from this address.")
try:
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as s:
        s.starttls(context=ssl.create_default_context())
        s.login(addr, password)
        s.send_message(msg)
except smtplib.SMTPAuthenticationError:
    print("Gmail refused the login. Check: 2-Step Verification is ON for this Gmail, and the app password was created while signed in to it.")
    sys.exit(1)
except Exception as exc:
    print(f"Couldn't send: {exc}")
    sys.exit(1)
PY
then
  systemctl restart peheraav
  echo
  echo "Done! Peheraav now sends emails from $ADDR (and shows it as the contact address)."
  echo "Look for the test email 'Peheraav can send emails' in that inbox."
else
  echo "The settings were saved, but the test failed (see above). Fix it and run me again."
  exit 1
fi
