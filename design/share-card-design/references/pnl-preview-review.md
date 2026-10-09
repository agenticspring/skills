# PnL preview review lessons

## Divergent concept set

A useful five-option exploration can include:

1. **Split signal** — diagonal two-zone composition, token and values left, PnL right.
2. **Ticker tape** — market-terminal hierarchy with a horizontal data rail.
3. **Orbital** — PnL inside a radial indicator, supporting values in a side column.
4. **Receipt** — verified transaction/receipt metaphor with aligned label-value rows.
5. **Poster** — editorial typography with the return dominating the canvas.

These are different compositions, unlike five recolors of one layout.

## Geometry pitfalls observed

- A diagonal divider can collide with the leading `+` even when the number's center looks safely placed. Review the full text bounding box, not its anchor point.
- Moving only `+` or `%` breaks numeric cohesion. Move and align the entire PnL block, including its label.
- Oversized poster typography can hide a decimal or detach `%`, changing the meaning of the result.
- Subtitle baselines can visually overlap large display type despite apparently separate Y coordinates; inspect rendered glyph bounds.
- Contact-sheet QA can reveal defects invisible at full-size coordinate review, but final verification should also inspect the revised individual image.

## Approval states

Use explicit tracking:

```text
concept accepted
concept revision requested
revision rendered and QA-passed
final approval received
implemented
```

A user saying two concepts are good while requesting a revision to one means: preserve both, revise the named concept, and do not implement either until they explicitly approve implementation.

## Fair comparison fixture

Use identical values across all previews, for example:

```text
token: PONSHOOD
PnL: +142.7%
entry: 0.010 ETH
exit/current: 0.02427 ETH
network: Robinhood
wallet/time/brand: identical
```

The exact fixture can change, but it must remain constant within one comparison set.
