"""BTC Monday-candle study — live Binance data, refreshed on the desk cycle.

Questions answered (operator-specified, ICT Monday-range style):
  Q1: after the weekly path TAKES one side of the Monday range (Monday high or
      low), what is the probability of (a) reversal back through the Monday
      midline before week end vs (b) continuation (week closes beyond the
      swept side)?
  Q2 (variable a): same stats conditioned on the Monday candle being OUTSIDE
      the previous weekly range / previous monthly range.
  Q3: after one side is swept, probability the opposite side is also taken
      within the same week.

Data: Binance public klines (BTCUSDT, 1d, full history since 2017-08, no key).
Honest methodology notes:
  - Weeks are ISO Monday-start UTC (matches Binance weekly candles).
  - If Tue..Sun touches BOTH sides on the same day, order is unknowable from
    daily data -> counted as 'ambiguous', never guessed.
  - This is descriptive frequency statistics, not a trading signal; sample
    sizes are reported with every percentage.
Cache: runtime/v101_current/btc_monday.json, TTL 12h.
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parents[2]
CACHE = HERE / "runtime" / "v101_current" / "btc_monday.json"
TTL_HOURS = 12
UA = {"User-Agent": "curl/8.5.0 WarRoomOS/10.1"}
API = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=1000&startTime={ms}"


def _fetch_daily() -> list[dict]:
    start = int(datetime(2017, 8, 1, tzinfo=timezone.utc).timestamp() * 1000)
    out: list[dict] = []
    while True:
        req = urllib.request.Request(API.format(ms=start), headers=UA)
        rows = json.loads(urllib.request.urlopen(req, timeout=45).read().decode())
        if not rows:
            break
        for r in rows:
            d = datetime.fromtimestamp(r[0] / 1000, tz=timezone.utc).date()
            out.append({"date": d, "o": float(r[1]), "h": float(r[2]), "l": float(r[3]), "c": float(r[4])})
        start = rows[-1][0] + 86_400_000
        if len(rows) < 1000:
            break
        time.sleep(0.4)
    return out


def _study(days: list[dict]) -> dict[str, Any]:
    weeks: dict[date, list[dict]] = {}
    for row in days:
        monday = row["date"] - timedelta(days=row["date"].weekday())
        weeks.setdefault(monday, []).append(row)
    mondays = sorted(weeks)
    month_of = lambda d: (d.year, d.month)

    stats = {
        "weeks": 0,
        "sweep_high_first": 0, "sweep_low_first": 0, "no_sweep": 0, "ambiguous_same_day": 0,
        "after_high_sweep": {"n": 0, "reversal_through_mid": 0, "close_above_mon_high": 0, "opposite_side_taken": 0},
        "after_low_sweep": {"n": 0, "reversal_through_mid": 0, "close_below_mon_low": 0, "opposite_side_taken": 0},
        "outside_prev_week": {"weeks": 0, "engulf": 0, "sweeps": 0, "opposite_also_taken": 0},
        "outside_prev_month": {"weeks": 0, "engulf": 0, "sweeps": 0, "opposite_also_taken": 0},
    }

    prev_week_range: tuple[float, float] | None = None
    prev_month_ranges: dict[tuple[int, int], tuple[float, float]] = {}
    month_ranges: dict[tuple[int, int], list[float, float]] = {}

    for mon in mondays:
        candleweek = sorted(weeks[mon], key=lambda r: r["date"])
        monday_c = next((r for r in candleweek if r["date"] == mon), None)
        rest = [r for r in candleweek if r["date"] > mon]
        # track month ranges for variable-a (needs previous month complete)
        mk = month_of(mon)
        month_ranges.setdefault(mk, [float("-inf"), float("inf")])
        # update previous-month map after processing (below)
        if monday_c is None or len(rest) < 2:
            continue
        mh, ml, mo = monday_c["h"], monday_c["l"], monday_c["o"]
        mid = (mh + ml) / 2
        stats["weeks"] += 1

        first_side = None
        opposite_taken = False
        reversal = False
        close_beyond = False
        for r in rest:
            touched_h = r["h"] >= mh
            touched_l = r["l"] <= ml
            if first_side is None:
                if touched_h and touched_l:
                    first_side = "ambiguous"
                    break
                if touched_h:
                    first_side = "high"
                elif touched_l:
                    first_side = "low"
                continue
            if first_side == "high":
                if r["l"] <= ml:
                    opposite_taken = True
                if r["l"] <= mid:
                    reversal = True
            else:
                if r["h"] >= mh:
                    opposite_taken = True
                if r["h"] >= mid:
                    reversal = True
        week_close = candleweek[-1]["c"]
        if first_side == "high":
            close_beyond = week_close > mh
        elif first_side == "low":
            close_beyond = week_close < ml

        if first_side == "ambiguous":
            stats["ambiguous_same_day"] += 1
        elif first_side is None:
            stats["no_sweep"] += 1

        # variable a: Monday trades OUTSIDE the previous weekly / monthly range.
        # Two definitions kept honest: 'engulf' (both sides out — near impossible
        # for one day vs a 7-day range) and 'one_side' (high above prev high OR
        # low below prev low — the standard reading of "Monday di luar previous").
        pm = (mon.year, mon.month - 1) if mon.month > 1 else (mon.year - 1, 12)
        pmr = prev_month_ranges.get(pm)
        engulf_w = bool(prev_week_range and mh > prev_week_range[0] and ml < prev_week_range[1])
        engulf_m = bool(pmr and mh > pmr[0] and ml < pmr[1])
        outside_w = bool(prev_week_range and (mh > prev_week_range[0] or ml < prev_week_range[1]))
        outside_m = bool(pmr and (mh > pmr[0] or ml < pmr[1]))
        if outside_w:
            stats["outside_prev_week"]["weeks"] += 1
            stats["outside_prev_week"]["engulf"] += int(engulf_w)
        if outside_m:
            stats["outside_prev_month"]["weeks"] += 1
            stats["outside_prev_month"]["engulf"] += int(engulf_m)

        if first_side in ("high", "low"):
            key = "after_high_sweep" if first_side == "high" else "after_low_sweep"
            stats["sweep_high_first" if first_side == "high" else "sweep_low_first"] += 1
            s = stats[key]
            s["n"] += 1
            s["reversal_through_mid"] += int(reversal)
            s["close_above_mon_high" if first_side == "high" else "close_below_mon_low"] += int(close_beyond)
            s["opposite_side_taken"] += int(opposite_taken)
            if outside_w:
                stats["outside_prev_week"]["sweeps"] += 1
                stats["outside_prev_week"]["opposite_also_taken"] += int(opposite_taken)
            if outside_m:
                stats["outside_prev_month"]["sweeps"] += 1
                stats["outside_prev_month"]["opposite_also_taken"] += int(opposite_taken)

        wk_h = max(r["h"] for r in candleweek)
        wk_l = min(r["l"] for r in candleweek)
        prev_week_range = (wk_h, wk_l)
        for r in candleweek:
            mk2 = month_of(r["date"])
            cur = month_ranges.setdefault(mk2, [float("-inf"), float("inf")])
            cur[0] = max(cur[0], r["h"])
            cur[1] = min(cur[1], r["l"])
        prev_month_ranges = {k: tuple(v) for k, v in month_ranges.items()}

    def pct(n: int, d: int) -> float | None:
        return round(100 * n / d, 1) if d else None

    w = stats["weeks"]
    ah, al = stats["after_high_sweep"], stats["after_low_sweep"]
    ow, om = stats["outside_prev_week"], stats["outside_prev_month"]
    return {
        "weeks_analyzed": w,
        "sweep_direction": {
            "high_first_pct": pct(stats["sweep_high_first"], w),
            "low_first_pct": pct(stats["sweep_low_first"], w),
            "no_sweep_pct": pct(stats["no_sweep"], w),
            "ambiguous_pct": pct(stats["ambiguous_same_day"], w),
        },
        "after_high_sweep": {"n": ah["n"],
                             "reversal_through_mid_pct": pct(ah["reversal_through_mid"], ah["n"]),
                             "continuation_close_beyond_pct": pct(ah["close_above_mon_high"], ah["n"]),
                             "opposite_side_also_taken_pct": pct(ah["opposite_side_taken"], ah["n"])},
        "after_low_sweep": {"n": al["n"],
                            "reversal_through_mid_pct": pct(al["reversal_through_mid"], al["n"]),
                            "continuation_close_beyond_pct": pct(al["close_below_mon_low"], al["n"]),
                            "opposite_side_also_taken_pct": pct(al["opposite_side_taken"], al["n"])},
        "outside_prev_week": {"n": ow["weeks"], "engulf_n": ow["engulf"], "with_sweep": ow["sweeps"],
                              "opposite_also_taken_pct": pct(ow["opposite_also_taken"], ow["sweeps"])},
        "outside_prev_month": {"n": om["weeks"], "engulf_n": om["engulf"], "with_sweep": om["sweeps"],
                               "opposite_also_taken_pct": pct(om["opposite_also_taken"], om["sweeps"])},
    }


def compute() -> dict[str, Any]:
    days = _fetch_daily()
    result = _study(days)
    result.update({
        "state": "CURRENT",
        "computed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "Binance public klines BTCUSDT 1d (full history, no key)",
        "first_day": days[0]["date"].isoformat() if days else None,
        "last_day": days[-1]["date"].isoformat() if days else None,
        "note": "Statistik frekuensi deskriptif, bukan sinyal trading. 'Ambiguous' = kedua sisi tersentuh di hari yang sama (urutan tak bisa diketahui dari data harian).",
    })
    return result


def current_state() -> dict[str, Any]:
    try:
        if CACHE.exists():
            payload = json.loads(CACHE.read_text(encoding="utf-8"))
            ts = payload.get("computed_at")
            if ts and (datetime.now(timezone.utc) - datetime.fromisoformat(ts)) < timedelta(hours=TTL_HOURS):
                return payload
    except Exception:
        pass
    try:
        payload = compute()
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return payload
    except Exception as exc:
        return {"state": "UNAVAILABLE", "reason": f"{type(exc).__name__}: {exc}"}


if __name__ == "__main__":
    print(json.dumps(current_state(), indent=1, default=str))
