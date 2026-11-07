#!/usr/bin/env bash
# Sets up Adaa on a fresh Ubuntu 24.04 server (Oracle Cloud, or any VPS), with https.
#
#   sudo git clone https://github.com/SwarangiK-21/Adaa-.git /opt/adaa
#   sudo bash /opt/adaa/deploy/install.sh your-name.duckdns.org
#
# Safe to run again: it skips what's already done and never touches existing data or settings.
set -euo pipefail

DOMAIN="${1:-}"
APP="$(cd "$(dirname "$0")/.." && pwd)"
DATA=/var/lib/adaa
BACKUPS=/var/backups/adaa

step() { printf '\n\033[1;35m==> %s\033[0m\n' "$*"; }
fail() { printf '\n\033[1;31m%s\033[0m\n' "$*"; exit 1; }

[ "$(id -u)" = 0 ] || fail "Please run with sudo:  sudo bash $0 your-name.duckdns.org"
[ -n "$DOMAIN" ] || fail "Please give your web address:  sudo bash $0 your-name.duckdns.org"
[[ "$DOMAIN" =~ ^[A-Za-z0-9.-]+$ ]] || fail "That doesn't look like a web address: $DOMAIN"
[ "$APP" = /opt/adaa ] || fail "Please clone Adaa into /opt/adaa (the service files expect it there)."

step "Installing system packages (Python, Node.js, git)"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-venv python3-pip nodejs npm git curl gnupg sqlite3 \
  debian-keyring debian-archive-keyring apt-transport-https
NODE_MAJOR="$(node -v | sed 's/^v\([0-9]*\).*/\1/')"
[ "$NODE_MAJOR" -ge 18 ] || fail "Node.js 18 or newer is needed (found $(node -v)). Use Ubuntu 24.04."

if [ "$(awk '/MemTotal/ {print $2}' /proc/meminfo)" -lt 1900000 ] && ! swapon --show | grep -q .; then
  step "Adding 2 GB of swap (this server has little memory; building the app needs it)"
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

if ! command -v caddy >/dev/null; then
  step "Installing Caddy (https web server)"
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
  chmod o+r /usr/share/keyrings/caddy-stable-archive-keyring.gpg /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -y
  apt-get install -y caddy
fi

step "Creating the adaa user and its folders"
id adaa >/dev/null 2>&1 || useradd --system --home-dir "$DATA" --shell /usr/sbin/nologin adaa
mkdir -p "$DATA" "$BACKUPS"
chown adaa:adaa "$DATA" "$BACKUPS"
chmod 750 "$DATA" "$BACKUPS"

step "Installing Adaa's Python packages"
[ -d "$APP/backend/.venv" ] || python3 -m venv "$APP/backend/.venv"
"$APP/backend/.venv/bin/pip" install --upgrade pip -q
"$APP/backend/.venv/bin/pip" install -r "$APP/backend/requirements.txt" -c "$APP/backend/requirements.lock" -q

step "Building the app (a few minutes on a small server)"
cd "$APP/frontend"
npm ci --no-audit --no-fund
npm run build

step "Settings (/etc/adaa.env)"
if [ ! -f /etc/adaa.env ]; then
  sed "s/YOUR-DOMAIN/$DOMAIN/g" "$APP/deploy/adaa.env.example" > /etc/adaa.env
  echo "Created /etc/adaa.env. Add your email settings there later (see docs/DEPLOY.md)."
else
  echo "/etc/adaa.env already exists: left as it is."
fi
chown root:adaa /etc/adaa.env
chmod 640 /etc/adaa.env

step "Keeping server logs for 30 days at most (as the privacy note says)"
mkdir -p /etc/systemd/journald.conf.d
printf '%s\n' '[Journal]' 'MaxRetentionSec=30day' > /etc/systemd/journald.conf.d/adaa.conf
systemctl restart systemd-journald

step "Starting Adaa and the nightly backup"
cp "$APP/deploy/adaa.service" "$APP/deploy/adaa-backup.service" "$APP/deploy/adaa-backup.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now adaa.service adaa-backup.timer
systemctl restart adaa.service

step "Turning on https for $DOMAIN"
sed "s/YOUR-DOMAIN/$DOMAIN/g" "$APP/deploy/Caddyfile" > /etc/caddy/Caddyfile
systemctl enable caddy >/dev/null
systemctl restart caddy

step "Opening the web ports (80 and 443) in the server's own firewall"
for port in 80 443; do
  iptables -C INPUT -p tcp -m state --state NEW --dport "$port" -j ACCEPT 2>/dev/null \
    || iptables -I INPUT 1 -p tcp -m state --state NEW --dport "$port" -j ACCEPT
done
if command -v netfilter-persistent >/dev/null; then netfilter-persistent save >/dev/null; fi
if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then ufw allow 80,443/tcp; fi

step "Checking"
for _ in $(seq 1 20); do
  if curl -fsS http://127.0.0.1:8000/api/health >/dev/null; then break; fi
  sleep 1
done
curl -fsS http://127.0.0.1:8000/api/health >/dev/null || fail "Adaa didn't start. See: sudo journalctl -u adaa -n 50"
echo "Adaa is running."
printf '\n\033[1;32mDone!\033[0m Open https://%s (the certificate can take a minute the first time).\n' "$DOMAIN"
echo "If it doesn't open, check that ports 80 and 443 are open in your provider's firewall (Oracle security list / Azure network security group)."
