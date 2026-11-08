"""R3, R4: apply a shock -> runways (a) today and (b) after shock. OWNER: Angela. STATUS: STUB."""
from engine.metrics import runway

def apply_shock(p, settings):
    """CONTRACT: returns dict with income, spending, buffer_left, runway_today, runway_shock, verdict_shock."""
    # STUB: replace with the official math in PLAN.md 2.4 (this stub already follows it)
    income = settings["income_multiplier"] * p["I"]
    spending = p["S"] + settings["bills_increase_pct"] / 100 * p["H"]
    one_off = settings["one_off_amount"] + settings["one_off_months_spending"] * p["S"]
    buffer_left = p["B"] - one_off
    r_today = runway(p["B"], p["S"], p["I"])
    r_shock = runway(buffer_left, spending, income)
    h = settings.get("horizon_months")
    verdict = None if h is None else (r_shock == "no shortfall (120+)" or r_shock >= h)
    return {"income": income, "spending": spending, "one_off": one_off, "buffer_left": buffer_left,
            "runway_today": r_today, "runway_shock": r_shock, "verdict_shock": verdict}
