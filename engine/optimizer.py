"""R5: optimizer -> runway (c). OWNER: Arshiya. STATUS: done (placeholders D-1, D-2, D-3).

Levers: cash withdrawals, household bills, other transfers out ONLY.
Each lever can be cut 0%, 5%, 10% ... up to its limit. We try EVERY combination
(brute force) and pick the best one according to the aim:
  "max"      : longest runway (cut as much as allowed); ties -> fewest dollars
  "cheapest" : fewest dollars that still reach the goal; ties -> fewest levers touched
               (if nothing reaches the goal, fall back to "max")

Cut limits depend on the customer type (LIMITS_BY_TYPE), e.g. Stabilize-first customers,
who already go below zero, are allowed stronger cuts.

Two versions of the same math:
  optimize(p, shocked, settings, ctype)    one customer, used by the pipeline (step 5)
  optimize_many(table, shocked, settings)  every customer at once, for step 6 (everyone.py);
                                           uses the table's "type" column to pick each row's limits
optimize() just runs optimize_many() on a one-row table, so they can't disagree.
"""
from itertools import product

import numpy as np
import pandas as pd

from engine.shocks import runway_many, goal_months, NO_SHORTFALL

# The three levers (names match the columns in get_profile() / all_customers())
LEVERS = ["cash", "bills", "transfers"]

# PLACEHOLDER: decision D-1 (cut limits). Arshiya's proposal: limits per customer type; team to confirm.
GENTLE = {"cash": 0.20, "bills": 0.05, "transfers": 0.25}
MODERATE = {"cash": 0.30, "bills": 0.10, "transfers": 0.50}
STRONG = {"cash": 0.50, "bills": 0.20, "transfers": 1.00}
LIMITS_BY_TYPE = {
    "Stabilize first": STRONG,        # already going below zero -> bigger changes needed
    "Savings-first": MODERATE,
    "Trim": MODERATE,
    "Pension-protected": GENTLE,      # pension keeps paying -> lighter touch
}
LIMITS = MODERATE                     # used when the type is unknown (e.g. ctype=None)


def limits_for(ctype):
    """Cut limits for a customer type (falls back to LIMITS for an unknown type)."""
    return LIMITS_BY_TYPE.get(ctype, LIMITS)
# PLACEHOLDER: decision D-2 (aim) and D-3 (step, best, tie-break). Arshiya's proposal: "max"; team to confirm.
STEP = 0.05
AIM = "max"          # "max" or "cheapest"


def cut_levels(limit, step):
    """Cut fractions to try for one lever, e.g. 0.0, 0.05, ... 0.30 (always includes the limit)."""
    # work in whole percents so float rounding (0.1 + 0.2) can't skip a level
    limit_pct, step_pct = round(limit * 100), round(step * 100)
    return [pct / 100 for pct in list(range(0, limit_pct, step_pct)) + [limit_pct]]


def all_combinations(limits, step):
    """Every combination of cut fractions, e.g. (0, 0, 0), (0, 0, 0.05) ... (0.30, 0.10, 0.50)."""
    return list(product(*[cut_levels(limits[lever], step) for lever in LEVERS]))


def optimize_many(table, shocked, settings, aim=None, limits=None, step=None):
    """Best cuts for every row at once.
    table   : needs columns cash, bills, transfers (lever medians, $/month)
    shocked : needs columns income, spending, buffer_left (from shocks.shock_many)
    Returns a DataFrame (same index) with cut_cash, cut_bills, cut_transfers, total_cut,
    runway_opt (number; 'no shortfall' = 120.0), no_shortfall, reached, extra_savings_needed.
    limits: one dict for every row; leave it out to use each row's type (table["type"])."""
    # No limits given + the table has customer types -> run each type with its own limits
    if limits is None and "type" in table.columns:
        parts = [optimize_many(table[table["type"] == t], shocked[table["type"] == t],
                               settings, aim, limits_for(t), step)
                 for t in table["type"].unique()]
        return pd.concat(parts).reindex(table.index)      # back in the original order

    # read the placeholders NOW (not when the file loads), so changing AIM/LIMITS/STEP takes effect
    aim = AIM if aim is None else aim
    limits = LIMITS if limits is None else limits
    step = STEP if step is None else step
    horizon = goal_months(settings)       # twist's goal, or the default
    n = len(table)
    income = shocked["income"].to_numpy(float)
    spending = shocked["spending"].to_numpy(float)
    buffer_left = shocked["buffer_left"].to_numpy(float)
    lever_amounts = {lever: table[lever].to_numpy(float) for lever in LEVERS}

    # Best option found so far, one value per customer. Start with "no cuts".
    best = {lever: np.zeros(n) for lever in LEVERS}
    best_total = np.zeros(n)
    best_runway = runway_many(buffer_left, spending, income)
    best_levers = np.zeros(n)              # how many levers are cut (for the "cheapest" tie-break)
    best_reaches = best_runway >= horizon

    for fracs in all_combinations(limits, step):
        # dollars cut from each lever = its monthly median x the fraction we cut (rounded to cents)
        cuts = {lever: np.round(lever_amounts[lever] * f, 2) for lever, f in zip(LEVERS, fracs)}
        total = cuts["cash"] + cuts["bills"] + cuts["transfers"]
        runway = runway_many(buffer_left, spending - total, income)   # same formula, lower spending
        n_levers = sum(1 for f in fracs if f > 0)

        if aim == "cheapest":
            reaches = runway >= horizon
            better = (
                (reaches & ~best_reaches)                                  # first option that reaches
                | (reaches & best_reaches & (total < best_total))          # reaches for fewer dollars
                | (reaches & best_reaches & (total == best_total) & (n_levers < best_levers))
                | (~reaches & ~best_reaches & (runway > best_runway))      # nothing reaches yet: longest
                | (~reaches & ~best_reaches & (runway == best_runway) & (total < best_total))
            )
        else:   # "max"
            reaches = best_reaches
            better = (runway > best_runway) | ((runway == best_runway) & (total < best_total))

        # copy this combination into "best" only for the customers where it's better
        for lever in LEVERS:
            best[lever] = np.where(better, cuts[lever], best[lever])
        best_total = np.where(better, total, best_total)
        best_runway = np.where(better, runway, best_runway)
        best_levers = np.where(better, n_levers, best_levers)
        best_reaches = np.where(better, reaches, best_reaches)

    out = pd.DataFrame({f"cut_{lever}": best[lever] for lever in LEVERS}, index=table.index)
    out["total_cut"] = np.round(best_total, 2)
    out["runway_opt"] = best_runway
    # 'no shortfall' = savings left AND income covers spending after the cuts
    out["no_shortfall"] = (buffer_left > 0) & (spending - best_total - income <= 0)

    out["reached"] = best_runway >= horizon
    # PLAN.md 2.5: extra savings = horizon x shortfall at MAX cuts - buffer left (never below 0)
    max_cut = sum(np.round(lever_amounts[lever] * limits[lever], 2) for lever in LEVERS)
    shortfall_at_max = np.maximum(spending - max_cut - income, 0)
    extra = np.maximum(horizon * shortfall_at_max - buffer_left, 0)
    out["extra_savings_needed"] = np.where(out["reached"], 0.0, np.round(extra, 2))
    return out


def optimize(p, shocked, settings, ctype):
    """CONTRACT: returns dict with cuts {cash, bills, transfers} in $/month, total_cut,
    runway_opt, reached (bool or None), extra_savings_needed ($ or 0)."""
    # run the "everyone" version on a table with just this one customer
    one_table = pd.DataFrame([{lever: p[lever] for lever in LEVERS}])
    one_shocked = pd.DataFrame([{k: shocked[k] for k in ("income", "spending", "buffer_left")}])
    row = optimize_many(one_table, one_shocked, settings, limits=limits_for(ctype)).iloc[0]

    runway_opt = NO_SHORTFALL if row["no_shortfall"] else float(row["runway_opt"])
    reached = bool(row["reached"])
    return {"cuts": {lever: float(row[f"cut_{lever}"]) for lever in LEVERS},
            "total_cut": float(row["total_cut"]), "runway_opt": runway_opt,
            "reached": reached, "extra_savings_needed": float(row["extra_savings_needed"])}