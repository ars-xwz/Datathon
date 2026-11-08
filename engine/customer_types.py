"""R2: customer type. OWNER: Optimizer teammate. STATUS: STUB."""

TYPES = ["Stabilize first", "Pension-protected", "Savings-first", "Trim"]

def classify(account_id):
    """First match wins: Stabilize first -> Pension-protected -> Savings-first -> Trim.
    CONTRACT: returns (type_name, reason_sentence)."""
    # STUB
    return "Savings-first", "55% of their income is above the 2026 EI maximum ($3,159/month)."
