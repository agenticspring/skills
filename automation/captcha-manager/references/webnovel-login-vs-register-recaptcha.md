# Webnovel reCAPTCHA: login vs register

Same sitekey for both risk gates:
`6Leb2SYUAAAAAEemO0h4Wj_casf9j5HM6RfNg7bG`

| Path | Page URL | Endpoint after token | Common fail if wrong |
|------|----------|----------------------|----------------------|
| Register | `passport.webnovel.com/register.html?...` | `doregister` `nextAction=1` + `validateCode` | `11306` if proxyless vs proxied |
| Login | `passport.webnovel.com/emaillogin.html?...` | `checkcode` `nextAction=1` + `validateCode` | cold `/sync` `11401 google code` / no ticket |

## Rules
1. Always **proxy-bound** when account uses sticky proxy
2. Login captcha is **required for ticket** — not optional soft-success
3. Rank providers by live balance; inject into bot `.env` for `/create` and login/sync
4. Module: `/root/webnovel-autoreg/captcha_solver.py` (`REGISTER_PAGE_URL`, `LOGIN_PAGE_URL`)
