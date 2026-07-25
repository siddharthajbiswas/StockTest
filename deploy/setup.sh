#!/usr/bin/env bash
# StockTest BACKEND setup for an Ubuntu 22.04+ VM (GCP Compute Engine).
# (The frontend is deployed separately to GitHub Pages — see DEPLOY.md.)
#
#   git clone <repo> /opt/stocktest
#   cd /opt/stocktest && sudo bash deploy/setup.sh
#
# Idempotent: safe to re-run (e.g. after `git pull`) to reinstall + restart.
# Point stocktest-api.biswas.net at this VM's public IP BEFORE running, so Caddy
# can get a TLS cert on the first try.
set -euo pipefail

APP_DIR=/opt/stocktest
# Run the service as the human who invoked `sudo` (GCP images have no default
# `ubuntu` user — the login user comes from your SSH key). Falls back to ubuntu.
APP_USER="${SUDO_USER:-ubuntu}"

echo "==> [1/6] System packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git curl ca-certificates \
	iptables-persistent debian-keyring debian-archive-keyring apt-transport-https

echo "==> [2/6] Caddy (auto-HTTPS reverse proxy)"
if ! command -v caddy >/dev/null; then
	curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
		| gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
	curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
		> /etc/apt/sources.list.d/caddy-stable.list
	apt-get update -y
	apt-get install -y caddy
fi

echo "==> [3/6] Open ports 80/443 in the host firewall (iptables)"
# GCP's default Ubuntu image does NOT block ports at the OS level (the VPC
# firewall does), so these rules are usually a harmless no-op — kept so the
# script also works on providers whose images ship a restrictive iptables.
# You STILL must allow 80/443 in the GCP VPC firewall (see DEPLOY.md A2).
for port in 80 443; do
	if ! iptables -C INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null; then
		iptables -I INPUT 6 -m state --state NEW -p tcp --dport "$port" -j ACCEPT 2>/dev/null || true
	fi
done
netfilter-persistent save 2>/dev/null || true

echo "==> [4/6] Python venv + dependencies"
cd "$APP_DIR"
if [ ! -d .venv ]; then python3 -m venv .venv; fi
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

echo "==> [5/6] Download price data (~530 tickers from Yahoo; one-time, ~10-20 min)"
if [ ! -d "$APP_DIR/data" ] || [ -z "$(ls -A "$APP_DIR/data" 2>/dev/null)" ]; then
	sudo -u "$APP_USER" "$APP_DIR/.venv/bin/python" "$APP_DIR/download_data.py"
else
	echo "    data/ already populated — skipping (use download_data.py --force to refresh)"
fi

echo "==> [6/6] Install + start services (running backend as '$APP_USER')"
sed "s/^User=ubuntu$/User=$APP_USER/" deploy/stocktest-backend.service \
	> /etc/systemd/system/stocktest-backend.service
install -m 644 deploy/Caddyfile /etc/caddy/Caddyfile
systemctl daemon-reload
systemctl enable --now stocktest-backend
systemctl restart caddy

echo
echo "Done. Backend + Caddy are running."
echo "  systemctl status stocktest-backend caddy"
echo "  curl -s http://127.0.0.1:8000/health"
echo "Once DNS has propagated: https://stocktest-api.biswas.net/health"
