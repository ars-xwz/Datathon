"""Tests for steps 4-5 (shocks.py, optimizer.py, goalplan.py). OWNER: Arshiya.
Checks the CLAUDE.md check values, edge accounts, and V4 (optimizer) / V11 (everyone = single).
Run from the repo root:  python tests/test_plan.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import engine.optimizer as optimizer
from engine.metrics import get_profile, all_customers
from engine.customer_types import classify
from engine.shocks import (apply_shock, shock_many, runway_number, ei_cap_view, ei_cap_many,
                           DEFAULT_HORIZON)
from engine.optimizer import optimize, optimize_many, limits_for, STRONG, MODERATE, GENTLE
from engine.goalplan import goal_plan


def twist(mult=1.0, bills=0.0, amount=0.0, months_sp=0.0, horizon=None):
    """Build a settings dict (only the fields steps 4-5 use)."""
    return {"income_multiplier": mult, "bills_increase_pct": bills, "one_off_amount": amount,
            "one_off_months_spending": months_sp, "horizon_months": horizon}


LAYOFF = twist(mult=0.55, horizon=6)                  # README twist 1
FURNACE = twist(months_sp=1)                          # README twist 2 (no goal given)
LAYOFF_BILLS = twist(mult=0.55, bills=15, horizon=6)  # README twist 3


def run_one(aid, settings, aim="max"):
    """Shock + optimizer for one account (with its real customer type) and the given aim."""
    optimizer.AIM = aim
    p = get_profile(aid)
    ctype, _ = classify(aid)
    shocked = apply_shock(p, settings)
    opt = optimize(p, shocked, settings, ctype)
    optimizer.AIM = "max"                             # put the placeholder back
    return p, shocked, opt


def test_check_values_23595():
    """CLAUDE.md check values (23595 is Savings-first -> moderate limits):
    shock 5.2, max cuts 1104/214/281 -> 10.1, cheapest ~411 -> 6.0."""
    p, shocked, opt = run_one(23595, LAYOFF_BILLS, "max")
    assert shocked["runway_shock"] == 5.2
    assert round(opt["cuts"]["cash"]) == 1104
    assert round(opt["cuts"]["bills"]) == 214
    assert round(opt["cuts"]["transfers"]) == 281
    assert opt["runway_opt"] == 10.1 and opt["reached"] is True

    _, _, cheap = run_one(23595, LAYOFF_BILLS, "cheapest")
    assert abs(cheap["total_cut"] - 411) < 1
    assert cheap["runway_opt"] == 6.0 and cheap["reached"] is True


def test_limits_per_type():
    """D-1 proposal: Stabilize first strong, Savings-first/Trim moderate, Pension-protected gentle."""
    assert limits_for("Stabilize first") == STRONG
    assert limits_for("Savings-first") == MODERATE and limits_for("Trim") == MODERATE
    assert limits_for("Pension-protected") == GENTLE
    assert limits_for(None) == MODERATE               # unknown type -> moderate

    # A Stabilize-first account that's still short of money after max cuts gets the STRONG cuts
    table = all_customers()
    for aid in table.index[table["type"] == "Stabilize first"]:
        p, shocked, opt = run_one(aid, LAYOFF_BILLS, "max")
        if opt["reached"] is False and p["cash"] > 0:
            assert abs(opt["cuts"]["cash"] - round(p["cash"] * 0.50, 2)) < 0.01
            break


def test_goal_plan_23595():
    """Goal plan: over 24 months the length is shown in years (103 months -> about 8.6 years)."""
    assert goal_plan(get_profile(23595), None)["message"] == \
        "Save $28/month for about 8.6 years to reach $20,238."
    assert goal_plan(get_profile(23595), None)["months"] == 103   # months key stays a number


def test_impossible_goal():
    """V4: when max cuts can't reach the goal, report it and the extra savings needed."""
    settings = twist(mult=0.55, bills=15, horizon=24)
    p, shocked, opt = run_one(23595, settings, "max")
    assert opt["reached"] is False
    shortfall = shocked["spending"] - opt["total_cut"] - shocked["income"]
    expected = 24 * shortfall - shocked["buffer_left"]
    assert abs(opt["extra_savings_needed"] - expected) < 1


def test_no_goal_uses_default():
    """D-4 proposal: a twist with no goal (furnace) is judged against DEFAULT_HORIZON (6 months)."""
    assert DEFAULT_HORIZON == 6
    _, shocked, opt = run_one(23595, FURNACE, "max")
    expected = runway_number(shocked["runway_shock"]) >= 6
    assert shocked["verdict_shock"] is expected
    assert opt["reached"] in (True, False)


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
    """V11 (for step 6): shock_many/optimize_many give the same runways as the single versions,
    including the per-type limits."""
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
                assert abs(opt["total_cut"] - many_opt.loc[aid, "total_cut"]) < 0.01


def test_ei_cap_view():
    """R11: capped view is labelled, never changes the official runway, and matches the finding
    (working customers under 6 months on EI: about 42% -> 61%)."""
    p = get_profile(23595)                            # Savings-first: 55% of income is over the cap
    official = apply_shock(p, LAYOFF)
    capped = ei_cap_view(p, LAYOFF)
    assert apply_shock(p, LAYOFF) == official         # official number untouched
    assert capped["cap_changes_answer"] is True and "not the official" in capped["label"]
    assert runway_number(capped["runway_capped"]) < runway_number(official["runway_shock"])
    assert ei_cap_view(p, FURNACE)["cap_changes_answer"] is False   # no job loss -> no cap

    table = all_customers()
    working = table["type"] != "Pension-protected"
    shock_pct = (shock_many(table, LAYOFF)["runway_shock"][working] < 6).mean() * 100
    cap_pct = (ei_cap_many(table, LAYOFF)["runway_capped"][working] < 6).mean() * 100
    assert round(shock_pct) == 42 and round(cap_pct) == 61

    for aid in table.index[::50]:                     # everyone version = single version
        single = runway_number(ei_cap_view(get_profile(aid), LAYOFF)["runway_capped"])
        assert single == ei_cap_many(table, LAYOFF).loc[aid, "runway_capped"]


def test_type_advice():
    """PLAN.md 2.5: one personalized sentence per type (none for Trim), matching the facts."""
    table = all_customers()
    # 23595 is Savings-first and reaches the goal -> the EI-cap sentence
    _, _, opt = run_one(23595, LAYOFF_BILLS)
    assert opt["reached"] is True and "capped" in opt["type_advice"]
    # Savings-first that can't reach a long goal -> "build savings first" with the extra amount
    _, _, opt = run_one(23595, twist(mult=0.55, bills=15, horizon=24))
    assert opt["reached"] is False and "Build savings first" in opt["type_advice"]
    assert f"${opt['extra_savings_needed']:,.0f}" in opt["type_advice"]
    # one account of each other type
    for ctype, must_say in [("Stabilize first", "stop going below zero"),
                            ("Pension-protected", "pension"), ("Trim", None)]:
        aid = table.index[table["type"] == ctype][0]
        _, _, opt = run_one(aid, LAYOFF_BILLS)
        if must_say is None:
            assert opt["type_advice"] is None
        else:
            assert must_say in opt["type_advice"]
    # every account gets advice without crashing (sample)
    for aid in table.index[::25]:
        run_one(aid, LAYOFF_BILLS)


if __name__ == "__main__":
    tests = [test_check_values_23595, test_limits_per_type, test_goal_plan_23595,
             test_impossible_goal, test_no_goal_uses_default, test_optimizer_never_worse_than_shock,
             test_edge_accounts, test_everyone_equals_single, test_ei_cap_view, test_type_advice]
    for t in tests:
        t()
        print("passed:", t.__name__)
    print("all plan tests passed")