# DER Decoding + RSA PKCS1 v1.5 (Pure Python)

## Decode SubjectPublicKeyInfo

```python
def _der_decode_pubkey(b64_pem):
    der = base64.b64decode(b64_pem)
    def read_tlv(data, pos):
        t = data[pos]; l = data[pos+1]; h = 2
        if l & 0x80:
            nl = l & 0x7f; l = int.from_bytes(data[pos+2:pos+2+nl], 'big'); h = 2 + nl
        return t, l, pos + h, pos + h + l
    
    # Outer SEQUENCE → value_start
    _, _, vs, _ = read_tlv(der, 0); p = vs
    # AlgorithmIdentifier → skip
    _, _, _, p = read_tlv(der, p)
    # BIT STRING → skip to payload (+1 for unused_bits)
    _, _, vs, _ = read_tlv(der, p)
    # RSAPublicKey SEQUENCE
    _, _, rp, _ = read_tlv(der, vs + 1)
    # INTEGER n
    _, _, ns, ne = read_tlv(der, rp); n = int.from_bytes(der[ns:ne], 'big')
    # INTEGER e
    _, _, es, ee = read_tlv(der, ne); e = int.from_bytes(der[es:ee], 'big')
    return n, e
```

## RSA PKCS1 v1.5 Encrypt

```python
def rsa_encrypt(password, n, e):
    pwd = password.encode()
    k = 128  # 1024-bit key
    ps = bytes(random.randint(1, 255) for _ in range(k - 3 - len(pwd)))
    eb = b"\x00\x02" + ps + b"\x00" + pwd
    c = pow(int.from_bytes(eb, "big"), e, n)
    return base64.b64encode(c.to_bytes(k, "big")).decode()
```

## Notes

- `JSEncrypt` library produces random padding each call → different base64 each time, which is correct
- Python `pycryptodome.Crypto.Cipher.PKCS1_v1_5` does the same thing
- The `00 02` prefix is the PKCS1 v1.5 block type 2 encryption format
- Key is always 1024-bit for Webnovel → k=128 bytes

## Pubkey Source

Webnovel pubkey is set at runtime from `login_v6.js`:
```javascript
LoginV1.config.pubkey = '-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----';
```

Extract with regex: `r"pubkey\s*=\s*'([^']+)'"` and replace `\n` with actual newlines.
