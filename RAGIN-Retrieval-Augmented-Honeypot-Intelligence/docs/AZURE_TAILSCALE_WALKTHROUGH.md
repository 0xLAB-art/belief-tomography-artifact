# Azure + Tailscale Field Walkthrough — Click-by-Click

**Purpose:** take the field deployment from "subscription disabled" to "three
smoked arms" with zero guesswork. Every command matches the repo scripts as
committed; nothing here requires the agent to hold credentials.

**Roles:** every step marked **[YOU]** is portal/console work only you can do
(browser sign-in, keys). Steps marked **[CLI/agent]** can be run here afterward.

**Time:** ~30 min portal/console + ~25 min per arm of automated provisioning.
**Budget reality:** the 750 free VM-hours is ONE pool per subscription, not
per VM — 3 always-on B1s VMs bill ≈ $15/mo compute + ~$11/mo static IPs
(≈ $26/mo total), or ≈ $0 compute if the field window runs inside the
remaining free-trial credit. Confirm in Cost Management before launch.

---

## Phase A — Reactivate the Azure subscription [YOU, portal]

> **Known state of this subscription (verified via ARM 2026-09-29):**
> free-trial quota (`FreeTrial_2014-09-01`), spending limit **On**,
> state **Disabled**. Expect step 4's *Upgrade* branch, not *Reactivate*:
> conversion to pay-as-you-go is the only re-enable path once trial credit
> is exhausted. Budget note below applies from the moment of conversion.

1. Open **https://portal.azure.com** and sign in with the account that owns
   the subscription (`8110178a-4797-4682-88b1-3aa5db08b521`).
2. Top search bar → type **Subscriptions** → click **Subscriptions**.
3. Click **"Azure subscription 1"**.
4. Read the banner:
   - *Spend limit reached / subscription disabled* → click **Reactivate**.
   - *Payment method issue* → **Manage payment methods** → fix or replace the
     card, then retry activation.
   - Free-trial credit exhausted → convert: click **Upgrade** (pay-as-you-go);
     the free-tier service allowances for the first 12 months still apply.
5. Refresh the overview. Status must read **Active**. (The CLI can show a
   cached `Enabled` while the portal still says disabled — the portal is the
   source of truth.)

**[CLI/agent] verify:**
```bash
az login
az account set --subscription 8110178a-4797-4682-88b1-3aa5db08b521
bash scripts/provision_azure_field.sh --probe   # expect: "PROBE PASS"
```
`--probe` writes a scratch resource group and fails honestly on
`ReadOnlyDisabledSubscription` — if it passes, every later step will too.

## Phase B — Tailscale auth keys [YOU, admin console]

1. Open **https://login.tailscale.com/admin/settings/keys** (sign in with the
   identity your tailnet uses).
2. **Generate auth key** and set exactly:
   - **Reusable:** OFF (single-use — one key per VM, they never overlap)
   - **Expiration:** 90 days (outlives the field window)
   - **Ephemeral:** OFF (VMs must persist in the tailnet)
   - **Pre-approved:** ON if the tailnet requires device approval
   - **Tags:** optional, e.g. `tag:field` (create the tag under Access
     Controls first if you use it)
3. **Generate** → COPY the key now (`tskey-auth-…`); it is shown once. Store
   it in the private ops store, NOT in the repo.
4. Repeat twice more — you need **3 separate single-use keys**, one per arm:
   `field-cowrie`, `field-vanilla`, `field-ragin`. (A reused key fails on the
   second VM — that is expected.)

Also check the ops store has `results/cti_audit_blinding_key.json` (it is
git-ignored by design); it must be backed up there before any eval work.

## Phase C — Provision the three arms [CLI/agent, after A+B]

One arm at a time; each VM in a DIFFERENT Azure region (the script enforces
this — separate IP prefixes are part of the study design):

```bash
bash scripts/provision_azure_field.sh cowrie  eastus2
bash scripts/provision_azure_field.sh vanilla westus2
bash scripts/provision_azure_field.sh ragin   northcentralus
```

Each run prints the VM's public IP and the per-arm next steps. For each arm:

1. Wait ~2 min for cloud-init, then check it:
   ```bash
   ssh azureuser@<IP> 'cloud-init status --wait && tail -5 /opt/ragin/README.txt'
   ```
2. Install Tailscale on the VM and join the tailnet with THAT arm's key:
   ```bash
   ssh azureuser@<IP> 'curl -fsSL https://tailscale.com/install.sh | sh'
   ssh azureuser@<IP> 'sudo tailscale up --ssh --authkey <SINGLE_USE_KEY_FOR_THIS_ARM>'
   ```
   From then on prefer tailnet SSH (`ssh azureuser@field-cowrie` after
   `tailscale status`) — the public NSG only keeps :22 for bootstrap.
3. rsync the repo and bring up compose:
   ```bash
   rsync -az --exclude .git --exclude data/sessions ./ azureuser@<IP>:/opt/ragin/repo/
   ssh azureuser@<IP>   # then on the VM:
   cp .env.field.example .env.field && vi .env.field   # per-arm LLM values
   docker compose -f docker-compose.field.yml --env-file .env.field up -d
   sudo bash scripts/field_provision.sh <arm>          # egress lockdown AFTER pulls
   ```
4. Smoke gate (run from the operator laptop, not the VM):
   ```bash
   .venv/bin/python scripts/field_smoke_ssh.py --host <IP> --arm <arm>
   ```
   Exit 0 = arm is live per FIELD_LAUNCH_CHECKLIST §4 go/no-go (a).

## Phase D — Verify [CLI/agent]

```bash
az vm list -g ragin-field-rg -o table                     # 3 VMs running
tailscale status | grep field-                            # 3 tailnet devices
cat results/azure_field_endpoints.jsonl                   # arm/IP records for ops log
```

Record the 3 IPs + tailnet hostnames in the PRIVATE ops log
(docs/ops/OPS_LOG_TEMPLATE.md) — never in a committed file.

## Failure modes (all seen before)

| Symptom | Cause | Fix |
|---|---|---|
| `PROBE` fails with `ReadOnlyDisabledSubscription` | Phase A not done / billing hold persists | redo Phase A, refresh portal, re-probe |
| `tailscale up` rejects key | key reused or expired | generate a NEW single-use key (Phase B) |
| `az login` times out in this sandbox | interactive browser needed | run `az login` in your own terminal, then tell the agent |
| compose `up` fails on LLM serve | `.env.field` missing/wrong | `cp .env.field.example .env.field`, fill per-arm values |
| smoke gate banner timeout | NSG or honeypot not listening | re-run `field_provision.sh <arm>`; check `docker ps` on the VM |
