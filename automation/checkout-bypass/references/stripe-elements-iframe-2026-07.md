# Stripe Elements Iframe Interaction

## Overview
Many modern sites use Stripe Elements (embedded in iframes) rather than redirect-based checkout. Elements include AddressElement, PaymentElement, and LinkAuthenticationElement. These are cross-origin iframes from `js.stripe.com`.

## Finding Stripe Frames
```python
stripe_frames = [f for f in page.frames if 'stripe.com' in (f.url or '')]
addr_frame = next((f for f in page.frames if 'elements-inner-address' in (f.url or '') and 'autocomplete' not in (f.url or '')), None)
pay_frame = next((f for f in page.frames if 'elements-inner-payment' in (f.url or '')), None)
```

## Address Element

### Known Fields
- `select[name="country"]` — country ISO code (e.g. "DE", "FR", "NL")
- `input[name="name"]` — full name
- `input[name="addressLine1"]` — street address
- `input[name="addressLine2"]` — apartment/suite
- `input[name="postalCode"]` — zip/postal code
- `input[name="locality"]` — city

### Setting Country
```python
await addr_frame.locator('select[name="country"]').select_option('DE')
```
Changing country recalculates tax (VAT) and may affect available payment methods.

## API Intercept Pattern
For intercepting checkout/billing API calls BEFORE the page renders:

```python
async def route_checkout(route):
    if 'checkout_capabilities' in route.request.url:
        await route.fulfill(
            status=200,
            content_type='application/json',
            body=json.dumps({"checkout_flow": "cassia"})
        )
    else:
        await route.continue_()

await page.route('**/*checkout_capabilities**', route_checkout)
```

This technique works for any fetch/XHR call made during page load.

## Payment Element
The payment element shows available payment methods. Common observed states:
- Card only (Visa/MC/Amex/Discover) — merchant hasn't enabled other methods
- Card + some EU methods (iDEAL, SEPA, etc.) — merchant configured properly

SEPA specifically requires merchant to enable it in Stripe dashboard AND customer country to be a SEPA country (DE, FR, etc.). Even with country=DE, if merchant hasn't enabled SEPA, it won't appear.

## Script Injection for Non-routable Calls
For pages that load before route registration, inject mock via `page.evaluate`:
```python
await page.evaluate(MOCK_SCRIPT)  # Tampermonkey-style fetch/XHR override
```

## Known Issues
- Stripe Elements iframes are cross-origin and sandboxed — `evaluate()` calls fail with SecurityError
- Frame must be fully loaded before interaction — wait 3-5s after page load
- hCaptcha Enterprise can appear on Stripe checkout — stealth patches may remove captcha but also remove some payment methods
- After changing country in address, payment options update asynchronously (2-4s delay)
- Tax recalculation confirms country was applied correctly
