"""Tests for step 3 (R1 customer profile, R2 customer type).
Run:  python tests/test_customer.py      (or: python -m pytest tests)

Golden values were calculated separately with plain pandas, straight from the CSVs,
using the AGENTS.md definitions (not by calling the engine)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from engine.metrics import get_profile, all_customers, runway, PROFILE_KEYS
from engine.customer_types import classify, TYPES

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# account: (I, F, S, H, B, P), rounded to cents
GOLDEN = {
    20111: (6339.39, 2330.06, 8599.60, 0.00, 17611.86, 2330.19),   # running loan in debt (D)
    23595: (6802.44, 2713.42, 6746.16, 2141.41, 17350.53, 0.00),   # the demo account
    20176: (4281.30, 40.27, 3211.54, 40.27, 34694.32, 0.00),       # pensioner
    40624: (3570.29, 2611.47, 2809.44, 1688.33, 8855.77, 0.00),    # finished loan (A) -> P = 0
}

# V7 edge accounts: shortest history, zero income, buffer <= 0 (per PLAN.md)
EDGE = [49649, 21132, 22682, 32078, 36407]


def test_golden_profiles():                                   # R1, V1
    for aid, (I, F, S, H, B, P) in GOLDEN.items():
        p = get_profile(aid)
        for name, want in zip("IFSHBP", (I, F, S, H, B, P)):
            assert abs(p[name] - want) < 0.01, f"{aid} {name}: got {p[name]}, want {want}"


def test_profile_keys_exact():                                # CONTRACT
    p = get_profile(23595)
    assert list(p.keys()) == PROFILE_KEYS
    assert p["bills"] == p["H"]
    assert isinstance(p["months_of_history"], int)


def test_unknown_account_raises():                            # R1
    for bad in (1, 999999, "abc", None):
        for fn in (get_profile, classify):
            try:
                fn(bad)
            except ValueError:
                continue
            raise AssertionError(f"{fn.__name__}({bad!r}) should raise ValueError")


def test_type_counts():                                       # R2, V2
    counts = all_customers()["type"].value_counts().to_dict()
    assert counts == {"Savings-first": 2348, "Trim": 1127,
                      "Pension-protected": 737, "Stabilize first": 288}, counts


def test_classify_examples():                                 # R2
    assert classify(20111)[0] == "Stabilize first"     # 4 months below zero
    assert classify(20176)[0] == "Pension-protected"
    assert classify(23595)[0] == "Savings-first"       # 0.55 * 6802 = 3741 > 3159
    assert classify(40624)[0] == "Trim"
    t, reason = classify(20111)
    assert t in TYPES and "4 months" in reason


def test_zero_income_is_not_pension():                        # R2 edge case
    for aid in (21132, 22682):                         # zero income accounts
        assert get_profile(aid)["I"] == 0
        assert classify(aid)[0] != "Pension-protected"


def test_P_only_for_running_loans():                          # R1
    loans = pd.read_csv(os.path.join(DATA, "loans.csv")).set_index("account_id")
    table = all_customers()
    for aid, row in table.iterrows():
        if aid in loans.index and loans.loc[aid, "status"] in ("C", "D"):
            assert row["P"] == loans.loc[aid, "monthly_payment"], aid
        else:
            assert row["P"] == 0, aid


def test_every_account_works():                               # R1 "runs for all 4,500", N3
    table = all_customers()
    assert len(table) == 4500
    for aid in table.index:
        p = get_profile(aid)
        assert classify(aid)[0] in TYPES
        assert p["months_of_history"] >= 12
    for aid in EDGE:
        get_profile(aid); classify(aid)


def test_all_customers_is_a_copy():
    t = all_customers()
    t.loc[23595, "I"] = -1
    assert get_profile(23595)["I"] > 0


def test_readme_twists_on_23595():                            # R4 sanity check with the official formula
    p = get_profile(23595)
    assert runway(p["B"], p["S"], 0.55 * p["I"]) == 5.8                       # laid off, EI 55%
    assert runway(p["B"], p["S"] + 0.15 * p["H"], 0.55 * p["I"]) == 5.2       # + bills up 15%
    assert runway(p["B"] - p["S"], p["S"], p["I"]) == "no shortfall (120+)"   # furnace = 1 month


def test_lead_done_when():                                    # lead's "Done when" checklist for step 3
    p = get_profile(23595)
    want = {"I": 6802.4, "S": 6746.2, "F": 2713.4, "H": 2141.4, "B": 17350.5, "P": 0.0,
            "cash": 3681.2, "bills": 2141.4, "transfers": 562.6}
    for k, v in want.items():
        assert round(p[k], 1) == v, f"23595 {k}: got {round(p[k], 1)}, want {v}"
    assert classify(23595)[0] == "Savings-first"
    assert round(get_profile(55447)["P"], 2) == 3658.58


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("passed:", t.__name__)
    print(f"all {len(tests)} customer tests passed")
