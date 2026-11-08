"""Tests for steps 4-5 (shocks.py, optimizer.py, goalplan.py). OWNER: Arshiya.
Checks the CLAUDE.md check values, edge accounts, and V4 (optimizer) / V11 (everyone = single).
Run from the repo root:  python tests/test_plan.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import engine.optimizer as optimizer
from engine.metrics import get_profile, all_customers
from engine.shocks import apply_shock, shock_many, runway_number
from engine.optimizer import optimize, optimize_many
from engine.goalplan import goal_plan


def twist(mult=1.0, bills=0.0, amount=0.0, months_sp=0.0, horizon=None):
    """Build a settings dict (only the fields steps 4-5 use)."""
    return {"income_multiplier": mult, "bills_increase_pct": bills, "one_off_amount": amount,
            "one_off_months_spending": months_sp, "horizon_months": horizon}


LAYOFF = twist(mult=0.55, horizon=6)                  # README twist 1
FURNACE = twist(months_sp=1)                          # README twist 2 (no goal given)
LAYOFF_BILLS = twist(mult=0.55, bills=15, horizon=6)  # README twist 3


def run_one(aid, settings, aim="max"):
    """Shock + optimizer for one account with the given aim."""
    optimizer.AIM = aim
    p = get_profile(aid)
    shocked = apply_shock(p, settings)
    opt = optimize(p, shocked, settings, None)
    optimizer.AIM = "max"                             # put the placeholder back
    return p, shocked, opt


def test_check_values_23595():
    """CLAUDE.md check values: shock 5.2, max cuts 1104/214/281 -> 10.1, cheapest ~411 -> 6.0."""
    p, shocked, opt = run_one(23595, LAYOFF_BILLS, "max")
    assert shocked["runway_shock"] == 5.2
    assert round(opt["cuts"]["cash"]) == 1104
    assert round(opt["cuts"]["bills"]) == 214
    assert round(opt["cuts"]["transfers"]) == 281
    assert opt["runway_opt"] == 10.1 and opt["reached"] is True

    _, _, cheap = run_one(23595, LAYOFF_BILLS, "cheapest")
    assert abs(cheap["total_cut"] - 411) < 1
    assert cheap["runway_opt"] == 6.0 and cheap["reached"] is True


def test_goal_plan_23595():
    """CLAUDE.md check value for the goal plan message."""
    assert goal_plan(get_profile(23595), None)["message"] == \
        "Save $28/month for 103 months to reach $20,238."


def test_impossible_goal():
    """V4: when max cuts can't reach the goal, report it and the extra savings needed."""
    settings = twist(mult=0.55, bills=15, horizon=24)
    p, shocked, opt = run_one(23595, settings, "max")
    assert opt["reached"] is False
    shortfall = shocked["spending"] - opt["total_cut"] - shocked["income"]
    expected = 24 * shortfall - shocked["buffer_left"]
    assert abs(opt["extra_savings_needed"] - expected) < 1


def test_no_goal_gives_none():
    """Furnace twist has no horizon -> reached is None, no extra savings."""
    _, shocked, opt = run_one(23595, FURNACE, "max")
    assert shocked["verdict_shock"] is None
    assert opt["reached"] is None and opt["extra_savings_needed"] == 0.0


def test_optimizer_never_worse_than_shock():
    """V4: cuts can only help: runway (c) >= runway (b), and cheapest never cuts more than max."""
    for aid in [23595, 55447, 49649, 21132, 32078]:
        _, shocked, opt_max = run_one(aid, LAYOFF_BILLS, "max")
        _, _, opt_cheap = run_one(aid, LAYOFF_BILLS, "cheapest")
        assert runway_number(opt_max["runway_opt"]) >= runway_number(shocked["runway_shock"])
        assert opt_cheap["total_cut"] <= opt_max["total_cut"] + 0.01


def test_edge_accounts():
    """V7: odd accounts don't crash; buffer <= 0 means runway 0; goal plan months never negative."""
    for aid in [49649, 21132, 22682, 32078, 36407]:
        for settings in (LAYOFF, FURNACE, LAYOFF_BILLS):
            p, shocked, opt = run_one(aid, settings)
            if shocked["buffer_left"] <= 0:
                assert shocked["runway_shock"] == 0.0 and opt["runway_opt"] == 0.0
        months = goal_plan(p, None)["months"]
        assert months is None or months >= 0


def test_everyone_equals_single():
    """V11 (for step 6): shock_many/optimize_many give the same runways as the single versions."""
    table = all_customers()
    sample = table.index[::10]                        # every 10th account keeps the test quick
    for settings in (LAYOFF, FURNACE, LAYOFF_BILLS):
        for aim in ("max", "cheapest"):
            optimizer.AIM = aim
            many_shock = shock_many(table, settings)
            many_opt = optimize_many(table, many_shock, settings)
            optimizer.AIM = "max"
            for aid in sample:
                _, shocked, opt = run_one(aid, settings, aim)
                assert runway_number(shocked["runway_shock"]) == many_shock.loc[aid, "runway_shock"]
                assert runway_number(opt["runway_opt"]) == many_opt.loc[aid, "runway_opt"]


if __name__ == "__main__":
    tests = [test_check_values_23595, test_goal_plan_23595, test_impossible_goal,
             test_no_goal_gives_none, test_optimizer_never_worse_than_shock,
             test_edge_accounts, test_everyone_equals_single]
    for t in tests:
        t()
        print("passed:", t.__name__)
    print("all plan tests passed")