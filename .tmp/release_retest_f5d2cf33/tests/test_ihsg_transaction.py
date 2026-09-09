from __future__ import annotations
import math

from ihsg_transaction import (
    broker_concentration_metrics,
    daily_persistence,
    order_book_metrics,
    intraday_metrics,
    combine_transaction_layers,
    transaction_evidence_delta,
    eod_transaction_snapshot,
    intraday_transaction_snapshot,
)

rows = [
    {"code":"AA","buy_value":100,"sell_value":20,"buy_volume":10,"sell_volume":2,"buy_freq":5,"sell_freq":1,"buy_avg":10,"sell_avg":10},
    {"code":"BB","buy_value":50,"sell_value":10,"buy_volume":5,"sell_volume":1,"buy_freq":3,"sell_freq":1,"buy_avg":10,"sell_avg":10},
    {"code":"CC","buy_value":0,"sell_value":70,"buy_volume":0,"sell_volume":7,"buy_freq":0,"sell_freq":3,"buy_avg":0,"sell_avg":10},
    {"code":"DD","buy_value":0,"sell_value":50,"buy_volume":0,"sell_volume":5,"buy_freq":0,"sell_freq":2,"buy_avg":0,"sell_avg":10},
]

c = broker_concentration_metrics(rows)
assert math.isfinite(c["buyer_hhi"])
assert math.isfinite(c["seller_hhi"])
assert len(c["top_accumulators"]) == 2
assert abs(c["accumulator_cost"] - 10.0) < 1e-9

p = daily_persistence({"2026-08-24":rows, "2026-08-25":rows})
assert abs(p["buyer_persistence"] - 1.0) < 1e-9
assert abs(p["seller_persistence"] - 1.0) < 1e-9
assert abs(p["persistence_edge"]) < 1e-9

book = {
    "bid":[{"bid1price":100,"bid1lot":1000}],
    "offer":[{"offer1price":101,"offer1lot":500}],
}
ob = order_book_metrics(book)
assert 0.32 < ob["order_book_imbalance"] < 0.34
assert ob["spread_bps"] > 0

im = intraday_metrics({"close":100,"prev":100,"haka_value":40,"haki_value":60}, book)
assert im["absorption_side"] == "BUY-SIDE ABSORPTION"
assert im["aggressive_flow_imbalance"] < 0

combined = combine_transaction_layers(
    {
        "eod_status":"READY · EOD BROKER ATTRIBUTION",
        "concentration_edge":0.10,
        "persistence_edge":0.20,
        "foreign_flow_intensity":0.10,
        "crossing_transfer_risk":0.10,
        "distance_from_accumulator_cost":0.03,
    },
    {"intraday_status":"READY · LIVE MICROSTRUCTURE", **im},
)
assert combined["transaction_coverage"] == "HIGH"
assert math.isfinite(combined["transaction_score"])
assert combined["transaction_is_probability"] is False
ev, det, basis = transaction_evidence_delta(combined)
assert ev in (0,1) and det in (0,1)
assert ev + det <= 1

# Missing keys must fail closed: never fabricate a state upgrade.
e = eod_transaction_snapshot("BBCA.JK", "")
i = intraday_transaction_snapshot("BBCA.JK", "")
g = combine_transaction_layers(e, i)
assert g["transaction_state"] == "DATA GATED"
assert g["transaction_coverage"] == "LOW"
assert transaction_evidence_delta(g)[:2] == (0,0)

# Negotiated-market contamination can neutralize/discount conviction.
crossed = combine_transaction_layers(
    {
        "eod_status":"READY · EOD BROKER ATTRIBUTION",
        "concentration_edge":0.15,
        "persistence_edge":0.30,
        "foreign_flow_intensity":0.20,
        "crossing_transfer_risk":0.90,
        "distance_from_accumulator_cost":0.01,
    },
    {"intraday_status":"GATED"},
)
assert crossed["transaction_state"] == "TRANSFER / CROSSING DOMINATED"
assert transaction_evidence_delta(crossed)[:2] == (0,0)

print("TEST_IHSG_TRANSACTION_PASS")
