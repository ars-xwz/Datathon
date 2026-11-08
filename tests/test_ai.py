"""Tests for the AI translator (R7) WITHOUT internet: the AI's replies are faked.
Run: python tests/test_ai.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine.twist as tw
from engine.twist import parse_twist, TWIST_SCHEMA

NOTHING = dict(account_id=None, income_multiplier=None, bills_increase_pct=None, one_off_amount=None,
               one_off_months_spending=None, horizon_months=None, reset=False)


def fake_ai(reply=None, error=None):
    """Replace the AI call with a fake answer (or a fake failure)."""
    def _fake(text, previous, timeout):
        if error:
            raise error
        return dict(NOTHING, **reply)
    tw._ask_ai = _fake


def test_ai_answer_is_used():
    fake_ai(dict(account_id=23595, income_multiplier=0.55, bills_increase_pct=15))
    s, used = parse_twist("Account 23595 gets let go with a bit over half their pay from EI and rent creeping up 15%")
    assert used == "AI", used
    assert s["account_id"] == 23595 and s["income_multiplier"] == 0.55 and s["bills_increase_pct"] == 15.0
    assert s["horizon_months"] is None and s["one_off_amount"] == 0.0


def test_ai_followup_keeps_previous():
    prev = dict(TWIST_SCHEMA, account_id=23595, income_multiplier=0.55, bills_increase_pct=15.0)
    fake_ai(dict(horizon_months=9))
    s, used = parse_twist("what about 9 months", prev)
    assert used == "AI" and s == dict(prev, horizon_months=9), s


def test_ai_new_account_starts_fresh():
    prev = dict(TWIST_SCHEMA, account_id=23595, income_multiplier=0.55, bills_increase_pct=15.0)
    fake_ai(dict(account_id=55447, one_off_amount=3500))
    s, _ = parse_twist("account 55447, $3,500 repair", prev)
    assert s == dict(TWIST_SCHEMA, account_id=55447, one_off_amount=3500.0), s


def test_bad_ai_answer_falls_back():
    fake_ai(dict(account_id=23595, income_multiplier=55))          # AI forgot to divide by 100
    s, used = parse_twist("Account 23595 was laid off. EI pays 55% of their usual income.")
    assert used == "backup" and s["income_multiplier"] == 0.55


def test_ai_failure_falls_back():
    for err in (TimeoutError("slow"), OSError("no internet"), NotImplementedError("no key"), KeyError("weird reply")):
        fake_ai(error=err)
        s, used = parse_twist("Account 23595 was laid off. EI pays 55% of their usual income.")
        assert used == "backup" and s["income_multiplier"] == 0.55, (err, s)


def test_no_key_means_backup():
    real_env, real_ask = tw._env, tw._ask_ai
    try:
        tw._env = lambda name: None
        tw._ask_ai = real_ask
        s, used = parse_twist("Account 23595 was laid off")
        assert used == "backup"
    finally:
        tw._env = real_env


if __name__ == "__main__":
    real = tw._ask_ai
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for t in tests:
        t(); tw._ask_ai = real; print("passed:", t.__name__)
    print(f"all {len(tests)} AI tests passed")
