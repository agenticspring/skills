# X signup reverse notes (2026-07-20)

Session: CLI scaffold `/root/x-autoreg`, email `<REDACTED>`, skip phone, shared ProxyScrape pool, captcha via existing keys.

## Working requests

### Guest activate
```
POST https://api.twitter.com/1.1/guest/activate.json
Authorization: Bearer AAAA...ANRILg... (public web bearer)
x-client-transaction-id: <generated>
→ {"guest_token":"..."}
```

### Begin signup
```
POST https://api.twitter.com/1.1/onboarding/task.json?flow_name=signup
json: {
  "input_flow_data": {
    "flow_context": {
      "debug_overrides": {},
      "start_location": {"location": "splash_screen"}
    }
  },
  "subtask_versions": { ... full map ... }
}
→ flow_token + subtasks graph
```

Observed subtask IDs (graph includes many; not all shown at once in UI):
- `SignupSSOSubtask`, `SignupGoogleSSOSubtask`, `SignupAppleSSOSubtask`
- `Signup`
- `SignupSettingsListEmailNonEU` / `SignupSettingsListPhoneNonEU`
- `SignupReview`
- `ArkoseEmail` / `ArkosePhone`
- `EmailVerification` / `PhoneVerification` / dialogs

### Signup subtask schema (email path)
From begin payload `sign_up`:
- `email_next_link` → next `ArkoseEmail`
- `next_link` → next `ArkosePhone` (phone default)
- `js_instrumentation.url` = `https://twitter.com/i/js_inst?native=true`
- `allowed_identifiers`: `phone_then_email`
- `birthday_type`: `none` (still send birthday in practice)

### js_instrumentation capture
1. GET `https://twitter.com/i/js_inst?native=true&native_js=true`
2. Script body defines outer function; inner returns `{rf: {...}, s: "..."}`
3. Ends with `window.location = "/?result=" + JSON.stringify(inner())`
4. Playwright evaluate: rewrite location assignment to `window.__JS_INST_RESULT = ...`
5. Submit `js_instrumentation.response` as **stringified** JSON of that object (~640–650 chars)

### x-client-transaction-id
```python
from bs4 import BeautifulSoup
from x_client_transaction import ClientTransaction
from x_client_transaction.utils import get_ondemand_file_url

home = session.get("https://x.com")
soup = BeautifulSoup(home.text, "html.parser")
ondemand = session.get(get_ondemand_file_url(response=soup))
ct = ClientTransaction(home_page_response=soup, ondemand_file_response=ondemand.text)
txid = ct.generate_transaction_id(method="POST", path="/1.1/onboarding/task.json")
```

Browser also sends this on guest activate.

## Failed Signup submit

All tested variants returned:
```json
{"errors":[{"code":366,"message":"Missing data. g;..."}]}
```

Tried:
- email_next_link + birthday + js_resp string
- multi-subtask: Signup + SignupSettingsListEmailNonEU + SignupReview (modern keys)
- multi-subtask with legacy EU settings keys (`allow_emails_about_activity`, `find_by_email`, `personalize_ads`)
- phone_only / phone+email
- api.twitter.com / api.x.com / twitter.com/i/api / x.com/i/api
- with transaction-id + without

Historical gist payload shape (pre-Arkose era) for reference:
```json
{
  "flow_token": "...",
  "subtask_inputs": [
    {"subtask_id":"Signup","sign_up":{
      "js_instrumentation":{"response":"<js>"},
      "link":"email_next_link",
      "name":"...","email":"...",
      "birthday":{"day":15,"month":8,"year":1996}
    }},
    {"subtask_id":"SignupSettingsListEmail","settings_list":{
      "setting_responses":[
        {"key":"allow_emails_about_activity","response_data":{"boolean_data":{"result":false}}},
        {"key":"find_by_email","response_data":{"boolean_data":{"result":false}}},
        {"key":"personalize_ads","response_data":{"boolean_data":{"result":false}}}
      ],
      "link":"next_link"
    }},
    {"subtask_id":"SignupReview","sign_up_review":{"link":"signup_with_email_next_link"}},
    {"subtask_id":"EmailVerification","email_verification":{"code":"...","email":"...","link":"next_link"}}
  ]
}
```
Modern graph renames settings list to `SignupSettingsListEmailNonEU` and inserts **ArkoseEmail** before email verification.

## UI observations (Playwright + proxy)

Landing body options:
- Continue with phone
- Continue with Google / Apple
- Email or username + Continue (behaves like identifier entry → often phone signup branch)
- After phone click: `Enter your phone number` — **no Use email instead**

Android client bearer begin returned `RequireAppUpdateWithBackButtonSubtask` only.

## ArkoseEmail modal

```
web_modal.url = https://mobile.twitter.com/i/ocf_arkose_challenge
  ?webKey=arkose_challenge_signup_web_prod
  &mobileKey=arkose_challenge_signup_mobile_prod
  &data=<blob>
  &flowToken=...
```
next_link → `EmailVerification` after success.

## Product wiring already in repo

`/root/x-autoreg/register.py`:
- loads ranked captcha + IMAP from `.env`
- proxy file format `host:port:user:pass`
- skip phone via `SKIP_PHONE=1`
- reports `signup_missing_data` / `phone_required` honestly

## Next experiment checklist

- [ ] Real successful browser HAR of **email** create (not phone)
- [ ] Compare full request headers (esp. `x-xp-forwarded-for`, csrf/ct0, client events)
- [ ] Confirm whether client_event jot telemetry is required before Signup
- [ ] Extract live Arkose public key from challenge page (do not trust hardcoded)
- [ ] Residential / EU geo proxies for email create availability
