"""The whole workflow in one function (PLAN.md 2.2). OWNER: Angela. The UI only calls run()."""
from engine.twist import parse_twist, validate
from engine.metrics import get_profile
from engine.customer_types import classify
from engine.shocks import apply_shock
from engine.optimizer import optimize
from engine.goalplan import goal_plan
from engine.everyone import run_on_everyone
from engine.explain import explain

def understand(text, session):
    """Steps 1-2: translate. Returns (settings, parser_used). Never raises for a missing account:
    the UI shows the settings as editable fields (and engine.twist.problems(settings) if any)."""
    return parse_twist(text, previous=session.settings)

def run(settings, session, text="", parser_used="manual"):
    """Steps 3-6 after the user confirms settings. Returns everything the UI needs.
    Raises ValueError with a plain-English message if the settings or account are invalid;
    the UI should catch it and show the message. Only successful runs go into the history."""
    validate(settings)
    aid = int(settings["account_id"])
    p = get_profile(aid)
    ctype, reason = classify(aid)
    shocked = apply_shock(p, settings)
    opt = optimize(p, shocked, settings, ctype)
    goal = goal_plan(p, ctype)
    crowd = run_on_everyone(settings, aid)
    view = explain(p, ctype, reason, shocked, opt, goal, crowd)
    session.update(text, settings, parser_used)
    return {"profile": p, "type": ctype, "reason": reason, "shocked": shocked, "opt": opt,
            "goal": goal, "crowd": crowd, "view": view, "parser_used": parser_used}
