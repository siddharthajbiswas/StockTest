#!/usr/bin/env bash
# StockTest one-shot server setup for an Ubuntu 22.04+ Oracle "Always Free" VM.
#
#   git clone <repo> /opt/stocktest
#   cd /opt/stocktest && sudo bash deploy/setup.sh
#
# Idempotent: safe to re-run (e.g. after `git pull`) to rebuild + restart.
# Point biswas.net at this VM's public IP BEFORE running, so Caddy can get a
# TLS cert on the first try.
set -euo pipefail

APP_DIR=/opt/stocktest
APP_USER=ubuntu

echo "==> [1/7] System packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git curl ca-certificates \
	iptables-persistent debian-keyring debian-archive-keyring apt-transport-https

echo "==> [2/7] Node.js 20 (to build the frontend)"
if ! command -v node >/dev/null || [ "$(node -v | cut -c2-3)" -lt 18 ]; then
	curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
	apt-get install -y nodejs
fi

echo "==> [3/7] Caddy (auto-HTTPS reverse proxy)"
if ! command -v caddy >/dev/null; then
	curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
		| gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
	curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
		> /etc/apt/sources.list.d/caddy-stable.list
	apt-get update -y
	apt-get install -y caddy
fi

echo "==> [4/7] Open ports 80/443 in the host firewall (iptables)"
# Oracle's Ubuntu image drops most inbound traffic by default. (You must ALSO
# allow 80/443 in the VCN Security List / NSG from the Oracle console.)
for port in 80 443; do
	if ! iptables -C INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null; then
		iptables -I INPUT 6 -m state --state NEW -p tcp --dport "$port" -j ACCEPT
	fi
done
netfilter-persistent save

echo "==> [5/7] Python venv + dependencies"
cd "$APP_DIR"
if [ ! -d .venv ]; then python3 -m venv .venv; fi
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

echo "==> [6/7] Build frontend + download price data"
sudo -u "$APP_USER" bash -c "cd '$APP_DIR/web/frontend' && npm ci && npm run build"
# ~530 tickers from Yahoo; one-time, ~10-20 min. Skips tickers already present.
if [ ! -d "$APP_DIR/data" ] || [ -z "$(ls -A "$APP_DIR/data" 2>/dev/null)" ]; then
	echo "    downloading price data (this takes a while)..."
	sudo -u "$APP_USER" "$APP_DIR/.venv/bin/python" "$APP_DIR/download_data.py"
else
	echo "    data/ already populated — skipping download (use download_data.py --force to refresh)"
fi

echo "==> [7/7] Install + start services"
install -m 644 deploy/stocktest-backend.service /etc/systemd/system/stocktest-backend.service
install -m 644 deploy/Caddyfile /etc/caddy/Caddyfile
systemctl daemon-reload
systemctl enable --now stocktest-backend
systemctl restart caddy

echo
echo "Done. Backend + Caddy are running."
echo "  systemctl status stocktest-backend caddy"
echo "  curl -s http://127.0.0.1:8000/health"
echo "Once DNS has propagated, https://biswas.net should serve the app."
