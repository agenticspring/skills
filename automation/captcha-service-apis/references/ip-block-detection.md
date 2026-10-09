# IP Block Detection Patterns

## 2captcha / rucaptcha

**Method 1: Balance check**
```bash
curl -s "https://2captcha.com/res.php?key=YOUR_KEY&action=getbalance"
# Positive float → OK, IP not blocked
# Negative float → OK but drained, IP not blocked
# ERROR_IP_NOT_ALLOWED → IP BLOCKED
# ERROR_IP_BLOCKED → IP BLOCKED
# ERROR_WRONG_ID_KEY → Key invalid (not IP issue)
```

**Method 2: reportbad test (more reliable)**
```bash
curl -s "https://2captcha.com/res.php?key=YOUR_KEY&action=reportbad&id=1"
# ERROR_WRONG_CAPTCHA_ID → IP OK (just fake ID)
# ERROR_IP_* → IP BLOCKED
```

## anti-captcha / capmonster / capsolver

All three use the same response format:
```json
{"errorId": 0, "balance": 1.23}          // OK
{"errorId": 1, "errorCode": "...", "errorDescription": "..."}  // Error
```

If `errorId > 0`, check `errorDescription` for IP block indicators:
- "IP address" or "blocked" → IP blocked
- "KEY_DOES_NOT_EXIST" → Key invalid (not IP issue)
- Timeout (no response) → Likely IP blocked or provider down

## Timeout vs Block

If curl returns exit code 28 (timeout), the provider may be blocking the server IP. Test with:
```bash
# Check if it's a network issue
curl -s --max-time 5 -o /dev/null -w "%{http_code}" https://api.anti-captcha.com/
# 200 or 4xx → network OK, API blocking your key/IP
# timeout → network issue or provider blocking at IP level
```

## Provider-Specific Notes

- **2captcha**: Most reliable from VPS/dedi IPs. Rarely blocks.
- **rucaptcha**: Same infrastructure as 2captcha. Same behavior.
- **anti-captcha**: Frequently blocks datacenter IPs. Works from residential.
- **capmonster**: Sometimes blocks datacenter IPs. Less aggressive than anti-captcha.
- **capsolver**: Similar to capmonster. May block from VPS IPs.
