# Virtuals ACP credit grant + console provisioning notes

Condensed session findings from live runs.

## Proven successful browserless path

A successful account/agent run yielded:
- domain email login via Privy OTP
- embedded EVM wallet creation
- session refresh after wallet creation
- ACP auth verify success
- agent creation success
- **console enable success**
- compute account:

```json
{"limit":10,"limitRemaining":10,"usage":0}
```

- compute API key issuance:

```text
acp-...
```

## Working backend indicator

The decisive backend step was:

```http
POST /agents/{id}/console
Authorization: Bearer <refreshed_privy_token>
Content-Type: application/json

{"runtime":"hermes","templateType":"personal_assistant"}
```

Observed success response pattern:

```json
{"message":"Successfully enabled console", ...}
```

After that, the following values appeared on compute account:

```json
{"limit":10,"limitRemaining":10,"usage":0}
```

## Why some runs showed $0

The following partial-success pattern happened repeatedly:
- UI showed Console ON / Hermes / Personal Assistance
- agent created successfully
- API key could still be created
- but backend compute stayed at:

```json
{"limit":0,"limitRemaining":0,"usage":0}
```

Associated backend hints included:
- `consoleAgentId = null`
- runtime not actually provisioned as Hermes
- Claw compute-account showing `openclaw`

Conclusion: frontend state was ahead of backend state.

## Auth details that mattered

### Privy side
After wallet creation, a session refresh was needed:

```http
POST /api/v1/sessions
{"refresh_token":"..."}
```

The refreshed response included:
- `token`
- `identity_token`
- wallet listed in `linked_accounts`

### ACP side
Wallet link verification succeeded with:

```http
POST /auth/verify
{"address":"0x...","token":"<refreshed_privy_token>","identityToken":"<refreshed_identity_token>"}
```

Observed success shape:

```json
{"message":"Successfully verified","data":{"walletAddress":"0x..."}}
```

For browserless create-agent requests, the **Authorization bearer that worked** was the refreshed Privy token.

## Rate-limit notes

Observed hot proxy/IP failure:

```json
{"statusCode":429,"message":"Rate limit exceeded"}
```

One proxy IP returned repeated 429s while another proxy IP immediately succeeded on the same payload shape.

Practical lesson:
- treat 429 as proxy/IP throttling
- rotate proxy and retry
- do not misdiagnose as payload/auth failure

## Live verification patterns

### API key validity
A successful API key could be verified against:

```http
GET https://compute.virtuals.io/v1/models
Authorization: Bearer acp-...
```

and a tiny chat completion call returned usage/cost.

### Balance re-check
After a small test completion, a live compute-account re-check showed balance decrement:

```json
{"limit":9.997886,"limitRemaining":9.997886,"usage":0.002114}
```

This confirmed the original `$10` grant was real and spendable.

## Recommended run summary fields

Store these for each account:
- email
- user wallet address
- agent wallet address
- agent id
- runtime
- proxy exit IP
- compute `limit`, `limitRemaining`, `usage`
- issued `acp-...` key
- whether console enable returned success

## Open question from this session

Some successful browser runs required post-create console forcing even though the UI already showed Hermes selected. Future reverse work should identify the exact create payload or secondary provisioning callback that would eliminate the need for the explicit post-create console call.
