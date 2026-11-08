"""The whole workflow in one function (PLAN.md 2.2). OWNER: Angela. The UI only calls run()."""
from engine.twist import parse_twist
from engine.metrics import get_profile
from engine.customer_types import classify
from engine.shocks import apply_shock
from engine.optimizer import optimize
from engine.goalplan import goal_plan
from engine.everyone import run_on_everyone
from engine.explain import explain

def understand(text, session):
    """Steps 1-3: translate + check. The UI shows the result for confirmation/editing."""
    return parse_twist(text, previous=session.settings)

def run(settings, session, text="", parser_used="manual"):
    """Steps 4-8 after the user confirms settings. Returns everything the UI needs."""
    session.update(text, settings, parser_used)
    aid = settings["account_id"]
    p = get_profile(aid)
    ctype, reason = classify(aid)
    shocked = apply_shock(p, settings)
    opt = optimize(p, shocked, settings, ctype)
    goal = goal_plan(p, ctype)
    crowd = run_on_everyone(settings, aid)
    view = explain(p, ctype, reason, shocked, opt, goal, crowd)
    return {"profile": p, "type": ctype, "reason": reason, "shocked": shocked, "opt": opt,
            "goal": goal, "crowd": crowd, "view": view, "parser_used": parser_used}
