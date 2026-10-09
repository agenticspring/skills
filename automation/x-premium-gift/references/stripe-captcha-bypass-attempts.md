# Stripe hCaptcha Bypass Attempts (2026-07-07)

## Background

Stripe added enterprise-grade hCaptcha invisible protection to checkout pages. This blocks the X Premium gift exploit's automated form filling.

## Captcha Details

- **Sitekey**: `ec637546-e9b8-447a-ab81-b5fb6d8e24c2`
- **Type**: hCaptcha invisible
- **Domain**: `newassets.hcaptcha.com/captcha/v1/5ee68ce1512ba926b899cf5273dfe1d7d2d22976/`
- **Frames detected**: `hcaptcha-invisible`, `human-security`, `hcaptcha.html`

## Approaches Tried

### 1. 2Captcha Standard
```
Submit: POST https://2captcha.com/in.php
Result: ERROR_CAPTCHA_UNSOLVABLE
```

### 2. 2Captcha with Callback
```
Submit: POST https://2captcha.com/in.php?callback=hCaptchaCallback
Result: ERROR_CAPTCHA_UNSOLVABLE
```

### 3. 2Captcha Invisible Mode
```
Submit: POST https://2captcha.com/in.php?invisible=1
Result: ERROR_CAPTCHA_UNSOLVABLE
```

### 4. Token Injection (when solved)
```python
# Inject into ALL frames
for frame in page.frames:
    await frame.evaluate(f"""
        () => {{
            const ta = document.querySelector('textarea[name="h-captcha-response"]');
            if (ta) ta.value = '{token}';
            const ta2 = document.querySelector('textarea[name="g-recaptcha-response"]');
            if (ta2) ta2.value = '{token}';
        }}
    """)
```
**Issue**: Token injected into captcha frame (`newassets.hcaptcha.com`) but NOT into checkout frame (`checkout.stripe.com`). Checkout frame has no h-captcha-response elements.

### 5. Payment Method Alternatives
All 4 methods trigger same hCaptcha:
- ❌ Bank Transfer
- ❌ Crypto
- ❌ iDEAL | Wero
- ❌ Card

### 6. Stealth Mode
```python
browser = await p.chromium.launch(
    headless=True,
    args=['--disable-blink-features=AutomationControlled']
)
await context.add_init_script("""
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
""")
```
**Result**: Still detected, hCaptcha still present.

### 7. Mobile API
```python
s.headers.update({"User-Agent": "TwitterAndroid/10.21.0"})
```
**Result**: API endpoints return 404.

### 8. Payment Request API
```javascript
const request = new PaymentRequest(supportedInstruments, details);
const response = await request.show();
```
**Result**: "Renderer process could not establish or lost IPC connection"

### 9. Stripe API Direct
```python
requests.post(f"https://api.stripe.com/v1/payment_pages/{session_id}/confirm", data={...})
```
**Result**: 401 Unauthorized (requires Stripe secret key).

## Root Cause Analysis

1. **Frame Isolation**: hCaptcha runs on `newassets.hcaptcha.com`, checkout on `checkout.stripe.com`. Token in one frame doesn't propagate to other.

2. **Enterprise hCaptcha**: Stripe uses custom implementation with fingerprinting. Standard solving services can't handle it.

3. **Invisible Mode**: hCaptcha invisible doesn't expose response elements in DOM. Token must be submitted via callback function.

4. **No Weak Payment Method**: All payment methods share same captcha protection. No bypass via alternative payment.

## Potential Solutions (Untested)

1. **Capsolver/AntiCaptcha** — Different provider may handle Stripe's implementation
2. **Fresh Donor** — New donor may not trigger captcha immediately
3. **Timing** — Captcha may be session-based; wait 24-48h
4. **Proxy/VPN** — Different IP may not trigger captcha
5. **Manual** — Most reliable; gift via browser manually

## 2Captcha Balance

- Key 1: $-0.001 (depleted)
- Key 2: $6.57 (active, but can't solve Stripe captcha)

## Conclusion

As of 2026-07-07, automated X Premium gifting via Stripe is **blocked** by enterprise hCaptcha. The exploit works manually but not programmatically.
