# War Room OS v2.9 — Decision-First Re-Audit

## Why v2.8 was wrong

The deployed screenshots exposed four separate design and logic defects.

### 1. Alpha Center was silently replaced by a tactical screener

`build_fast_desk()` emitted an empty `alpha` list. The browser filled that hole with the same
price setups used by market tabs. This changed Alpha Center from generational/asymmetric discovery
into a short-horizon NVDA/SPY/AMD watchlist.

**v2.9 fix:** the structural asymmetric-discovery engine now runs in the first-paint pipeline.
Tactical price context is attached only as a separate timing field.

### 2. The fallback setup engine could only emit longs

The old fallback could not construct an honest bearish watchlist. A bearish market could therefore
still show only long candidates.

**v2.9 fix:** two-sided markets now construct independent long and short price contexts. The UI then
applies the market gate. IHSG remains long-only and converts bearish contexts to `REDUCE / AVOID`
or `NO TRADE`.

### 3. Raw provider endpoints were drawn as decision nodes

Binance/Bybit errors and paid-provider entitlements covered the canvas, even when another venue or
domain remained usable. Endpoint health is infrastructure evidence, not the decision itself.

**v2.9 fix:** Institutional and Derivatives canvases show domain summaries. Raw endpoint states and
errors remain available in the Evidence Ledger for diagnosis.

### 4. Layout had too many nodes, edges and text fields

Fixed-width cards, long status values, radial validation layout and all-to-many edges caused visible
overlap.

**v2.9 fix:**

- separate title, subtitle, value and evidence badge rows;
- bounded card counts per canvas;
- bounded edge labels;
- domain aggregation instead of provider walls;
- staged/layered validation layout;
- full 16-workspace browser geometry test with zero node overlaps.

## Alpha Center: intended meaning

Alpha Center searches for:

```text
structural change
→ bottleneck / scarcity
→ direct value capture
→ expectation gap
→ room to run
→ independent proof
→ timing
→ validation / capital permission
```

Headroom buckets are scenario classes:

| Headroom class | Approximate total-return headroom | Base-rate framing |
|---|---:|---|
| 1.5–3x | +50% to +200% | higher |
| 3–10x | +200% to +900% | moderate |
| 10–50x | +900% to +4,900% | low |
| 50–500x | +4,900% to +49,900% | very low |
| 500x+ | +49,900%+ | lottery |

These are not price targets, probabilities or expected returns. A high tier is deliberately paired
with a lower base rate and a stricter proof burden.

## Market-tab decision contract

Every candidate must answer two different questions:

1. **Direction to watch:** long, short or neither.
2. **Permission now:** build, watch, reduce/avoid or no trade.

The canvas and Decision Rail now show explicit actions, trigger, stop, reference target and market
posture. A readiness score remains a descriptive ranking field and is never displayed as win
probability.

## Provider-error contract

- Individual endpoint failure does not make an entire domain `ERROR` when another usable source is
  live.
- Raw error and entitlement details remain in the ledger.
- Missing data is never replaced with synthetic production observations.
- Optional paid feeds can remain `NOT_ENTITLED`; the rest of War Room must continue operating.

## Validation performed

- 189 Python files compiled successfully.
- Dashboard JavaScript parsed successfully.
- Controlled first-paint fixture produced 79 structural Alpha candidates.
- Long and short setup construction both produced candidates.
- Bearish IHSG test produced `REDUCE / AVOID` and no `BUILD SHORT`.
- Bearish US test produced directional short watches.
- Chromium rendered all 16 workspaces with zero JavaScript page errors.
- Geometry audit found zero node-card overlaps across all 16 workspaces.
- Raw provider errors are absent from the Institutional/Derivatives canvases and retained in the
  ledgers.

Authenticated paid-provider responses cannot be certified without the deployment account's real
keys and entitlements. v2.9 changes how those failures are isolated and displayed; it does not
invent access.
