#!/usr/bin/env bash
# Sets up the off-site copy of Adaa's nightly backup (Backblaze B2, or any S3-compatible storage),
# then runs one backup to check it works.
#
#   sudo bash /opt/adaa/deploy/backup-setup.sh
#
# It asks for the bucket's endpoint and name, and the key ID and secret key (typed in hidden, never
# shown or logged), and writes them into /etc/adaa.env (readable only by root and Adaa).
set -euo pipefail
[ "$(id -u)" = 0 ] || exec sudo bash "$0" "$@"
ENV=/etc/adaa.env
[ -f "$ENV" ] || { echo "No $ENV yet: run deploy/install.sh first."; exit 1; }
clean() { echo "$1" | tr -d '[:space:]'; }

read -rp "Endpoint (e.g. s3.us-west-004.backblazeb2.com): " ENDPOINT
ENDPOINT="$(clean "$ENDPOINT")"; ENDPOINT="${ENDPOINT#https://}"; ENDPOINT="${ENDPOINT#http://}"; ENDPOINT="${ENDPOINT%/}"
[[ "$ENDPOINT" =~ ^[A-Za-z0-9.-]+\.[A-Za-z]+$ ]] || { echo "That doesn't look like an endpoint. Run me again."; exit 1; }
if [[ "$ENDPOINT" =~ ^s3\.([a-z0-9-]+)\.backblazeb2\.com$ ]]; then REGION="${BASH_REMATCH[1]}"; else REGION=auto; fi

read -rp "Bucket name: " BUCKET
BUCKET="$(clean "$BUCKET")"
[[ "$BUCKET" =~ ^[A-Za-z0-9-]{3,63}$ ]] || { echo "That doesn't look like a bucket name. Run me again."; exit 1; }

read -rp "keyID: " KEY_ID
KEY_ID="$(clean "$KEY_ID")"
[ "${#KEY_ID}" -ge 10 ] || { echo "That keyID looks too short (${#KEY_ID} characters). Run me again."; exit 1; }

echo "Next: the applicationKey (the secret one). Paste it with Ctrl+V (or Ctrl+Shift+V), or type it."
echo "Nothing shows while you paste or type: that's normal, it keeps it secret."
SECRET=""
for attempt in 1 2 3; do
  read -rsp "applicationKey, then Enter: " SECRET; echo
  SECRET="$(clean "$SECRET")"
  [ "${#SECRET}" -ge 20 ] && break
  echo "Received ${#SECRET} characters, but the applicationKey is longer (about 31). Try again ($attempt of 3)."
  SECRET=""
done
[ -n "$SECRET" ] || { echo "No applicationKey after 3 tries. Run me again when you have it."; exit 1; }

set_var() {   # replace KEY=... in the settings file, or add it (safe for any characters in the value)
  local tmp; tmp="$(mktemp)"
  grep -v "^$1=" "$ENV" > "$tmp" || true
  printf '%s=%s\n' "$1" "$2" >> "$tmp"
  cat "$tmp" > "$ENV"; rm -f "$tmp"
}
set_var ADAA_BACKUP_S3_ENDPOINT "https://$ENDPOINT"
set_var ADAA_BACKUP_S3_BUCKET "$BUCKET"
set_var ADAA_BACKUP_S3_KEY_ID "$KEY_ID"
set_var ADAA_BACKUP_S3_SECRET "$SECRET"
set_var ADAA_BACKUP_S3_REGION "$REGION"
chown root:adaa "$ENV"; chmod 640 "$ENV"
echo "Saved the backup settings (region: $REGION)."

echo "Running one backup now to check it reaches $BUCKET..."
START="$(date '+%Y-%m-%d %H:%M:%S')"
if systemctl start adaa-backup.service && journalctl -u adaa-backup --since "$START" -o cat | grep -q "Copied off-site"; then
  echo
  echo "Done! Each night's backup is now also copied to $BUCKET."
  echo "In Backblaze, open the bucket (Browse Files): you should see a file like adaa-$(date +%Y%m%d)-....tar.gz"
else
  echo
  journalctl -u adaa-backup --since "$START" -o cat | tail -5
  echo "The settings were saved, but the off-site copy failed (see above). Check the 4 values and run me again."
  exit 1
fi
