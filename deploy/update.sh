#!/usr/bin/env bash
# Puts the newest Peheraav from GitHub on the server: backup first, then update, rebuild and restart.
#
#   sudo bash /opt/peheraav/deploy/update.sh
set -euo pipefail

APP="$(cd "$(dirname "$0")/.." && pwd)"
step() { printf '\n\033[1;35m==> %s\033[0m\n' "$*"; }

[ "$(id -u)" = 0 ] || { echo "Please run with sudo:  sudo bash $0"; exit 1; }

step "Backing up first"
systemctl start peheraav-backup.service
ls -1t /var/backups/peheraav | head -1

step "Getting the newest version"
git -C "$APP" pull --ff-only

step "Updating Python packages"
"$APP/backend/.venv/bin/pip" install -r "$APP/backend/requirements.txt" -c "$APP/backend/requirements.lock" -q

step "Rebuilding the app"
cd "$APP/frontend"
npm ci --no-audit --no-fund
npm run build

step "Restarting"
cp "$APP/deploy/peheraav.service" "$APP/deploy/peheraav-backup.service" "$APP/deploy/peheraav-backup.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl restart peheraav.service
for _ in $(seq 1 20); do
  if curl -fsS http://127.0.0.1:8000/api/health >/dev/null; then echo "Peheraav is running the new version."; exit 0; fi
  sleep 1
done
echo "Peheraav didn't come back. See: sudo journalctl -u peheraav -n 50"
exit 1
