# Login 11401 + trust OTP recovery (2026-07-21)

## login_check must solve captcha
File: `/root/webnovel-autoreg/signup.py` → `login_check(..., solve_captcha=True)`
Solver: `/root/webnovel-autoreg/captcha_solver.py` (`LOGIN_PAGE_URL`, same sitekey as register)

## Trust OTP poll improvements
`poll_trust_code(..., exclude=set)`:
- folders include Spam
- multi-pattern extract; prefer 6-char mixed alnum
- newest-first
- exclude already-failed codes on `11319`

`checkTrust` loop: up to 3 OTP tries when code error.

## Observed sync fail mix (cold pool)
1. `11401 google code` — dominant without login captcha solve
2. `11318` + OTP / `11319` wrong code
3. login OK but mobile `no csrf` / CF
4. Warm session restore → usually OK <1s
