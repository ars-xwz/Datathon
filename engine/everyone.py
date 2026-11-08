"""R10: run the twist on all customers. OWNER: Optimizer teammate. STATUS: STUB.
Must give the same runway as apply_shock() for every account (test V11)."""

def run_on_everyone(settings, account_id=None):
    """CONTRACT: returns dict with pct_under_shock, pct_under_opt, by_type {type: (pct_shock, pct_opt)},
    rank_longer_pct (share of customers with a longer runway), rank_in_type_pct."""
    # STUB
    return {"horizon": settings.get("horizon_months") or 6,
            "pct_under_shock": 39, "pct_under_opt": 11,
            "by_type": {"Pension-protected": (3, 0), "Trim": (11, 3),
                        "Savings-first": (59, 14), "Stabilize first": (76, 42)},
            "rank_longer_pct": 67, "rank_in_type_pct": 49}
