# Deploying StockTest to stocktest.biswas.net on a free Oracle Cloud VM

This runs the **whole app** (React frontend + FastAPI backend + price data) on a
single Oracle Cloud "Always Free" VM, at **$0/month, permanently**, with HTTPS at
`stocktest.biswas.net`. It uses a subdomain so the existing site at `biswas.net`
stays untouched. The data is downloaded on the VM from Yahoo Finance, so nothing
is uploaded and no stock data lives in this repo.

Steps 1–3 are things only you can do (account, DNS). Step 4 is one script.

---

## 1. Create the VM (Oracle Cloud Console)

1. Sign up at <https://cloud.oracle.com>. A credit card is required for identity
   verification — the "Always Free" resources are **not** charged. Pick a home
   region close to you.
2. **Compute → Instances → Create instance:**
   - **Image:** Canonical Ubuntu 22.04 (or 24.04).
   - **Shape:** *Ampere (ARM)* → `VM.Standard.A1.Flex`. Set **2 OCPU / 12 GB RAM**
     (well within Always Free; plenty for this app). If ARM capacity is
     unavailable in your region, `VM.Standard.E2.1.Micro` (AMD, 1 GB) also works
     but is tight — retry ARM later.
   - **SSH keys:** upload your public key (or let it generate one and download it).
   - Create. Note the **public IPv4 address** once it's running.

## 2. Open ports 80 and 443 (VCN Security List)

Oracle blocks inbound traffic by default in **two** places. This step is the
cloud firewall; `setup.sh` handles the host firewall.

1. From the instance page: **Virtual Cloud Network → Subnet → Security List**.
2. Add two **Ingress Rules**: Source `0.0.0.0/0`, IP Protocol TCP, Destination
   port `80`, then another for `443`.

## 3. Point stocktest.biswas.net at the VM (DNS)

StockTest lives on a **subdomain** so it doesn't disturb the existing site at
`biswas.net` / `www.biswas.net` (a separate GitHub Pages site). You add **one**
new record and leave everything else alone.

biswas.net's DNS is on Google Cloud nameservers (`ns-cloud-*.googledomains.com`),
registrar **Squarespace**. Edit records at **<https://account.squarespace.com>
→ Domains → biswas.net → DNS Settings** (Squarespace absorbed Google Domains).
Add a custom record:

| Type | Host / Name  | Value / Data    | TTL  |
|------|--------------|-----------------|------|
| A    | `stocktest`  | *VM public IP*  | 3600 |

**Do not touch** the existing `@`/`www` records (the `185.199.x.x` GitHub Pages
IPs). Verify with `dig +short stocktest.biswas.net` — it should return the VM IP.
**Do this before step 4** so Caddy can get its TLS cert on the first attempt.
Propagation takes minutes to a few hours.

## 4. Deploy (on the VM)

SSH in: `ssh ubuntu@<VM_PUBLIC_IP>`, then:

```bash
# Clone this private repo. Easiest auth: a read-only Deploy Key —
#   ssh-keygen -t ed25519 -f ~/.ssh/deploy -N ""
#   cat ~/.ssh/deploy.pub   # add at: GitHub repo → Settings → Deploy keys → Add
#   GIT_SSH_COMMAND='ssh -i ~/.ssh/deploy' \
#     git clone git@github.com:rahulbiswas/StockTest.git /tmp/stocktest
# (or clone with a fine-grained read-only Personal Access Token over HTTPS)

sudo mv /tmp/stocktest /opt/stocktest
cd /opt/stocktest
sudo bash deploy/setup.sh
```

`setup.sh` installs Python/Node/Caddy, builds the frontend, downloads price data
(~10–20 min, one time), and starts everything as systemd services.

## 5. Verify

```bash
systemctl status stocktest-backend caddy   # both active (running)
curl -s http://127.0.0.1:8000/health        # {"status":"ok","tickers_loaded":...}
```

Open <https://stocktest.biswas.net>. If the cert isn't issued yet, confirm DNS
resolves to the VM and ports 80/443 are open (steps 2–3), then
`sudo systemctl restart caddy`.

---

## Maintenance

**Deploy code changes:**
```bash
cd /opt/stocktest && git pull && sudo bash deploy/setup.sh   # rebuilds + restarts
```

**Refresh price data** (e.g. weekly, via `crontab -e` as `ubuntu`):
```
0 6 * * 1  /opt/stocktest/.venv/bin/python /opt/stocktest/download_data.py && systemctl restart stocktest-backend
```

**Logs:** `journalctl -u stocktest-backend -f` and `journalctl -u caddy -f`.

## Notes / decisions

- **Cost:** $0 as long as you stay on Always Free shapes. Oracle reclaims *idle*
  Always Free ARM VMs — this one runs a web server 24/7, so it stays active.
- **Public exposure:** anyone can reach the site and trigger backtests (CPU/RAM
  on your VM). Fine for personal use; add auth or rate-limiting before sharing
  widely.
- **Backups:** the only non-reproducible state is `web/backend/store/*.json`
  (saved strategies). Everything else — code from git, data from Yahoo — rebuilds.
