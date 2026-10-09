# Playwright Patterns for Checkout Automation

## Cookie-Based Authentication

Set cookies on target domain (with leading dot for subdomain support):

```python
await context.add_cookies([
    {"name": "auth_token", "value": "...", "domain": ".site.com", "path": "/", "secure": True, "sameSite": "None"},
    {"name": "session_token", "value": "...", "domain": ".site.com", "path": "/", "secure": True, "sameSite": "None"},
])
```

## Handling Cookie Consent Overlay

Many sites show cookie consent banners that block clicks:

```python
await page.goto("https://site.com", timeout=15000, wait_until="domcontentloaded")
await asyncio.sleep(2)
try:
    await page.click("button:has-text('Accept all cookies')", timeout=3000)
except:
    pass
await asyncio.sleep(1)
```

## Force Clicks for Intercepted Elements

When elements are behind overlays or masks:

```python
await page.click('button:has-text("Pay")', force=True, timeout=5000)
```

Or use JavaScript dispatch:

```python
await page.evaluate("""
    const btn = document.querySelector('[aria-label="Bank transfer"]');
    if (btn) btn.click();
""")
```

## Form Filling

Use Playwright's `fill` method for reliable input:

```python
await page.fill('input[name="email"]', 'value')
await page.select_option('select', 'DE')  # Country dropdown
```

## Network Interception

Track API calls for debugging:

```python
api_calls = []
async def handle_response(response):
    if "stripe" in response.url or "checkout" in response.url:
        try:
            body = await response.text()
            api_calls.append({"url": response.url, "body": body[:500]})
        except:
            pass
page.on("response", handle_response)
```

## Common Issues

1. **Page redirects** — Cookies invalid or account limit hit
2. **Element click timeout** — Use `force=True` or JS dispatch
3. **Form fields not filling** — Use `page.fill()` not `page.evaluate()` for inputs
4. **Stripe iframe** — Checkout loads in iframe, selectors must target the right frame
