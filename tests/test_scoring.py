import pytest
from scripts.scoring import score_metric, verdict_of, dim_score, WEIGHTS

def test_score_pe_low_is_great():
    # PE < 15 → 92 (çok iyi, dir=down)
    assert score_metric(14, "pe") == 92

def test_score_pe_high_is_bad():
    # PE > 60 → 18 (çok kötü)
    assert score_metric(65, "pe") == 18

def test_score_roe_high_is_great():
    # ROE > 20 → 92 (çok iyi, dir=up)
    assert score_metric(25, "roe") == 92

def test_score_missing_value_returns_none():
    assert score_metric(None, "pe") is None

def test_verdict_strong_buy():
    assert verdict_of(80) == ("GÜÇLÜ AL", "strong_buy")

def test_verdict_sell():
    assert verdict_of(35) == ("SAT", "sell")

def test_dim_score_averages_valid_scores():
    metrics = {"pe": 92, "pb": 74, "ps": None}  # ps atlanır
    result = dim_score(metrics)
    assert result == round((92 + 74) / 2)

def test_weights_sum_to_one():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 0.001
