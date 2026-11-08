"""Tests for steps 1-2 (R7, R8, V3, V12): backup parser, follow-ups, validation.
Run: python tests/test_twist.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.twist import fallback_parse, parse_twist, validate, problems, TWIST_SCHEMA


def expect(s, **want):
    """Check the settings match `want`; anything not listed must be at its default."""
    full = dict(TWIST_SCHEMA); full.update(want)
    for k, v in full.items():
        assert s[k] == v, f"{k}: got {s[k]!r}, expected {v!r}\n  settings: {s}"


def test_readme_chain_1_and_2():
    s1 = fallback_parse("Account 23595 was laid off. EI pays 55% of their usual income for 6 months. Do they make it?")
    expect(s1, account_id=23595, income_multiplier=0.55, horizon_months=6)
    s2 = fallback_parse("The furnace dies, and the repair costs a full month of their typical spending.", s1)
    expect(s2, account_id=23595, income_multiplier=0.55, horizon_months=6, one_off_months_spending=1)


def test_readme_chain_3_and_followup():
    s3 = fallback_parse("Account 23595 loses their job (EI at 55%) and household bills go up 15% in the same month.")
    expect(s3, account_id=23595, income_multiplier=0.55, bills_increase_pct=15.0)
    s4 = fallback_parse("What if it's 9 months instead?", s3)
    expect(s4, account_id=23595, income_multiplier=0.55, bills_increase_pct=15.0, horizon_months=9)


def test_new_account_starts_fresh():
    prev = fallback_parse("Account 23595 loses their job (EI at 55%) and household bills go up 15%.")
    s = fallback_parse("Account 55447 gets a $3,500 car repair bill", prev)
    expect(s, account_id=55447, one_off_amount=3500.0)


def test_missing_account():
    s = fallback_parse("bills up 10%")
    expect(s, bills_increase_pct=10.0)
    assert any("Which account" in p for p in problems(s))
    try:
        validate(s); raise AssertionError("validate should raise for a missing account")
    except ValueError as e:
        assert "Which account" in str(e)


def test_rephrasings():
    expect(fallback_parse("account 23595 gets fired, EI covers 55%"), account_id=23595, income_multiplier=0.55)
    expect(fallback_parse("Customer 23595 is laid off"), account_id=23595, income_multiplier=0.55)
    expect(fallback_parse("account 23595 rent jumps 20%"), account_id=23595, bills_increase_pct=20.0)
    expect(fallback_parse("account 23595 utilities up 12.5%"), account_id=23595, bills_increase_pct=12.5)
    expect(fallback_parse("account 23595 has a $2k car repair"), account_id=23595, one_off_amount=2000.0)
    expect(fallback_parse("account 23595: repair costs two months of their spending"), account_id=23595, one_off_months_spending=2)
    expect(fallback_parse("account 23595: repair costs half a month of spending"), account_id=23595, one_off_months_spending=0.5)
    expect(fallback_parse("account 23595 loses their job and EI pays 55%. Can they last 12 months?"),
           account_id=23595, income_multiplier=0.55, horizon_months=12)
    expect(fallback_parse("account 23595 bills drop 10%"), account_id=23595, bills_increase_pct=-10.0)


def test_followup_chain_keeps_everything():
    s = fallback_parse("Account 23595 was laid off, EI at 55%.")
    s = fallback_parse("What if their household bills also go up 15%?", s)
    s = fallback_parse("And a $2,000 car repair on top.", s)
    s = fallback_parse("Make it 9 months.", s)
    expect(s, account_id=23595, income_multiplier=0.55, bills_increase_pct=15.0, one_off_amount=2000.0, horizon_months=9)


def test_parse_twist_uses_backup_and_never_raises():
    s, used = parse_twist("bills up 10%", dict(TWIST_SCHEMA))
    assert used == "backup"
    s, used = parse_twist("Account 23595 was laid off", dict(TWIST_SCHEMA))
    expect(s, account_id=23595, income_multiplier=0.55)


def test_range_checks():
    bad = dict(TWIST_SCHEMA, account_id=23595, income_multiplier=9, bills_increase_pct=500, horizon_months=0)
    msg = " ".join(problems(bad))
    assert "Income" in msg and "bills" in msg and "goal" in msg


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for t in tests:
        t()
    print(f"all {len(tests)} twist tests passed")
