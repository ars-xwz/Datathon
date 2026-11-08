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
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

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
SPENDING_WORDS = (r"(?:their\s+|his\s+|her\s+)?(?:typical\s+|usual\s+|normal\s+|average\s+|monthly\s+)?"
                  r"(?:spending|expenses|costs)")
MONTH_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
               "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "eighteen": 18,
               "twenty-four": 24}


def _number(word):
    word = word.strip().lower()
    return NUMBER_WORDS[word] if word in NUMBER_WORDS else float(word.replace(",", ""))


def _normalize(text):
    """Lower-case and rewrite common wordings into the forms the rules below look for."""
    t = " ".join(text.lower().split())
    t = re.sub(r"\s*(?:percent|per cent)\b", "%", t)                     # "20 percent" -> "20%"
    t = re.sub(r"\bhalf (?:a|of a) year\b", "6 months", t)                # "half a year" -> "6 months"
    t = re.sub(r"\b(?:a|one) (?:full )?year\b", "12 months", t)           # "a year" -> "12 months"
    t = re.sub(r"\b(\d+) years?\b", lambda m: f"{int(m.group(1)) * 12} months", t)
    t = re.sub(r"\b(" + "|".join(MONTH_WORDS) + r")\s+(months?)\b",       # "six months" -> "6 months"
               lambda m: f"{MONTH_WORDS[m.group(1)]} {m.group(2)}", t)
    return t


def _income_multiplier(t):
    """Income after the shock as a fraction of usual income, or None if the text doesn't say.
    Order matters: the more specific wordings are checked first."""
    pct = r"(\d+(?:\.\d+)?)\s*%"
    income = r"(?:their\s+|his\s+|her\s+)?(?:usual\s+|normal\s+|typical\s+|monthly\s+)?(?:income|pay|paycheque|paycheck|salary|earnings)"
    if re.search(r"\b(?:lose|loses|lost|losing)\s+all\s+" + income + r"|\bno income\b|\bincome (?:stops|disappears|goes to zero)", t):
        return 0.0
    m = re.search(r"\b(?:lose|loses|lost|losing)\s+" + pct + r"\s+of\s+" + income, t)
    if m:
        return 1 - float(m.group(1)) / 100
    m = re.search(income + r"[^%\d.]{0,25}?(?:drops?|falls?|decreases?|is cut|gets cut|goes down|shrinks?|declines?)\s+(?:by\s+)?" + pct, t)
    if m:
        return 1 - float(m.group(1)) / 100
    m = re.search(income + r"[^%\d.]{0,25}?(?:rises?|increases?|goes up|grows?)\s+(?:by\s+)?" + pct, t)
    if m:
        return 1 + float(m.group(1)) / 100
    if re.search(r"\bhalf\s+(?:of\s+)?" + income + r"|" + income + r"[^.]{0,25}?\b(?:by half|is halved|halves|in half)\b", t):
        return 0.5
    m = (re.search(r"\bei\b[^%\d.]{0,30}" + pct, t)                     # "EI at 55%" (never across a '.')
         or re.search(pct + r"\s+of\s+" + income, t))                  # "55% of their usual income"
    if m:
        return float(m.group(1)) / 100
    job_loss = re.search(r"laid[- ]off|lay[- ]?off|let go|los(?:e|es|t|ing) (?:their|his|her|the|a) job|job loss|"
                         r"unemploy|fired|out of work|shuts? down|clos(?:es|ed) down|\b(?:on|gets?|collects?|go on|goes on) ei\b", t)
    if job_loss:
        return DEFAULT_EI
    return None


def fallback_parse(text, previous=None):
    """Keyword/regex parser. Merges what the text mentions into previous settings."""
    t = _normalize(text)

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

    # Job loss / EI / income change -> income multiplier
    mult = _income_multiplier(t)
    if mult is not None:
        s["income_multiplier"] = mult

    # Household bills / rent / utilities up X% (or double / triple)
    bills = r"(?:bills?|rent|utilit\w*|hydro|heating)"
    m = re.search(bills + r"[^%.]{0,40}?(\d+(?:\.\d+)?)\s*%", t)
    if m:
        pct_val = float(m.group(1))
        down = re.search(bills + r"[^%.]{0,40}?(?:down|drop|fall|decrease|lower)", t)
        s["bills_increase_pct"] = -pct_val if down else pct_val
    elif re.search(bills + r"[^.]{0,20}?\b(?:double|doubles|doubled)\b", t):
        s["bills_increase_pct"] = 100.0
    elif re.search(bills + r"[^.]{0,20}?\b(?:triple|triples|tripled)\b", t):
        s["bills_increase_pct"] = 200.0

    # One-off cost in months of spending ("a full month of their typical spending")
    m = re.search(r"(half a|an?|one|two|three|four|half|\d+(?:\.\d+)?)\s+(?:full\s+)?months?\s+of\s+" + SPENDING_WORDS, t)
    if m:
        s["one_off_months_spending"] = _number(m.group(1))

    # One-off cost in dollars ("$2,000", "$2k", "2000 dollars")
    m = re.search(r"\$\s*([\d,]+(?:\.\d+)?)\s*(k)?\b", t) or re.search(r"([\d,]+(?:\.\d+)?)\s*(k)?\s*dollars", t)
    if m:
        s["one_off_amount"] = _number(m.group(1)) * (1000 if m.group(2) else 1)

    # Goal: "6 months" that is NOT "N months of spending"
    m = re.search(r"(\d+)\s*months?\b(?!\s+of\s+" + SPENDING_WORDS + r")", t)
    if m:
        s["horizon_months"] = int(m.group(1))

    return s

# ---------------------------------------------------------------- AI translator

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"   # gitignored: never commit API keys
ANTHROPIC_MODEL_DEFAULT = "claude-haiku-5-5"                  # fast + cheap; override with LLM_MODEL in .env

# What the AI must return: ONLY the settings the text mentions (null = not mentioned).
# Our code then merges these into the previous settings, so follow-up memory stays in our code.
FIELDS_SCHEMA = {
    "type": "object",
    "properties": {
        "account_id": {"type": ["integer", "null"], "description": "Account number if the text names one."},
        "income_multiplier": {"type": ["number", "null"],
            "description": "Income AFTER the shock as a fraction of usual income. 'EI pays 55%' -> 0.55. "
                           "'income falls 30%' -> 0.70. 'loses all income' -> 0. Job loss with EI but no % -> 0.55."},
        "bills_increase_pct": {"type": ["number", "null"],
            "description": "Change in household bills/rent/utilities in percent. 'up 15%' -> 15. 'double' -> 100. 'down 10%' -> -10."},
        "one_off_amount": {"type": ["number", "null"], "description": "One-off cost in dollars. '$2k' -> 2000."},
        "one_off_months_spending": {"type": ["number", "null"],
            "description": "One-off cost given as months of typical spending. 'a full month of their spending' -> 1."},
        "horizon_months": {"type": ["integer", "null"],
            "description": "The goal in months: 'do they make it 6 months?' / 'for 6 months' -> 6. 'a year' -> 12."},
        "reset": {"type": "boolean", "description": "True only if the text says to start over / clear the twist."},
    },
    "required": ["account_id", "income_multiplier", "bills_increase_pct", "one_off_amount",
                 "one_off_months_spending", "horizon_months", "reset"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = (
    "You translate a bank 'what if' twist into settings for a financial calculator. "
    "Do no calculations beyond turning words into the numbers described. "
    "Return null for every setting the text does not mention. "
    "You are given the previous settings only as context for follow-ups like 'what if it's 9 months instead?'; "
    "return only what THIS text mentions."
)


def _env(name):
    """Read a setting from the environment, or from the project's .env file (KEY=value lines)."""
    if os.environ.get(name):
        return os.environ[name]
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                if k.strip() == name:
                    return v.strip().strip('"').strip("'")
    return None


def _post(url, headers, body, timeout):
    """Send a JSON POST and return the JSON reply (separate function so tests can replace it)."""
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"content-type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:      # show the service's own error message (wrong key, model, etc.)
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}") from None


def _anthropic_headers():
    """Claude API headers. A key that isn't scoped to one workspace also needs ANTHROPIC_WORKSPACE_ID in .env."""
    h = {"x-api-key": _env("ANTHROPIC_API_KEY"),
         "anthropic-version": _env("ANTHROPIC_VERSION") or "2023-06-01"}
    if _env("ANTHROPIC_WORKSPACE_ID"):
        h["anthropic-workspace-id"] = _env("ANTHROPIC_WORKSPACE_ID")
    return h


def _ask_ai(text, previous, timeout):
    """Ask whichever AI service has a key in .env. Returns the FIELDS_SCHEMA dict."""
    user = f"Previous settings: {json.dumps(previous or {})}\nTwist: {text}"
    model = _env("LLM_MODEL")
    if _env("ANTHROPIC_API_KEY"):
        reply = _post("https://api.anthropic.com/v1/messages",
                      _anthropic_headers(),
                      {"model": model or ANTHROPIC_MODEL_DEFAULT, "max_tokens": 300, "system": SYSTEM_PROMPT,
                       "tools": [{"name": "settings", "description": "The twist's settings.",
                                  "input_schema": FIELDS_SCHEMA}],
                       "tool_choice": {"type": "tool", "name": "settings"},
                       "messages": [{"role": "user", "content": user}]}, timeout)
        return next(b["input"] for b in reply["content"] if b.get("type") == "tool_use")
    if _env("OPENAI_API_KEY"):
        if not model:
            raise RuntimeError("Set LLM_MODEL in .env to the OpenAI model your team uses.")
        reply = _post("https://api.openai.com/v1/chat/completions",
                      {"authorization": f"Bearer {_env('OPENAI_API_KEY')}"},
                      {"model": model, "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                                                    {"role": "user", "content": user}],
                       "response_format": {"type": "json_schema", "json_schema":
                                           {"name": "settings", "strict": True, "schema": FIELDS_SCHEMA}}},
                      timeout)
        return json.loads(reply["choices"][0]["message"]["content"])
    raise NotImplementedError("No AI key in .env (ANTHROPIC_API_KEY or OPENAI_API_KEY)")


def llm_parse(text, previous=None, timeout=8):
    """AI translator: the AI returns only what the text mentions; OUR code merges it into the
    previous settings with the same follow-up rules as the backup parser.
    Raises on no key / no internet / timeout / bad answer, so parse_twist() falls back to the backup parser."""
    found = _ask_ai(text, previous, timeout)
    new_account = found.get("account_id")
    prev_account = (previous or {}).get("account_id")
    if previous and not found.get("reset") and (new_account is None or new_account == prev_account):
        s = dict(previous)
    else:
        s = dict(TWIST_SCHEMA)
        if found.get("reset") and new_account is None and prev_account is not None:
            s["account_id"] = prev_account
    for k in TWIST_SCHEMA:
        if k in found and found[k] is not None and k != "apply_ei_cap":
            s[k] = found[k]
    for k in ("income_multiplier", "bills_increase_pct", "one_off_amount", "one_off_months_spending"):
        s[k] = float(s[k])
    for k in ("account_id", "horizon_months"):
        if s[k] is not None:
            s[k] = int(s[k])
    return s


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


if __name__ == "__main__":
    # Try the translator live:  python -m engine.twist "Account 23595 was laid off, EI 55%"
    import sys
    text = " ".join(sys.argv[1:]) or "Account 23595 loses their job (EI at 55%) and household bills go up 15%."
    try:
        print("AI says:    ", llm_parse(text, None))
    except Exception as e:
        print("AI failed:  ", type(e).__name__, str(e)[:200])
    print("Backup says:", fallback_parse(text, None))
    print("App uses:   ", parse_twist(text, None))
