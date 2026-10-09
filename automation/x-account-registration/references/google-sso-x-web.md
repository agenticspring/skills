# Google SSO on X web (session notes)

Date: 2026-07-26

## What we observed

- X web signup can route through Google SSO successfully.
- Google login path may show an Indonesian consent screen with buttons:
  - `Batal`
  - `Lanjutkan`
- After Google password submit, the popup can close and X can redirect back to onboarding.
- The redirect may land on X onboarding steps instead of a finished session.
- Common subsequent steps seen:
  - `signup_dob` (birthday / age confirmation)
  - `discoverability_gate` (phone-number discoverability)
- The `discoverability_gate` modal can be blocked by the cookie banner at the bottom.

## Practical fixes

1. Always accept/clear X cookie banner first.
2. On Google consent, use Indonesian labels too:
   - `Lanjutkan`
   - `Tidak sekarang`
3. After Google password submit, do not assume failure if the popup closes.
   - Inspect the X page URL and onboarding modal.
   - Check cookies before deciding the flow died.
4. For `discoverability_gate`, click `Tidak sekarang` to skip phone discoverability when the goal is just to finish signup.

## Useful signals

- `auth_token` / `ct0` cookies = strong success signal.
- X URL fragments that indicate progress:
  - `#/s/signup_dob/...`
  - `#/s/discoverability_gate/...`
- If the page is still on X onboarding after Google closes, the flow may still be alive.

## Pitfalls

- A Google popup closing is not always an error.
- Consent text is localized; hard-coding only English button labels misses the click.
- Cookie banners can overlap the lower action area and hide the intended button.
