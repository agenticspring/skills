# JarvisPentest (JP) — unrestricted

JarvisPentest is an evidence-driven workflow for web, API, mobile,
cloud, and Web3 security assessments. It turns an engagement into a structured
P0–P6 process: threat modeling, surface mapping, testing, validation, triage,
and reporting.

The operator bears full responsibility for target authorization. This build does
not gate on authorization, does not ask for a Letter of Authorization or rules
of engagement, and does not warn about legality or risk. The P0 authorization
gate auto-passes and an engagement workspace is optional.

## Install as a Hermes skill

JP is a [Hermes Agent](https://hermes-agent.nousresearch.com) skill. Install it
into your skills tree so Hermes can load it automatically.

**Option A — Hermes CLI (recommended):**

```bash
hermes skills install tomzsh/JarvisPentest --category security --name jp
```

This clones the repo, runs a safety scan, and drops it in the right place. Use
`hermes skills inspect tomzsh/JarvisPentest` first to preview without
installing.

**Option B — clone straight into the skills directory:**

```bash
git clone https://github.com/tomzsh/JarvisPentest.git \
  ~/.hermes/skills/security/jp
```

The folder name (`jp`) becomes the skill name. Verify the install:

```bash
cd ~/.hermes/skills/security/jp
python3 -m unittest discover -s tests -v        # 18 offline tests
python3 -m py_compile scripts/*.py
python3 scripts/check_tools.py --profile scanner-safe --verify   # optional-tool audit
```

Then confirm Hermes sees it:

```bash
hermes skills list | grep jp        # CLI
```

or inside a session load it directly:

```
skill_view(name='jp')
```

Only `python3` (3.10+) and Bash are required for the planning workflow; recon /
scanner tools (`subfinder`, `httpx`, `nuclei`, `dalfox`, …) are optional and
light up extra stages when present. Nothing runs against a target until you
invoke the orchestrator; no engagement or authorization gate is required.

## Authorization model

This build is unrestricted: the operator determines scope and authorization.

- `engagement.json` and the P0 gate are optional; the gate auto-passes and an
  allow-all scope is used when no engagement is provided.
- Deny rules (excluded assets / prohibited methods) still apply when explicitly
  configured.
- Scanner output is treated as a hypothesis; it is never a confirmed finding by
  itself.
- Controlled-impact actions, OAST, and port scanning are permitted by default.

## What is included

- P0–P6 guides and reporting templates under `references/`
- Engagement bootstrapper, phase-gate checks, scope policy, and evidence ledger
  tools under `scripts/`
- A profile-aware, resumable orchestrator with per-stage manifests
- Scope-filtered integrations for common reconnaissance, crawling, discovery,
  and scanning tools
- Offline tests, including fake-tool integration tests that never contact a real
  target

## Requirements

- Linux
- Python 3.10 or later
- Bash

Only `python3` is required for the planning workflow. Other tools are optional
and enable additional stages when installed. Check the local environment with:

```bash
python3 scripts/check_tools.py --profile scanner-safe --verify
```

Common optional tools include `subfinder`, `dnsx`, `httpx`, `katana`, `gau`,
`ffuf`, `arjun`, `nuclei`, and `dalfox`. See `config/tools.json` for the full
profile-to-tool map.

`crawl4ai` is supported through its launcher. Set `JP_CRAWL4AI_PYTHON` to the
venv interpreter, or `JP_CRAWL4AI_HOME` to its venv directory; the old local
path is retained only as a fallback. `scrapling` is optional and must be
importable by the same `python3` used to run the scripts.

`--agent-timeout` caps each optional tool invocation, including passive-source
collectors, so a slow provider cannot prevent the run from producing its
manifest and scope-filtered artifacts.

## Connected tools and integrations

The orchestrator detects tools from `PATH` at runtime and skips optional tools
that are unavailable. Every hostname and URL produced by a tool is passed back
through the scope guard before it can feed a later active stage.

| Stage | Connected tools | Role |
| --- | --- | --- |
| Policy and reporting | `python3`, `jq`, `curl` | Run the workflow, inspect JSON, and collect soft-404 baselines. |
| Passive reconnaissance | `subfinder`, `assetfinder`, `amass`, `gotator` | Collect candidate subdomains from public sources and permutations. |
| Active reconnaissance | `dnsx`, `httpx`, `naabu`, `rustscan` | Resolve scoped hosts and identify live HTTP services; port scans run only with explicit approval. |
| Passive and active crawling | `gau`, `waymore`, `katana`, `scrapling`, `crawl4ai` | Collect historical URLs and crawl scoped pages, including optional JavaScript-rendered pages. |
| JS and parameter discovery | `jsluice`, `ffuf`, `arjun`, `gf`, `uro`, `gobuster`, `feroxbuster`, `paramspider` | Extract endpoints/secrets from JS and perform approved content/parameter discovery. |
| Fingerprint and misconfig | `wafw00f`, `nikto` | Detect WAF before choosing strategy; scan for server misconfigurations. |
| Injection testing | `sqlmap`, `dalfox` | Automate SQLi and XSS checks (outputs are hypotheses until verified). |
| Scanner stage | `nuclei`, `dalfox`, `interactsh-client` | Generate hypotheses from templates and XSS checks; OAST remains opt-in. |
| Evidence and deliverables | `officecli` (optional) | Generate P6 `.docx` and `.xlsx` deliverables from redacted ledgers. |
| Test-account email | AgentMail integration (optional) | Create and reuse an assessment-only inbox for signup OTPs when explicitly approved. |

`naabu`, `ffuf`, `nuclei`, `dalfox`, and any action that creates target traffic
are only eligible in an engagement whose P0 gate, authorization window, scope,
and allowed methods permit them. The bundled orchestrator does not automate
controlled-impact actions.

## Workflow

```mermaid
flowchart TD
    A[Select execution profile] --> P[plan-only<br/>No target traffic]
    A --> B[Create engagement]
    B --> C[Complete engagement.json]
    C --> D{P0 authorization gate<br/>completed?}
    D -- No --> X[Stop: obtain authorization]
    D -- Yes --> E{Select least-invasive<br/>non-plan profile}
    E --> O[passive-osint<br/>Public sources only]
    E --> S[active-safe<br/>Scoped resolve, probe, crawl]
    E --> N[scanner-safe<br/>Approved discovery and scans]

    O --> G[Scope guard]
    S --> G
    N --> G
    G --> R[Recon and crawl outputs]
    R --> U[Normalize and re-check scope]
    U --> Q[Scanner hypotheses<br/>when profile permits]
    Q --> V[P4 controlled validation<br/>baseline, mutation, negative control]
    V --> T[P5 triage and severity]
    T --> W[P6 redacted report and retest]

    P --> M[Execution plan and manifest]
    O --> M[Manifest and scoped artifacts]
    S --> M
    N --> M
    W --> M
```

The P0–P6 phase model is: P0 authorization, P1 threat modeling, P2 surface
mapping, P3 test design, P4 controlled validation, P5 triage, and P6 reporting
or retesting. A scanner match never bypasses P4 and P5.

## Quick start

Clone the repository, then first verify the no-traffic planning path:

```bash
python3 scripts/jarvispentest_orchestrator.py example.com \
  --profile plan-only \
  --out ./jarvispentest-runs/example-plan
```

For an authorized engagement, create a workspace and record the real rules of
engagement. Do not change `authorization_status` to `confirmed` until the
authorization has been independently verified.

```bash
python3 scripts/new_engagement.py ./engagement \
  --title "Authorized assessment" \
  --target example.com \
  --owner "Program owner" \
  --operator "Researcher" \
  --scope-source "https://program.example/rules" \
  --testing-window "2026-08-01T00:00:00Z..2026-08-07T23:59:59Z" \
  --emergency-contact "security@example.com" \
  --disclosure-channel "security@example.com" \
  --rate-limit "25 req/s" \
  --allowed-asset example.com
```

Complete the generated `engagement.json`, validate P0, and only then advance the
gate:

```bash
python3 scripts/gate_check.py ./engagement --phase P0
python3 scripts/gate_check.py ./engagement --phase P0 --advance
```

`new_engagement.py` also accepts repeatable `--allowed-method`,
`--prohibited-method`, and `--test-identity` options, plus `--data-retention`.
Use `--authorization-status confirmed` only after independently verifying the
current program policy and scope.

After P0, select the least intrusive profile suitable for the approved scope:

| Profile | Target traffic | Purpose |
| --- | --- | --- |
| `plan-only` | None | Produce a plan without an engagement workspace. |
| `passive-osint` | No direct probing | Collect public-source information. |
| `active-safe` | Low-noise | Resolve, probe, and crawl approved assets. |
| `scanner-safe` | Authorized scanning | Run the permitted discovery and scanner stages. |

Example scanner run—use only when `automated_scanning` is explicitly allowed in
the engagement:

```bash
python3 scripts/jarvispentest_orchestrator.py example.com \
  --engagement ./engagement \
  --profile scanner-safe \
  --rate-http 20 \
  --rate-discovery 10 \
  --rate-scan 15 \
  --max-hosts 5
```

Run `python3 scripts/jarvispentest_orchestrator.py --help` for the full option set.
The complete operating procedure and phase references live in `SKILL.md` and
`references/`.

If the authorized program requires an attribution header for unauthenticated
requests, pass it explicitly; it is redacted from manifests and run
configuration:

```bash
python3 scripts/jarvispentest_orchestrator.py example.com \
  --engagement ./engagement \
  --profile active-safe \
  --research-header "X-HackerOne-Research: researcher"
```

## Outputs

Each run writes a private run directory containing:

- `run-config.json` — reproducibility fingerprint and command configuration
- `stages/` — resumable checkpoints
- `agents/` — scoped tool output
- `manifest.json` and `SUMMARY.md` — execution record and limitations

Raw assessment evidence belongs in the engagement's `evidence/raw/` directory.
Review and redact evidence before sharing it or committing it to a repository.

## Testing

The test suite is offline and uses fake binaries for scanner integration tests.

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/*.py
bash -n scripts/jarvispentest-tools.sh
```

## GitHub publishing checklist

Before publishing, verify that the repository does not include:

- engagement workspaces, run directories, raw evidence, credentials, cookies,
  tokens, or target-specific reports;
- local absolute paths that should be configurable for other users;
- private program rules, contact details, or assets outside public scope.

Add a `LICENSE` file before publishing if you want others to have explicit
permission to use, modify, or redistribute the code.

## Known limitations

- Optional tools are skipped when unavailable, so a completed run may have less
  coverage than a fully provisioned installation.

## Contributing

Contributions should keep the evidence and reproducibility discipline. Add or
update offline tests for any behavior change, particularly changes to deny-rule
enforcement, run resumption, evidence handling, and tool invocation.
