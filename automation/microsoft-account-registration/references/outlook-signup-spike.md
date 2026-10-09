# Outlook signup spike notes (2026-07-25)

## Working path (Webshare)
Proxy class: Webshare (`<REDACTED>` worked for form path).

Stages observed:
1. Email (`input[type=email]`) → Next enabled after full `*@outlook.com`
2. Password page copy: “Create your password”
3. Birth: “Add some details” — Country/Region, Month, Day, Year
   - `#countryDropdownId` combobox (often prefilled United States)
   - `#BirthMonthDropdown`, `#BirthDayDropdown`
   - `input[name=BirthYear]` number
4. Name: “Add your name” — `firstNameInput` / `lastNameInput`
5. Human: “Let's prove you're human” / “Press and hold the button.”

## HUMAN / PerimeterX
- Outer page still `signup.live.com`
- Nested: `iframe.hsprotect.net/index.html?app_id=PXzC5j78di&session_id=…`
- Also DFP frames: `fpt.live.com`, `df.cfp.microsoft.com`
- Hold UI in nested blank/hsprotect child:
  - `aria-label`: `Press & Hold Human Challenge`
  - text: `Press and hold`
  - `#px-captcha` container (~360×42)
- ServerData also exposes:
  - `sHumanAppId = PXzC5j78di`
  - `urlArkoseEnforcement` / `sArkoseEnforcementPid = B7D8911C-5CC8-A9A3-35B0-554ACEE604DA`
  - Arkose was **not** the iframe that appeared after name in successful Webshare runs

## Failures
| Symptom | Cause |
|---|---|
| “We ran into a problem” after email | DC/risk IP |
| Next disabled | incomplete/invalid email field state |
| CreateAccount API `1347` | missing risk/HIP/human tokens |
| Capsolver FunCaptcha 400 / useless | wrong gate (HUMAN not Arkose) |
| Mouse hold on outer page only | wrong target (not nested hold button) |

## Browserless crumbs
- Parse `ServerData={…};` from signup HTML
- Refresh canary via `EvaluateExperimentAssignments` before `CheckAvailableSigninNames`
- `apiCanary` header required on XHR APIs

## Not finished
- Reliable pass of HUMAN hold (in-frame long-press or solver)
- Post-human phone rate
- Credential vault format beyond `/root/outlook_accounts.txt` idea
