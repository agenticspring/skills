# PnL Card Layout Coordinate Map (1536×864)

Used during the Compact/Minimal/Pro redesign. Approx text width = `len(s) * fontSize * 0.6`.
Bounds: x≤1536, y≤864. All templates share `cardW=1536, cardH=864`.

## Compact
- Panel: m=48, rounded rect, accent bar left (w14).
- Header: logo (64px) at (xL, m+34); symbol bold52 at hx; botName bold30 right-anchored at xR.
  - xL = m+56 = 104; xR = cardW-m-56 = 1432.
- PnL: triangle at (xL+26, m+210); text bold140 anchored (xL+70, m+210). "42.5%" -> ~420px wide, right=594.
- Stats grid: gx=xL, gy=m+320=368, colW=(cardW-2m-112)/2=664, rowH=130.
  - 6 items -> 3 rows. Last row y=368+2*130=628, value+44=672, +40h=712 < footer (cardH-m-30=786). OK.
  - col1 x=768, "1,000,000,000" bold40 ~312px -> right=1080 < 1432. OK.

## Minimal
- Center cx=768. Logo (90px) at (cx-45, 70) if present -> logoBottom=190 else 96.
- Symbol bold56 at (cx, logoBottom+30), centered.
- Arrow at (cx, logoBottom+90); PnL bold150 at (cx, arrowY+150), centered. "42.5%"~450px -> left543/right993. OK.
- Stats sy=pnlY+130, lines*52. With logo: last line y=560+104=664 < cardH-90=774. OK.

## Pro
- Header bar h=92, dark 0.45. Logo(60) at (40,16); symbol bold42 at hx; botName+when right at cardW-40.
- Content: m=92, top=m+50=142. PnL left: triangle (px+24, top+30) px=60; text bold130 at (px+72, top+30). right=522 < splitX=640. OK.
- Split line at x=640.
- Right grid: gx=690, gy=top+20=162, colW=(cardW-gx-60)/2=393, rowH=110.
  - 7 items -> 4 rows. Last row y=162+3*110=492, value+42=534, +38h=572 < cardH-70=794. OK.
  - col1 x=1083, "1,000,000,000" bold38~312 -> right=1395 < 1536. OK.

## Verified-clean themes
default / neon / gold / ice / hacker / white -- all use `theme.*` colors, no hardcoded green/red.
White theme: PnL Positive {34,197,94}, Negative {239,68,68}, Text pure white.
