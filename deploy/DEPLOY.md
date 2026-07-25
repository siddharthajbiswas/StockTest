# Deploying StockTest to biswas.net/sid/stocktest

The app is served at **`biswas.net/sid/stocktest`** (alongside your other `/sid`
projects). Because that path is your GitHub Pages site — which can only serve
static files — the app is split:

- **Frontend** → built static files committed to your Pages repo
  (`rahulbiswas.github.io`) at `sid/stocktest/`. Free; lives with your other projects.
- **Backend** → the FastAPI engine on a free Oracle Cloud "Always Free" VM, at
  **`stocktest-api.biswas.net`** over HTTPS. The frontend calls it cross-origin
  (CORS is already open in `app.py`). Price data is downloaded on the VM, so no
  stock data lives in any repo.

Order: stand up the backend (Part A), then deploy the frontend pointed at it
(Part B). Names like `stocktest-api` are easy to change — just keep the DNS
record, the Caddyfile hostname, and the `VITE_API_BASE` build var in sync.

---

# Part A — Backend on the Oracle VM

## A1. Create the VM (Oracle Cloud Console)

1. Sign up at <https://cloud.oracle.com>. A credit card is required for identity
   verification — "Always Free" resources are **not** charged. Pick a home region.
2. **Compute → Instances → Create instance:**
   - **Image:** Canonical Ubuntu 22.04 (or 24.04).
   - **Shape:** *Ampere (ARM)* → `VM.Standard.A1.Flex`, **2 OCPU / 12 GB RAM**
     (within Always Free). If ARM capacity is unavailable, retry later or use
     `VM.Standard.E2.1.Micro` (AMD, 1 GB — tight).
   - **SSH keys:** upload `~/.ssh/oracle_vm.pub`.
   - Create, then note the **public IPv4 address**.

## A2. Open ports 80 and 443 (VCN Security List)

Oracle blocks inbound in two places; this is the cloud firewall (`setup.sh` does
the host firewall). Instance page → **Virtual Cloud Network → Subnet → Security
List** → add two **Ingress Rules**: Source `0.0.0.0/0`, TCP, dest port `80`, then
`443`.

## A3. DNS: point stocktest-api.biswas.net at the VM

biswas.net's DNS is on Google Cloud nameservers, registrar **Squarespace**. Edit
at **<https://account.squarespace.com> → Domains → biswas.net → DNS Settings**.
Add **one** record — leave every existing record alone:

| Type | Host / Name       | Value / Data   | TTL  |
|------|-------------------|----------------|------|
| A    | `stocktest-api`   | *VM public IP* | 3600 |

Verify: `dig +short stocktest-api.biswas.net` → the VM IP. Do this **before A4**
so Caddy gets its cert on the first attempt.

## A4. Deploy the backend (on the VM)

`ssh -i ~/.ssh/oracle_vm ubuntu@<VM_PUBLIC_IP>`, then:

```bash
# Clone this private repo. Easiest auth: a read-only Deploy Key —
#   ssh-keygen -t ed25519 -f ~/.ssh/deploy -N ""
#   cat ~/.ssh/deploy.pub   # add at: GitHub repo → Settings → Deploy keys
#   GIT_SSH_COMMAND='ssh -i ~/.ssh/deploy' \
#     git clone git@github.com:rahulbiswas/StockTest.git /tmp/stocktest
sudo mv /tmp/stocktest /opt/stocktest
cd /opt/stocktest
sudo bash deploy/setup.sh          # Python + Caddy + data + services
```

Verify: `curl -s https://stocktest-api.biswas.net/health` →
`{"status":"ok","tickers_loaded":...}`.

---

# Part B — Frontend on GitHub Pages

Build the app pointed at the backend, with its public base path, and drop it into
the Pages repo. Run this **on your Mac** (not the VM):

```bash
STOCKTEST=<path to this repo>          # the StockTest working copy
PAGES=<path to your rahulbiswas.github.io working copy>

cd "$STOCKTEST/web/frontend"
VITE_BASE=/sid/stocktest/ \
VITE_API_BASE=https://stocktest-api.biswas.net \
  npm ci && npm run build              # outputs dist/

rm -rf "$PAGES/sid/stocktest"
mkdir -p "$PAGES/sid/stocktest"
cp -R dist/. "$PAGES/sid/stocktest/"

cd "$PAGES"
git add sid/stocktest
git commit -m "Add StockTest app at /sid/stocktest"
git push                               # publishes to biswas.net/sid/stocktest
```

Open <https://biswas.net/sid/stocktest/>. (Optionally add a link/card to it from
your `sid/index.html` landing page.)

---

## Maintenance

**Backend code change:** `cd /opt/stocktest && git pull && sudo bash deploy/setup.sh`.

**Frontend change:** re-run the Part B build + copy + push.

**Refresh price data** (weekly, `crontab -e` as `ubuntu` on the VM):
```
0 6 * * 1  /opt/stocktest/.venv/bin/python /opt/stocktest/download_data.py && systemctl restart stocktest-backend
```

**Logs (VM):** `journalctl -u stocktest-backend -f`, `journalctl -u caddy -f`.

## Notes

- **Cost:** $0 on Always Free shapes. This VM runs a web server 24/7, so Oracle
  won't reclaim it as idle.
- **Public API:** anyone can reach `stocktest-api.biswas.net` and spend your VM's
  CPU/RAM. Fine for personal use; add auth or rate-limiting before promoting it.
  You can also tighten `allow_origins` in `app.py` to just your Pages origin.
- **Backups:** only `web/backend/store/*.json` (saved strategies) is
  non-reproducible; code comes from git, data from Yahoo.
