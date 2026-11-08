"""R5: optimizer -> runway (c). OWNER: Optimizer teammate. STATUS: STUB.
Levers: cash withdrawals, household bills, other transfers out ONLY."""

# PLACEHOLDER: decision D-1 (cut limits)
LIMITS = {"cash": 0.30, "bills": 0.10, "transfers": 0.50}
# PLACEHOLDER: decision D-2 (aim) and D-3 (step, best, tie-break)
STEP = 0.05

def optimize(p, shocked, settings, ctype):
    """CONTRACT: returns dict with cuts {cash, bills, transfers} in $/month, total_cut,
    runway_opt, reached (bool or None), extra_savings_needed ($ or 0)."""
    # STUB: fixed fake cuts
    cuts = {"cash": 1104.0, "bills": 214.0, "transfers": 281.0}
    return {"cuts": cuts, "total_cut": sum(cuts.values()), "runway_opt": 10.1,
            "reached": True, "extra_savings_needed": 0.0}
