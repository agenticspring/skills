# Deterministic Financial Card Reference

## Truthful semantics

Financial cards must communicate data quality, not just values:

```text
UNAVAILABLE  no trustworthy valuation
INDICATIVE   non-executable floor/index estimate
EXECUTABLE   current executable quote within stated bounds
PARTIAL      aggregate excludes one or more positions
```

If an indicative aggregate has missing positions, show both labels and an unvalued count. Do not silently collapse unknown positions to zero.

Use signs only for PnL. Show cost basis, gas, marketplace fees, and royalties as magnitudes. Keep payment-token dimensions separate unless an explicit FX source and timestamp exist.

## Numeric and text safety

- Format atomic values as decimal strings/BigInt; do not use floating point.
- Bound token symbols and labels.
- Escape markup before SVG/HTML interpolation.
- Truncate deterministically with an ellipsis.
- Test zero, negative PnL, very large atomic integers, long wallet labels, and hostile markup.

## Deterministic rendering gate

For each supported aspect ratio:

1. render one fixed fixture twice and compare bytes;
2. decode output and assert width/height/format;
3. assert EXIF/ICC metadata is absent when privacy requires it;
4. check attachment byte limits and restrictive local file mode if artifacts are written;
5. inspect visually for clipping, overlap, margin imbalance, label coverage, and footer collisions;
6. apply visual corrections before computing the approved golden hash;
7. add the golden under a test filename pattern that the actual test workspace discovers;
8. rerun the canonical full quality gate.

Semantic wording changes can alter geometry. Re-run visual QA after changing labels such as `INDICATIVE · PARTIAL` or adding unvalued counts.

## Hardened remote media ingress

Remote logos/artwork are optional. The renderer must remain valid without them.

For enabled media:

- HTTPS only; no URL credentials or non-standard ports;
- resolve and reject localhost/private/link-local/multicast/documentation addresses;
- validate every redirect target;
- pin the validated public IP for the connection while preserving origin TLS hostname to close DNS-rebinding windows;
- bound redirects and timeout;
- allowlist image MIME types;
- enforce header and streamed byte caps;
- enforce decoder pixel limits and disable animation;
- rotate/resize and re-encode to a known format without source metadata.

A unit fake can verify redirect and private-IP policy, but run one real public-image normalization smoke because HTTP client DNS lookup contracts can differ at runtime (for example single-address vs `all=true` callback shapes).

## Telegram update behavior

First render sends one photo and records its actual `message_id`. Refresh edits that exact media message. Never use a hardcoded message ID and do not create repeated cards unless editing is impossible and the fallback is explicit.
