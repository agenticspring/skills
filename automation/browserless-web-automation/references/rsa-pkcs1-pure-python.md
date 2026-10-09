# Pure-Python RSA PKCS1 v1.5 Encryption

## Why PKCS1 v1.5?

Many Chinese web apps (Webnovel, some game platforms) use JSEncrypt for password encryption. JSEncrypt's `encrypt()` method performs RSA PKCS1 v1.5 encryption and returns Base64. We must match this exactly.

## Block Format

```
EB = 0x00 || 0x02 || PS || 0x00 || M
```

- `EB` = encryption block (k bytes, k = key size in bytes)
- `0x00 0x02` = fixed block type 02
- `PS` = padding: k - 3 - len(M) bytes of non-zero random bytes (≥8)
- `0x00` = separator
- `M` = password bytes

Then: `ciphertext = EB^e mod n`

## Key Size

1024-bit key = 128 bytes. Max password = 128 - 3 - 8 = 117 bytes.

## Random Padding is Correct

Each encryption differs. This is a feature (semantic security), not a bug.

## DER Structure

```
SEQUENCE (SubjectPublicKeyInfo)
  SEQUENCE (AlgorithmIdentifier)
    OID 1.2.840.113549.1.1.1
    NULL
  BIT STRING
    SEQUENCE (RSAPublicKey)
      INTEGER n
      INTEGER e (usually 65537)
```

## Common Mistakes

| Mistake | Result |
|---------|--------|
| Hardcoded stale pubkey | Decrypts to garbage → password error |
| PS contains 0x00 bytes | Truncated decryption |
| Wrong byte order | Key length mismatch |
