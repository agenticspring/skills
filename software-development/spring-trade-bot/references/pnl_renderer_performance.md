# PnL Renderer Performance and Multi-User Safety

Use this when optimizing a Go/fogleman-gg PNG card renderer or a Telegram live-preview studio.

## Measure first

Benchmark separately:

```text
preset background render
normalized custom-background render
legacy 4K custom-background render
Studio preview cache hit
```

Use `go test -bench ... -benchmem`, then CPU/allocation profiles. Typical hotspots are not fonts: pixel-by-pixel gradients, same-size `gg.DrawImage` resampling, custom 4K resize, and PNG filtering/compression.

## Proven architecture

1. **Pre-render immutable gradients** once at package startup into fixed-size RGBA images.
2. **Direct-copy same-size images** with stdlib `image/draw.Draw`; `gg.DrawImage` may invoke an expensive transform kernel even when source and destination dimensions match.
3. **Normalize custom backgrounds once** at upload: cover-fit + center-crop to the final canvas dimensions, then store a fast-encoded PNG. Keep a legacy fallback that normalizes old files once.
4. **Cache decoded normalized backgrounds** by `path + mtime`; bound the cache (for example 16 entries) and evict least-recently-used/oldest entries.
5. **Use `png.Encoder{CompressionLevel: png.BestSpeed}`** after benchmarking output size. Telegram card PNGs commonly remain small enough that CPU savings outweigh a modest byte increase.
6. **Cache font faces cautiously.** `opentype.Face` has mutable internal glyph/rasterizer state and is not safe for concurrent use. A concurrent race test is mandatory. Either create faces per render or serialize rendering when sharing cached faces.
7. **Add backpressure.** A bounded render semaphore prevents simultaneous high-memory renders. If cached faces are shared, capacity 1 is the correctness-safe default.
8. **Latest-selection-wins Studio UX.** Debounce rapid config taps (roughly 150–250 ms), cancel the previous pending update, and render/upload only the final config. Continue editing the same Telegram photo in place; never spawn completion messages.
9. **Bounded identical-preview cache.** Key by every visual option plus background identity/mtime; use a short TTL and bounded entries. Return copied bytes so callers cannot mutate cached backing arrays.

## Verification

```bash
gofmt -w <changed files>
go test -race -shuffle=on -count=1 ./...
go vet ./...
go build ./cmd/bot
```

Add lasting tests for:

- preset image reuse;
- background normalization dimensions;
- cache bounds and byte isolation;
- render limiter capacity;
- concurrent render race safety;
- positive/negative output validity.

Generate actual renderer PNGs and visually compare layouts after optimization. If visual tooling flags a seam or aliasing regression, inspect pixel values/geometry numerically before changing the design.

## Reference benchmark pattern

A successful optimization on a 1536×864 renderer improved:

```text
preset: ~340 ms → ~123 ms
normalized custom background: ~1.06 s / 120 MB → ~188 ms / ~8.7 MB
identical Studio preview cache hit: ~23 µs
```

Treat these as directional, not universal targets; hardware, templates, and PNG complexity vary.
