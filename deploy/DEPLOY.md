# Deploying StockTest to biswas.net/sid/stocktest

The app is served at **`biswas.net/sid/stocktest`** (alongside your other `/sid`
projects). Because that path is your GitHub Pages site — which can only serve
static files — the app is split:

- **Frontend** → built static files committed to your Pages repo
  (`rahulbiswas.github.io`) at `sid/stocktest/`. Free; lives with your other projects.
- **Backend** → the FastAPI engine on a **Google Cloud Compute Engine** VM, at
  **`stocktest-api.biswas.net`** over HTTPS. The frontend calls it cross-origin
  (CORS is already open in `app.py`). Price data is downloaded on the VM, so no
  stock data lives in any repo.

> **Why a VM, not Cloud Run?** The app loads all price data into memory and
> pre-warms it at startup, then keeps it warm and runs background validation
> jobs on threads. That needs a long-running instance — Cloud Run's scale-to-zero
> model would cold-start slowly and kill in-flight jobs.

Order: stand up the backend (Part A), then deploy the frontend pointed at it
(Part B). Names like `stocktest-api` are easy to change — just keep the DNS
record, the Caddyfile hostname, and the `VITE_API_BASE` build var in sync.

---

# Part A — Backend on the Google Cloud VM

## A1. Create the VM (Google Cloud Console)

1. At <https://console.cloud.google.com>: create/select a **project** and make
   sure **billing is enabled** for it (Compute Engine requires it), then enable
   the **Compute Engine API** when prompted.
2. **Compute Engine → VM instances → Create instance:**
   - **Name:** `stocktest`. **Region:** pick one near you (e.g. `us-central1`).
   - **Machine type:** `e2-medium` (2 vCPU, **4 GB RAM**) — comfortable for the
     in-memory data + pre-warm. Budget option: `e2-small` (2 GB) works but is
     tight and may OOM during startup; bump up if so. (The Always-Free `e2-micro`
     at 1 GB is too small.)
   - **Boot disk:** Ubuntu 22.04 LTS, 20 GB standard is plenty.
   - **Firewall:** check **Allow HTTP traffic** and **Allow HTTPS traffic**
     (this creates the VPC rules for ports 80/443 — see A2 if you skip it here).
   - **SSH key** (Advanced → Security → Manage Access → Add manually): paste the
     contents of `~/.ssh/oracle_vm.pub`. The key's comment is just a label — it
     works fine for GCP. GCP maps the key to the username in it; if unsure, use
     `ssh -i ~/.ssh/oracle_vm <that-username>@<IP>` shown after creation.
   - Create, then note the **External IP**. (Reserve it as a **static** IP under
     VPC network → IP addresses so it can't change and break DNS.)

## A2. Open ports 80 and 443 (VPC firewall)

If you ticked "Allow HTTP/HTTPS traffic" in A1, this is already done. Otherwise:
**VPC network → Firewall → Create firewall rule**, Ingress, targets = your VM's
tag/all instances, source `0.0.0.0/0`, allow TCP `80` and `443`.

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

- **Cost:** a Compute Engine `e2-medium` runs ~$25/mo (24/7), `e2-small` ~$13/mo,
  plus ~$1–2/mo for the disk and a static IP. Set a **budget alert** in Billing.
  Frontend (Pages) and the data (from Yahoo) stay free.
- **Public API:** anyone can reach `stocktest-api.biswas.net` and spend your VM's
  CPU/RAM. Fine for personal use; add auth or rate-limiting before promoting it.
  You can also tighten `allow_origins` in `app.py` to just your Pages origin.
- **Backups:** only `web/backend/store/*.json` (saved strategies) is
  non-reproducible; code comes from git, data from Yahoo.
