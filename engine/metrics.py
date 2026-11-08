"""R1: official customer numbers. STATUS: done.

The CSVs are loaded ONCE, when this module is first imported, into a table with
one row per account. get_profile() and all_customers() just read that table.

Official definitions (AGENTS.md), per account, from data/monthly_summary.csv:
  I = median money_in
  F = median (household_bills + insurance + loan_payments)   (display only)
  S = median money_out
  H = median household_bills
  B = mean avg_daily_balance over the account's LAST 6 rows sorted by month
  P = monthly_payment from loans.csv if the loan is still running (status C or D), else 0
"""
from pathlib import Path

import pandas as pd

from engine.customer_types import assign_types

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def runway(buffer_left, spending, income):
    """README runway formula. Returns months (1 decimal) or the string 'no shortfall (120+)'."""
    gap = spending - income
    if buffer_left <= 0:
        return 0.0
    if gap <= 0:
        return "no shortfall (120+)"
    return round(min(buffer_left / gap, 120), 1)


def _build_table():
    """Read the CSVs and build the one-row-per-account customer table."""
    ms = pd.read_csv(DATA_DIR / "monthly_summary.csv")
    loans = pd.read_csv(DATA_DIR / "loans.csv")

    # Sort by month so "last 6 rows" really means the 6 most recent months
    ms = ms.sort_values(["account_id", "month"])
    ms["fixed"] = ms["household_bills"] + ms["insurance"] + ms["loan_payments"]
    g = ms.groupby("account_id")

    table = pd.DataFrame({
        "I": g["money_in"].median(),
        "F": g["fixed"].median(),
        "S": g["money_out"].median(),
        "H": g["household_bills"].median(),
        "B": g["avg_daily_balance"].apply(lambda s: s.tail(6).mean()),
        # lever medians for the optimizer
        "cash": g["cash_withdrawals_genuine"].median(),
        "bills": g["household_bills"].median(),          # same as H
        "transfers": g["transfers_out_other"].median(),
        "months_of_history": g.size(),
        # used for the customer type
        "pension": g["pension_in"].median(),
        "below_zero_months": g["days_below_zero"].apply(lambda s: int((s > 0).sum())),
    })

    # P: only loans still running at the end of 2025 (C = running OK, D = running, in debt)
    running = loans[loans["status"].isin(["C", "D"])].set_index("account_id")["monthly_payment"]
    table["P"] = running.reindex(table.index).fillna(0.0)

    table = assign_types(table)
    table.index.name = "account_id"
    return table


_TABLE = _build_table()

PROFILE_KEYS = ["account_id", "I", "F", "S", "H", "B", "P",
                "cash", "bills", "transfers", "months_of_history"]


def customer_row(account_id):
    """One account's full row as a dict. Raises ValueError for an unknown account."""
    try:
        aid = int(account_id)
    except (TypeError, ValueError):
        raise ValueError(f"Not a valid account id: {account_id!r}")
    if aid not in _TABLE.index:
        raise ValueError(f"Unknown account: {aid}")
    row = _TABLE.loc[aid].to_dict()
    row["account_id"] = aid
    return row


def get_profile(account_id):
    """Official I, F, S, H, B, P + lever medians for one account.
    CONTRACT: returns a dict with exactly these keys:
    account_id, I, F, S, H, B, P, cash, bills, transfers, months_of_history.
    Raises ValueError for an unknown account."""
    row = customer_row(account_id)
    p = {k: float(row[k]) for k in PROFILE_KEYS if k not in ("account_id", "months_of_history")}
    p["account_id"] = row["account_id"]
    p["months_of_history"] = int(row["months_of_history"])
    return {k: p[k] for k in PROFILE_KEYS}     # keep the contract's key order


def all_customers():
    """The whole customer table (one row per account, indexed by account_id) for step 6.
    Columns: I, F, S, H, B, P, cash, bills, transfers, months_of_history,
    pension, below_zero_months, type, reason. Returns a copy, so callers can't change it."""
    return _TABLE.copy()
