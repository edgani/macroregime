from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import json

import pytest

from warroom_v3.trading import (
    PaperTradeStatus,
    TradeDirection,
    build_structural_template,
    calculate_manual_trade_plan,
    close_paper_trade,
    list_paper_trades,
    open_paper_trade,
    paper_journal_summary,
    verify_paper_journal,
)


def mqa_state():
    return {
        "close": 100.0,
        "atr": 4.0,
        "fixed_lower": 96.0,
        "fixed_upper": 104.0,
        "conformal_lower": 95.0,
        "conformal_upper": 105.0,
    }


def test_structural_template_requires_operator_direction():
    long = build_structural_template(
        asset="BTCUSDT", timeframe="1h", direction=TradeDirection.LONG,
        source_snapshot_hash="a" * 64, mqa_state=mqa_state(),
    )
    assert long.invalidation_price < long.entry_zone[0]
    assert all(t > long.entry_zone[1] for t in long.targets)
    assert long.claim_ceiling == "OPERATOR_PLANNING_ONLY"

    short = build_structural_template(
        asset="BTCUSDT", timeframe="1h", direction=TradeDirection.SHORT,
        source_snapshot_hash="a" * 64, mqa_state=mqa_state(),
    )
    assert short.invalidation_price > short.entry_zone[1]
    assert all(t < short.entry_zone[0] for t in short.targets)


def test_risk_sizing_respects_cash_budget_and_leverage_cap():
    plan = calculate_manual_trade_plan(
        asset="BTCUSDT", timeframe="1h", direction=TradeDirection.LONG,
        source_snapshot_hash="b" * 64, entry_zone=(99.5, 100.5), invalidation_price=96.0,
        targets=(104.0, 108.0), account_equity=10_000, risk_budget_pct=0.5,
        estimated_roundtrip_cost_bps=12, max_leverage=1.0,
        created_at=datetime(2026, 7, 13, tzinfo=timezone.utc),
    )
    assert plan.estimated_loss_at_invalidation <= 50.0001
    assert plan.notional <= 10_000.0001
    assert plan.mode == "DISCRETIONARY_PAPER_ONLY"
    assert plan.reward_r_multiples[1] > plan.reward_r_multiples[0]


def test_invalid_geometry_is_rejected():
    with pytest.raises(ValueError):
        calculate_manual_trade_plan(
            asset="BTCUSDT", timeframe="1h", direction=TradeDirection.LONG,
            source_snapshot_hash="b" * 64, entry_zone=(99.5, 100.5), invalidation_price=101.0,
            targets=(104.0,), account_equity=10_000, risk_budget_pct=0.5,
        )


def test_append_only_paper_journal_open_and_close(tmp_path: Path):
    plan = calculate_manual_trade_plan(
        asset="ETHUSDT", timeframe="4h", direction=TradeDirection.SHORT,
        source_snapshot_hash="c" * 64, entry_zone=(1995.0, 2005.0), invalidation_price=2050.0,
        targets=(1900.0, 1800.0), account_equity=20_000, risk_budget_pct=0.5,
        created_at=datetime(2026, 7, 13, tzinfo=timezone.utc),
    )
    event = open_paper_trade(tmp_path, plan=plan, opened_at=datetime(2026, 7, 13, 1, tzinfo=timezone.utc))
    trades = list_paper_trades(tmp_path)
    assert len(trades) == 1
    assert trades[0].status == PaperTradeStatus.OPEN
    close_paper_trade(
        tmp_path, trade_id=event["trade_id"], exit_price=1900.0, reason="TARGET",
        closed_at=datetime(2026, 7, 14, tzinfo=timezone.utc),
    )
    trades = list_paper_trades(tmp_path)
    assert trades[0].status == PaperTradeStatus.CLOSED
    assert trades[0].realized_pnl > 0
    assert paper_journal_summary(tmp_path)["closed"] == 1
    assert not verify_paper_journal(tmp_path)


def test_paper_journal_tamper_is_detected(tmp_path: Path):
    plan = calculate_manual_trade_plan(
        asset="BTCUSDT", timeframe="15m", direction=TradeDirection.LONG,
        source_snapshot_hash="d" * 64, entry_zone=(99.0, 100.0), invalidation_price=95.0,
        targets=(105.0,), account_equity=10_000, risk_budget_pct=0.5,
        created_at=datetime(2026, 7, 13, tzinfo=timezone.utc),
    )
    open_paper_trade(tmp_path, plan=plan, opened_at=datetime(2026, 7, 13, 1, tzinfo=timezone.utc))
    journal = tmp_path / "runtime/trading/paper_events.jsonl"
    row = json.loads(journal.read_text().strip())
    row["recorded_at"] = "2099-01-01T00:00:00+00:00"
    journal.write_text(json.dumps(row) + "\n")
    assert verify_paper_journal(tmp_path)


def test_open_paper_trade_is_idempotent_for_same_trade_identity(tmp_path: Path):
    plan = calculate_manual_trade_plan(
        asset="BTCUSDT", timeframe="1h", direction=TradeDirection.LONG,
        source_snapshot_hash="e" * 64, entry_zone=(99.5, 100.5), invalidation_price=96.0,
        targets=(104.0,), account_equity=10_000, risk_budget_pct=0.5,
        created_at=datetime(2026, 7, 13, tzinfo=timezone.utc),
    )
    opened=datetime(2026,7,13,1,tzinfo=timezone.utc)
    first=open_paper_trade(tmp_path,plan=plan,opened_at=opened)
    second=open_paper_trade(tmp_path,plan=plan,opened_at=opened)
    assert first['entry_hash']==second['entry_hash']
    assert len(list_paper_trades(tmp_path))==1
