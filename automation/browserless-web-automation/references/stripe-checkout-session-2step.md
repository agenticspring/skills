# Stripe Checkout Session — API-based creation & confirmation

Generic patterns for creating Stripe Checkout Sessions and confirming payments via API (no browser Stripe.js needed).

## 2-step Checkout Session pattern

Many merchants (e.g. Claude/Anthropic) expose a backend API that creates a Stripe Checkout Session. The session is created **without** the billing address, then a second call sets the address.

### Step 1: Create session

```python
# POST /api/organizations/{org_id}/subscription/checkout_session
body = {
    'plan': 'plan_name',              # e.g. 'max_5x', 'pro', 'max_20x'
    'billingInterval': 'monthly',     # or 'yearly'
    'ipCountryHint': 'NL',            # hint; overridden by address step
    'referralCode': None,
    'referralSource': None,
    'returnUrl': 'https://merchant.com/settings/billing?action=subscribe&redirect_status=succeeded&plan={plan}',
    'paymentMethodTypes': ['card', 'sepa_debit'],  # include sepa_debit for SEPA
    'uiMode': 'custom',               # Stripe Elements custom mode
}
# Response includes:
#   sessionId: "cs_live_..."
#   clientSecret: "cs_live_...secret_..."
#   priceMinorUnitsBase: 9000   # price in cents
#   baseCurrency: "EUR"
```

### Step 2: Set address

```python
# POST /api/organizations/{org_id}/subscription/checkout_session/{sessionId}/address
{'country': 'DE'}  # ISO 3166-1 alpha-2
```

### Key findings (Claude.ai, 2026-07-26)

| Parameter | Value | Notes |
|-----------|-------|-------|
| API base | `claude.ai/api/organizations/{org_id}/subscription/checkout_session` | POST only |
| Plan names | `pro`, `max_5x`, `max_20x` | NOT `pro_monthly` — truncate suffix |
| Billing interval | `monthly`, `yearly` | `billingInterval` field |
| Country in body | ❌ `invalid_country` | Must use 2-step: create → address |
| Country after session | ✅ `POST /{sessionId}/address` with `{"country":"DE"}` | |
| `sepa_debit` in paymentMethodTypes | ✅ Accepted | SEPA PaymentMethod can be created separately |
| `uiMode: 'hosted'` | ❌ | Not permitted — only `'custom'` is accepted |
| Checkout URL direct access | ❌ | `checkout.stripe.com/c/pay/{id}` returns 404 for custom mode |

## SEPA PaymentMethod creation (publishable key)

Create a SEPA Direct Debit PaymentMethod using the merchant's publishable Stripe key:

```python
PK = 'pk_live_...'  # merchant's publishable key (from page source)
IBAN = 'DE89370400440532013000'

resp = requests.post(
    'https://api.stripe.com/v1/payment_methods',
    headers={
        'Authorization': f'Bearer {PK}',
        'Content-Type': 'application/x-www-form-urlencoded',
    },
    data={
        'type': 'sepa_debit',
        'sepa_debit[iban]': IBAN,
        'billing_details[name]': 'Max Mustermann',
        'billing_details[email]': 'user@example.com',
        'billing_details[address][country]': 'DE',
    })
# Returns pm_... on success
```

**Limitation:** Create works with publishable key, but **confirm/write operations** (confirm PaymentIntent, attach to customer, retrieve session) require the merchant's **Stripe secret key** — not available externally.

## Pricing API (before checkout)

Get pricing for a specific country:

```python
# POST /api/billing/{org_id}/individual_plan_pricing/v2
{'address': {'country': 'DE', 'postalCode': '10115'}}
# Returns per-plan prices in cents:
# {"product_prices_due_today": {"pro_monthly": {"basePrice": 1800, "taxAmount": 342, "totalPrice": 2142, ...}}}
```

Plan names in pricing response include `_monthly`/`_annual` suffix.
Checkout session expects shortened names (`pro` not `pro_monthly`).

## Pitfalls

- `paymentMethodTypes: ['card', 'sepa_debit']` may be accepted by API but Ignored by merchant's Stripe Elements configuration — SEPA only shows if merchant has it enabled in Stripe dashboard
- Session may expire — create fresh for each attempt
- `custom` mode sessions cannot be opened as standalone Stripe Checkout URLs — they require Stripe.js on the merchant's domain
- `invalid_country` often means the address must be set **after** session creation, not in the initial body
- `billingInterval: "Field required"` — always include this even if implicit from plan name
- `Invalid plan` — try shortened names (`max_5x` not `max_5x_monthly`)
