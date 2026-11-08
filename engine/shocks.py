"""R3, R4: apply a shock -> runways (a) today and (b) after shock. OWNER: Arshiya. STATUS: done.

Official math (PLAN.md 2.4, AGENTS.md):
  income   = income_multiplier x I
  spending = S + (bills_increase_pct / 100) x H
  one_off  = one_off_amount + one_off_months_spending x S
  (a) today: runway(B, S, I)
  (b) shock: runway(B - one_off, spending, income)

Two versions of the same math:
  apply_shock(p, settings)        one customer, used by the pipeline (step 4)
  shock_many(table, settings)     every customer at once, for step 6 (everyone.py)
Both call shock_numbers(), so they can't disagree.

EI-cap adjusted view (R11): a SEPARATE, labelled extra number. It never replaces runway (b).
  ei_cap_view(p, settings)        one customer
  ei_cap_many(table, settings)    every customer at once
Real EI pays at most $729/week (2026), about $3,159/month. The official rule (55% of income)
ignores that, so for higher earners it overstates how much EI pays.
"""
import numpy as np
import pandas as pd

from engine.metrics import runway
from engine.customer_types import EI_MAX   # $729/week x 52 / 12 = $3,159/month

NO_SHORTFALL = "no shortfall (120+)"   # what metrics.runway() returns when income covers spending


def shock_numbers(I, S, H, B, settings):
    """Income, spending, one-off and buffer left after the shock. Works on numbers OR pandas columns."""
    income = settings["income_multiplier"] * I
    spending = S + settings["bills_increase_pct"] / 100 * H
    one_off = settings["one_off_amount"] + settings["one_off_months_spending"] * S
    buffer_left = B - one_off
    return income, spending, one_off, buffer_left


def runway_number(r):
    """Turn a runway into a number we can compare: 'no shortfall (120+)' counts as 120."""
    return 120.0 if r == NO_SHORTFALL else r


def runway_many(buffer_left, spending, income):
    """Same rule as metrics.runway(), for whole columns at once. 'No shortfall' becomes 120.0."""
    buffer_left = np.asarray(buffer_left, dtype=float)
    gap = np.asarray(spending, dtype=float) - np.asarray(income, dtype=float)
    # np.where needs a safe value to divide by, even in rows where we won't use the result
    safe_gap = np.where(gap > 0, gap, 1.0)
    months = np.minimum(buffer_left / safe_gap, 120)
    months = np.round(months, 1)                           # 1 decimal, like metrics.runway()
    result = np.where(gap <= 0, 120.0, months)            # income covers spending
    result = np.where(buffer_left <= 0, 0.0, result)      # no savings left (checked first in runway())
    return result


def apply_shock(p, settings):
    """CONTRACT: returns dict with income, spending, buffer_left, runway_today, runway_shock, verdict_shock."""
    income, spending, one_off, buffer_left = shock_numbers(p["I"], p["S"], p["H"], p["B"], settings)
    r_today = runway(p["B"], p["S"], p["I"])               # (a) today, no shock
    r_shock = runway(buffer_left, spending, income)        # (b) after shock = OFFICIAL number
    h = settings.get("horizon_months")
    verdict = None if h is None else runway_number(r_shock) >= h
    return {"income": income, "spending": spending, "one_off": one_off, "buffer_left": buffer_left,
            "runway_today": r_today, "runway_shock": r_shock, "verdict_shock": verdict}


def shock_many(table, settings):
    """apply_shock() for every customer at once. `table` = metrics.all_customers().
    Returns a DataFrame (same index) with income, spending, one_off, buffer_left,
    runway_today, runway_shock (numbers; 'no shortfall' = 120.0)."""
    income, spending, one_off, buffer_left = shock_numbers(
        table["I"], table["S"], table["H"], table["B"], settings)
    out = pd.DataFrame({"income": income, "spending": spending,
                        "one_off": one_off, "buffer_left": buffer_left}, index=table.index)
    out["runway_today"] = runway_many(table["B"], table["S"], table["I"])
    out["runway_shock"] = runway_many(buffer_left, spending, income)
    return out


EI_CAP_LABEL = (f"Adjusted view (not the official number): EI capped at the 2026 maximum "
                f"of ${EI_MAX:,.0f}/month")


def capped_income(income, settings):
    """Income after the shock, with EI capped at EI_MAX. Works on numbers OR pandas columns.
    The cap only applies to a job loss (income_multiplier below 1); otherwise income is unchanged."""
    if settings["income_multiplier"] >= 1:
        return income                                  # no job loss -> no EI -> nothing to cap
    return np.minimum(income, EI_MAX)


def ei_cap_view(p, settings):
    """R11: extra labelled runway with EI capped. Returns income_capped, runway_capped,
    verdict_capped, cap_changes_answer (True if the cap lowers income), label."""
    income, spending, _, buffer_left = shock_numbers(p["I"], p["S"], p["H"], p["B"], settings)
    income_capped = float(capped_income(income, settings))
    r = runway(buffer_left, spending, income_capped)
    h = settings.get("horizon_months")
    return {"income_capped": income_capped, "runway_capped": r,
            "verdict_capped": None if h is None else runway_number(r) >= h,
            "cap_changes_answer": income_capped < income, "label": EI_CAP_LABEL}


def ei_cap_many(table, settings):
    """ei_cap_view() for every customer at once. Returns a DataFrame (same index) with
    income_capped and runway_capped (numbers; 'no shortfall' = 120.0)."""
    income, spending, _, buffer_left = shock_numbers(
        table["I"], table["S"], table["H"], table["B"], settings)
    income_capped = capped_income(income, settings)
    return pd.DataFrame({"income_capped": income_capped,
                         "runway_capped": runway_many(buffer_left, spending, income_capped)},
                        index=table.index)