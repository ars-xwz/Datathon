"""R1: official customer numbers. OWNER: Angela. STATUS: STUB (fake numbers)."""

def runway(buffer_left, spending, income):
    """README runway formula. Returns months (1 decimal) or the string 'no shortfall (120+)'."""
    gap = spending - income
    if buffer_left <= 0:
        return 0.0
    if gap <= 0:
        return "no shortfall (120+)"
    return round(min(buffer_left / gap, 120), 1)

def get_profile(account_id):
    """Official I, F, S, H, B, P + lever medians for one account.
    CONTRACT: returns a dict with exactly these keys."""
    # STUB: replace with real calculation from data/monthly_summary.csv + loans.csv
    return {
        "account_id": account_id,
        "I": 6802.4, "F": 2713.4, "S": 6746.2, "H": 2141.4, "B": 17350.5, "P": 0.0,
        "cash": 3681.0,       # median cash_withdrawals_genuine
        "bills": 2141.4,      # median household_bills (same as H)
        "transfers": 563.0,   # median transfers_out_other
        "months_of_history": 40,
    }
