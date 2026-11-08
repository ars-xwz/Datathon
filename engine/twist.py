"""R7, R8: words -> settings. OWNER: Angela. STATUS: STUB.
The language model ONLY translates; it never calculates."""

TWIST_SCHEMA = {
    "account_id": None,
    "income_multiplier": 1.0,
    "apply_ei_cap": False,
    "bills_increase_pct": 0.0,
    "one_off_amount": 0.0,
    "one_off_months_spending": 0.0,
    "horizon_months": None,
}

def validate(s):
    """Raise ValueError if any setting is outside sensible ranges (AGENTS.md)."""
    # STUB: add range checks
    return s

def fallback_parse(text, previous=None):
    """Keyword/regex parser. Merges what the text mentions into previous settings."""
    # STUB: always returns README twist 3 for account 23595
    s = dict(previous or TWIST_SCHEMA)
    s.update({"account_id": 23595, "income_multiplier": 0.55, "bills_increase_pct": 15.0, "horizon_months": 6})
    return s

def llm_parse(text, previous=None, timeout=8):
    """Structured-output call to the LLM provider (decision D-6). Not built yet."""
    raise NotImplementedError

def parse_twist(text, previous=None):
    """CONTRACT: returns (settings_dict, parser_used) where parser_used is 'AI' or 'backup'."""
    try:
        return validate(llm_parse(text, previous)), "AI"
    except Exception:
        return validate(fallback_parse(text, previous)), "backup"
