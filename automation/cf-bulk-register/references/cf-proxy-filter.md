# CF Proxy Filter — Validate proxies against Cloudflare signup

After scraping proxies from public lists, most are datacenter IPs that CF blocks.
This filter tests each proxy against the real CF bootstrap endpoint.

## cf_filter.py workflow

1. Collect live HTTP/HTTPS proxies from scraper output
2. Test each against `https://dash.cloudflare.com/api/v4/system/bootstrap`
3. **HTTP 200 + `"success":true`** = CF-clean ✅
4. **HTTP 403** = blocked by CF WAF ❌
5. **HTTP 000** = proxy dead ❌

## Real-world results

From 2,615 live proxies (scraped from 70+ sources):
- Only ~0.1-0.3% pass CF bootstrap (typically Zscaler/CDN edge IPs)
- Even those that pass bootstrap still get `code 1111` (unable to sign up) on `/user/create`
- Free proxy lists are ~99.9% datacenter — CF blocks all for signup

## Conclusion

Only **residential/ISP proxies** work for CF account farming. Public free proxy lists
are insufficient. See `references/proxy-requirements.md` for provider recommendations.

## Code pattern

```python
async def test_proxy(proxy):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(CHECK_URL, proxy=f"http://{proxy}") as resp:
                if resp.status == 200:
                    text = await resp.text()
                    if '"success":true' in text:
                        return True  # CF-clean
    except: pass
    return False
```
