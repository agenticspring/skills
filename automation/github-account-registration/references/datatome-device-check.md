# GitHub signup DataDome / device restriction

## Symptom
GitHub `/signup` probes return:

- `status=403`
- `authenticity_token_missing`
- `octocaptcha`/captcha iframe absent

Browser confirmation showed the real page was not signup form HTML but a DataDome restriction page.

## Browser-confirmed page shape
Visible text on the iframe page:

- `Access is temporarily restricted`
- `We detected unusual activity from your device or network.`
- `Automated (bot) activity on your network`
- `Use of developer or inspection tools`

Iframe URL observed:

```text
https://geo.captcha-delivery.com/interstitial/?initialCid=...&referer=https%3A%2F%2Fgithub.com%2Fsignup&...
```

## Interpretation
This is a **page-load block**, not a missing token / parser bug.

If `/signup` returns this page:
1. Do not keep hunting for `authenticity_token`
2. Do not blame `octocaptcha-token` parsing
3. Classify the attempt as `no_proxy_opens_signup` or `data-dome_blocked`
4. Move to a different proxy/IP/fingerprint source before retrying

## Useful checks
- `browser_snapshot` should show the blocked text, not a form
- `browser_console` should show the DataDome interstitial iframe URL
- CLI probes may still return `authenticity_token_missing` because the HTML is not the signup form

## Practical fallback
When all local pools return 403 on `/signup`, stop repeating captcha work and refresh the network pool first. The blocker is upstream of captcha solving.
