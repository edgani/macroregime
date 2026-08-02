from eros.opportunity.ev import CostBreakdown, ExpectedValueInput, evaluate_expected_value


def test_net_ev_includes_losses_and_every_cost() -> None:
    inputs = ExpectedValueInput(probability_win=0.60, expected_win=0.20, expected_loss=-0.10,
        costs=CostBreakdown(transaction=0.005, funding=0.002, borrow=0.001, tax=0.004, fx=0.003, liquidity_impact=0.005),
        lower_confidence_adjustment=0.015, tail_risk_penalty=0.010, model_uncertainty_penalty=0.005)
    result = evaluate_expected_value(inputs)
    assert result.gross_ev == 0.08
    assert result.total_cost == 0.02
    assert result.net_ev == 0.06
    assert result.conservative_ev == 0.03
