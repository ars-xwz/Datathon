"""R2: customer type (first match wins). STATUS: done.

Rules (AGENTS.md):
  1. Stabilize first   : any month with days_below_zero > 0
  2. Pension-protected : median pension_in >= 30% of I   (and I > 0)
  3. Savings-first     : 0.55 * I > EI_MAX ($3,159/month)
  4. Trim              : everyone else

This file does NOT import metrics.py at the top, because metrics.py uses
assign_types() while building its table (that would be a circular import).
"""

TYPES = ["Stabilize first", "Pension-protected", "Savings-first", "Trim"]

# 2026 EI maximum: $729/week * 52 weeks / 12 months = $3,159/month
EI_MAX = 729 * 52 / 12


def type_and_reason(I, pension, below_zero_months):
    """Type + one-sentence reason for one customer, from their official numbers."""
    if below_zero_months > 0:
        word = "month" if below_zero_months == 1 else "months"
        return ("Stabilize first",
                f"Their balance went below zero in {below_zero_months} {word}, "
                f"so the first step is to stop going into overdraft.")
    # I > 0 guard: with zero income, 0 >= 0.3 * 0 would wrongly count as pension-based
    if I > 0 and pension >= 0.3 * I:
        return ("Pension-protected",
                f"{round(pension / I * 100)}% of their income is pension, which a job loss doesn't cut.")
    if 0.55 * I > EI_MAX:
        return ("Savings-first",
                f"55% of their income (${0.55 * I:,.0f}/month) is above the 2026 EI maximum "
                f"(${EI_MAX:,.0f}/month), so EI wouldn't replace as much as the official rule assumes.")
    return ("Trim",
            "No overdraft history, not pension-based, and under the EI cap: a standard cuts plan fits.")


def assign_types(table):
    """Add 'type' and 'reason' columns to the customer table (used by metrics.py)."""
    pairs = [type_and_reason(r.I, r.pension, r.below_zero_months) for r in table.itertuples()]
    table["type"] = [p[0] for p in pairs]
    table["reason"] = [p[1] for p in pairs]
    return table


def classify(account_id):
    """First match wins: Stabilize first -> Pension-protected -> Savings-first -> Trim.
    CONTRACT: returns (type_name, reason_sentence). Raises ValueError for an unknown account."""
    from engine.metrics import customer_row   # imported here to avoid a circular import
    row = customer_row(account_id)
    return row["type"], row["reason"]
