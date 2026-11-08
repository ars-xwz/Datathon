"""R6: goal plan (emergency fund). OWNER: Arshiya. STATUS: done (placeholder D-5).

Fund target = FUND_MONTHS x S (months of typical spending).
Monthly saving = SAVE_SHARE x surplus, where surplus = I - S.
Months = (target - B) / monthly saving, rounded up.
"""
import math

# PLACEHOLDER: decision D-5
FUND_MONTHS = 3
SAVE_SHARE = 0.5


def goal_plan(p, ctype):
    """CONTRACT: returns dict with target, monthly_saving, months, message."""
    target = FUND_MONTHS * p["S"]
    still_needed = target - p["B"]
    surplus = p["I"] - p["S"]
    monthly_saving = max(SAVE_SHARE * surplus, 0.0)

    if still_needed <= 0:
        # already have the fund -> no months to count
        return {"target": target, "monthly_saving": 0.0, "months": 0,
                "message": f"Already funded: savings of ${p['B']:,.0f} cover the "
                           f"${target:,.0f} goal ({FUND_MONTHS} months of spending)."}
    if monthly_saving <= 0:
        # spends all income (or more) -> can't save, so months would be infinite: show None
        return {"target": target, "monthly_saving": 0.0, "months": None,
                "message": f"No monthly surplus to save from: spending needs to drop below income "
                           f"before building the ${target:,.0f} fund."}

    months = math.ceil(still_needed / monthly_saving)
    return {"target": target, "monthly_saving": monthly_saving, "months": months,
            "message": f"Save ${monthly_saving:,.0f}/month for {months} months to reach ${target:,.0f}."}