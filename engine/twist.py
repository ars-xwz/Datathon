"""R7, R8: words -> settings. OWNER: Angela.
The language model ONLY translates; it never calculates.

How it works:
- parse_twist() tries the AI translator first (llm_parse); if that isn't set up, fails or is slow,
  it uses fallback_parse(), a keyword/regex parser that works with no internet.
- Follow-ups: previous settings are kept and only what the new text mentions changes.
  If the text names a DIFFERENT account, we start from the defaults (it's a new twist).
- parse_twist() never raises for a missing account, so the Confirm step can still show the
  fields and let the user type it. pipeline.run() calls validate() before calculating.
"""
import re

TWIST_SCHEMA = {
    "account_id": None,
    "income_multiplier": 1.0,
    "apply_ei_cap": False,
    "bills_increase_pct": 0.0,
    "one_off_amount": 0.0,
    "one_off_months_spending": 0.0,
    "horizon_months": None,
}

DEFAULT_EI = 0.55   # README: EI pays 55% of usual income

# ---------------------------------------------------------------- checking

def problems(s):
    """Return a list of plain-English problems with the settings (empty list = all good).
    The Confirm screen can show these next to the fields."""
    out = []
    if s.get("account_id") is None:
        out.append("Which account? Add it, e.g. 'account 23595'.")
    m = s.get("income_multiplier")
    if m is None or not (0 <= m <= 1.5):
        out.append("Income after the shock must be between 0% and 150%.")
    b = s.get("bills_increase_pct")
    if b is None or not (-50 <= b <= 300):
        out.append("Household bills change must be between -50% and +300%.")
    if (s.get("one_off_amount") or 0) < 0 or (s.get("one_off_months_spending") or 0) < 0:
        out.append("One-off costs can't be negative.")
    h = s.get("horizon_months")
    if h is not None and not (1 <= h <= 120):
        out.append("The goal must be between 1 and 120 months.")
    return out


def validate(s):
    """Raise ValueError (with all problems in one message) if the settings can't be run. Returns s if fine."""
    p = problems(s)
    if p:
        raise ValueError(" ".join(p))
    return s

# ---------------------------------------------------------------- backup parser

NUMBER_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4,
                "half": 0.5, "half a": 0.5}
SPENDING_WORDS = r"(?:their\s+|his\s+|her\s+)?(?:typical\s+|usual\s+|normal\s+|average\s+|monthly\s+)?spending"


def _number(word):
    word = word.strip().lower()
    return NUMBER_WORDS[word] if word in NUMBER_WORDS else float(word.replace(",", ""))


def fallback_parse(text, previous=None):
    """Keyword/regex parser. Merges what the text mentions into previous settings."""
    t = " ".join(text.lower().split())

    # Which account? A different account than before means a brand-new twist.
    m = re.search(r"(?:account|acct|customer|client)\s*(?:id|number|no\.?|#)?\s*#?\s*(\d{2,6})", t)
    new_account = int(m.group(1)) if m else None
    reset = re.search(r"\b(reset|start over|new twist|no shock)\b", t) is not None
    prev_account = (previous or {}).get("account_id")
    if previous and not reset and (new_account is None or new_account == prev_account):
        s = dict(previous)
    else:
        s = dict(TWIST_SCHEMA)
        if reset and new_account is None and prev_account is not None:
            s["account_id"] = prev_account
    if new_account is not None:
        s["account_id"] = new_account

    # Job loss / EI -> income multiplier
    job_loss = re.search(r"laid off|lay ?off|los(?:e|es|t|ing) (?:their|his|her|the|a) job|job loss|"
                         r"unemploy|fired|out of work", t)
    pct = (re.search(r"\bei\b[^%\d]{0,30}(\d+(?:\.\d+)?)\s*%", t)
           or re.search(r"(\d+(?:\.\d+)?)\s*%\s*of\s+(?:their\s+|his\s+|her\s+)?(?:usual\s+|normal\s+|typical\s+)?income", t)
           or re.search(r"income[^%\d]{0,30}(\d+(?:\.\d+)?)\s*%", t))
    if pct:
        s["income_multiplier"] = float(pct.group(1)) / 100
    elif job_loss:
        s["income_multiplier"] = DEFAULT_EI

    # Household bills / rent / utilities up X%
    m = re.search(r"(?:bills?|rent|utilit\w*|hydro)[^%.]{0,40}?(\d+(?:\.\d+)?)\s*%", t)
    if m:
        pct_val = float(m.group(1))
        down = re.search(r"(?:bills?|rent|utilit\w*|hydro)[^%.]{0,40}?(?:down|drop|fall|decrease|lower)", t)
        s["bills_increase_pct"] = -pct_val if down else pct_val

    # One-off cost in months of spending ("a full month of their typical spending")
    m = re.search(r"(half a|an?|one|two|three|four|half|\d+(?:\.\d+)?)\s+(?:full\s+)?months?\s+of\s+" + SPENDING_WORDS, t)
    if m:
        s["one_off_months_spending"] = _number(m.group(1))

    # One-off cost in dollars ("$2,000", "$2k", "2000 dollars")
    m = re.search(r"\$\s*([\d,]+(?:\.\d+)?)\s*(k)?\b", t) or re.search(r"([\d,]+(?:\.\d+)?)\s*(k)?\s*dollars", t)
    if m:
        s["one_off_amount"] = _number(m.group(1)) * (1000 if m.group(2) else 1)

    # Goal: "6 months" that is NOT "N months of spending"
    m = re.search(r"(\d+)\s*months?(?!\s+of\s+" + SPENDING_WORDS + r")", t)
    if m:
        s["horizon_months"] = int(m.group(1))

    return s

# ---------------------------------------------------------------- AI translator

def llm_parse(text, previous=None, timeout=8):
    """Structured-output call to the AI service (decision D-6). Not built yet.
    When built: send the text + previous settings, require a JSON answer matching TWIST_SCHEMA,
    time out after `timeout` seconds. Raising here makes parse_twist use the backup parser."""
    raise NotImplementedError("AI translator not set up yet")


def _ranges_ok(s):
    """Range problems only (a missing account is allowed at this stage)."""
    return [p for p in problems(s) if not p.startswith("Which account")] == []


def parse_twist(text, previous=None):
    """CONTRACT: returns (settings_dict, parser_used) where parser_used is 'AI' or 'backup'.
    Never raises for a missing account; the UI shows problems(settings) and pipeline.run() validates."""
    try:
        s = llm_parse(text, previous)
        if _ranges_ok(s):
            return s, "AI"
    except Exception:
        pass
    return fallback_parse(text, previous), "backup"
