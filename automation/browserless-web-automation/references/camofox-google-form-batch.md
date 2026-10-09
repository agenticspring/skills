# Camofox Google Form batch — tested run

## Context

HypzList (Hypz Club official GTD form) required: X handle, EVM wallet, reason,
follow checkbox (Yes/No), engagement radio (`Done ✅`), acknowledgment radio
(`I understand`). Direct `formResponse` POSTs with fresh hidden state
(`fbzx`, `fvv=1`, `pageHistory`, sentinels, cookies) consistently returned
`HTTP 400` with `data-validation-failed="true"`. Camofox UI submission worked
100/100.

## Setup (one-time)

```bash
npm install -g camofox-browser@2.4.7        # pinned version
camofox-browser                              # background server on 127.0.0.1:9377
curl -fsS <CAMOFOX_URL_REDACTED>/health       # expect "running":true
```

Stop the server after the run (`process` tool kill) and confirm
`ss -ltnp | grep :9377` shows nothing left.

## Per-entry flow

```text
camofox open <viewform URL>
camofox snapshot                    # get live [eN] refs
camofox fill '[e3]="handle" [e4]="wallet" [e5]="reason"'
camofox click <yes-ref> <done-ref> <understand-ref>
camofox click <submit-ref>
camofox snapshot                    # verify confirmation page
camofox close                       # REQUIRED before next open
```

## Ref-label matcher (HypzList form)

Regex over the snapshot dump:
`(textbox|checkbox|radio|button|link) "label" [eN]`

| label starts with | ref key |
|---|---|
| `Drop X handle` | handle |
| `Drop EVM wallet` | wallet |
| `Why HypzClub` | reason |
| `Yes` (checkbox role) | yes |
| `Done` | done |
| `I understand` | understand |
| `Prześlij` (button role) | submit |

Never hardcode refs — they change between snapshots.

## Confirmation markers

Recorded (success):

```text
Twoja odpowiedź została zapisana.
Your response has been recorded.
```

Failures/uncertain:

```text
data-validation-failed="true"
Nie udało się ...
There was a problem ...
```

Only `confirmed` counts. Stop on first non-confirmed; inspect partial
`results.json` before retrying.

## Pitfalls

1. **Max tabs:** after ~8 opens Camofox returns
   `Error: Maximum tabs per session reached` and `camofox open` fails.
   Fix: `camofox close` before each open (ignore its error on first run).
2. **Long fill strings:** pass the fill argument as one quoted argument
   (Python subprocess list form) — a naive shell `&&` line breaks on quotes.
3. **Per-entry reason uniqueness:** generate a distinct reason string per set
   (99 unique) and load from `reasons.json` keyed by set; identical template
   strings across all entries is detectable.
4. **Resume from index:** `python3 camofox-google-form-batch.py START END`
   resumes after a failure; the results file records absolute indexes.
5. **Wallet mapping must be verified before running:** derive addresses from
   the mnemonic sets in file order and confirm the mapping addresses match
   (`set 2` address == first mapping entry, `set N` == last).
6. No retry loops on `failed_page`; a retry could create duplicate responses.

## Result of the tested run

- 100 mnemonic sets (50 existing + 50 generated), formatted as `Set 1..100`.
- 99 handles mapped to sets 2-100 (set 1 reserved for `springhermes`).
- 99/99 entries confirmed recorded via Camofox; no failures after the tab
  fix; server stopped afterward; results kept in project folder mode 600.
