# Session + /sync recovery notes

## Soft TTL
- `wn/session_store.py` DEFAULT_TTL_SEC = 24h (soft)
- Real validity = server accept of uid/ukey/_csrfToken via userInfoAjax
- Successful PS/sync use should refresh saved_at / rewrite cookies

## ensure_session strategy (tested then implemented)
A. cookies restore → use  
B. login once → open mobile immediately  
C. same ticket after ~1s pause  
D. rotate proxy + re-login on no-csrf / -51037  

Tested win: fail account `haruki.gupta206` recovered with A (login once → mobile + PS).  
Residual: some accounts stay on `-51037` after captcha token (proxy/network).

## /sync post-fail button
- Store failed full emails in in-memory `SYNC_FAIL_BATCHES[batch_id]`
- Keyboard: `relogin:{batch_id}` + dismiss
- Relogin job: invalidate cookies → `ensure_session(force=True)` → get_power_balance
- Still-fail list can spawn another batch button

## Common fail labels
| Error | Meaning |
|---|---|
| `-51037 Internet error` | transient after login/captcha |
| `no csrf` / `login/info failed` | mobile session exchange failed |
| `11401 google code` | risk captcha — must auto-solve same proxy |
| trust `11319` | wrong/stale OTP — try next code |

## Proxy replace checklist
1. backup old proxy.txt  
2. write new list  
3. rebind device_profiles sticky proxies (prefer 1:1 unique)  
4. clear sessions/  
5. restart single bot instance  
