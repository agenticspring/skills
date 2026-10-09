# Stripe API: SEPA Direct Debit PaymentMethod (without secret key)

> 2026-07-26 — technique for creating SEPA PaymentMethods using only the publishable key (pk_live_...).

## Why useful

Stripe's publishable key (`pk_live_*`) allows **tokenization** — creating PaymentMethods, SetupIntents, and certain read operations — without the secret key (`sk_live_*`). The secret key is needed for write operations like confirm, capture, refund, or deleting.

This means:
- ✅ Create SEPA Direct Debit PaymentMethod with IBAN → returns `pm_...` ID
- ❌ Confirm PaymentIntent/CheckoutSession with that PaymentMethod → needs secret key
- ❌ Retrieve Checkout Session details → needs secret key

## Creating a SEPA PaymentMethod

```python
import requests
PK = 'pk_live_...'
resp = requests.post(
    'https://api.stripe.com/v1/payment_methods',
    headers={'Authorization': f'Bearer {PK}', 'Content-Type': 'application/x-www-form-urlencoded'},
    data={
        'type': 'sepa_debit',
        'sepa_debit[iban]': 'DE87500105173319149382',
        'billing_details[name]': 'Max Mustermann',
        'billing_details[email]': 'email@example.com',
        'billing_details[address][country]': 'DE',
    },
    timeout=30
)
pm_id = resp.json().get('id')  # pm_1TxLrTBjIQrRQnuxC2pdvAdj
```

## Response includes
- `sepa_debit.bank_code`, `sepa_debit.last4`, `sepa_debit.fingerprint`
- `billing_details.name`, `billing_details.address.country`
- `livemode: true`

## What pk_live_* CANNOT do
| Operation | Result |
|---|---|
| Confirm PaymentIntent | 403 secret_key_required |
| Create PaymentIntent | 403 secret_key_required |
| Retrieve/confirm Checkout Session | 403/404 |
| Attach PM to session | needs merchant's secret key |
