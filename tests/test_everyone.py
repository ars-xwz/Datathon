"""Tests for step 6 (R10, V11): the twist on everyone matches the single-customer numbers.
Run: python tests/test_everyone.py"""
import os, sys, random, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.twist import TWIST_SCHEMA
from engine.metrics import get_profile, all_customers
from engine.customer_types import classify, TYPES
from engine.shocks import apply_shock, runway_number
from engine.optimizer import optimize
from engine.everyone import everyone_table, run_on_everyone

README_TWISTS = {
    "job loss EI 55%, 6 months": dict(TWIST_SCHEMA, income_multiplier=0.55, horizon_months=6),
    "furnace = 1 month of spending": dict(TWIST_SCHEMA, one_off_months_spending=1),
    "job loss + bills +15%": dict(TWIST_SCHEMA, income_multiplier=0.55, bills_increase_pct=15),
}


def test_v11_shock_matches_every_account():
    """Official runway after the shock: everyone version == apply_shock() for ALL accounts, all 3 twists."""
    ids = list(all_customers().index)
    for name, s in README_TWISTS.items():
        t = everyone_table(s)
        bad = [a for a in ids if runway_number(apply_shock(get_profile(a), s)["runway_shock"]) != t.loc[a, "runway_shock"]]
        assert not bad, f"{name}: {len(bad)} mismatches, e.g. {bad[:5]}"


def test_v11_optimizer_matches_sample():
    """Optimizer runway: everyone version == optimize() for 150 random accounts per twist (all accounts is slow)."""
    random.seed(1)
    ids = random.sample(list(all_customers().index), 150) + [23595, 55447]
    for name, s in README_TWISTS.items():
        t = everyone_table(s)
        for a in ids:
            p = get_profile(a)
            single = runway_number(optimize(p, apply_shock(p, s), s, classify(a)[0])["runway_opt"])
            assert single == t.loc[a, "runway_opt"], f"{name}, account {a}: single {single} vs everyone {t.loc[a, 'runway_opt']}"


def test_contract_and_check_values():
    s = dict(README_TWISTS["job loss + bills +15%"])
    start = time.time()
    c = run_on_everyone(s, 23595)
    took = time.time() - start
    for k in ["horizon", "pct_under_shock", "pct_under_opt", "by_type", "rank_longer_pct", "rank_in_type_pct"]:
        assert k in c, f"missing key {k}"
    assert set(c["by_type"]) == set(TYPES) and all(len(v) == 2 for v in c["by_type"].values())
    assert c["n_customers"] == 4500 and sum(c["type_counts"].values()) == 4500
    assert c["horizon"] == 6
    assert abs(c["pct_under_shock"] - 38.7) <= 0.2, c["pct_under_shock"]       # prototype check value
    assert c["pct_under_opt"] < c["pct_under_shock"]
    assert abs(c["rank_longer_pct"] - 66.7) <= 0.2 and abs(c["rank_in_type_pct"] - 48.8) <= 0.2
    assert c["account_type"] == "Savings-first"
    assert took < 5, f"run_on_everyone took {took:.1f}s"
    print(f"  ({took:.2f}s) {c['pct_under_shock']}% -> {c['pct_under_opt']}% (EI-cap view {c['pct_under_capped']}%), by type {c['by_type']}")


def test_unknown_account_gives_no_rank():
    c = run_on_everyone(dict(README_TWISTS["job loss EI 55%, 6 months"]), 1)
    assert c["rank_longer_pct"] is None and c["pct_under_shock"] > 0


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for t in tests:
        t(); print("passed:", t.__name__)
    print(f"all {len(tests)} everyone tests passed")
