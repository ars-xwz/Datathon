"""R10: run the same twist on all 4,500 customers. OWNER: Angela. STATUS: done.

Reuses the SAME math as steps 3-5, so the numbers can't disagree with the single customer (test V11):
  metrics.all_customers()        Basmah's one-row-per-customer table (with 'type')
  shocks.shock_many()            Arshiya's shock math for every customer at once
  optimizer.optimize_many()      Arshiya's optimizer for every customer at once (per-type limits)
  shocks.ei_cap_many()           Arshiya's EI-cap adjusted view (R11), labelled, never the official number
"""
from engine.metrics import all_customers
from engine.customer_types import TYPES
from engine.shocks import shock_many, ei_cap_many, goal_months
from engine.optimizer import optimize_many


def everyone_table(settings):
    """One row per customer: type, runway_shock, runway_opt, runway_capped (numbers; 120 = no shortfall)."""
    table = all_customers()
    shocked = shock_many(table, settings)
    opt = optimize_many(table, shocked, settings)
    capped = ei_cap_many(table, settings)
    out = table[["type"]].copy()
    out["runway_shock"] = shocked["runway_shock"]
    out["runway_opt"] = opt["runway_opt"]
    out["runway_capped"] = capped["runway_capped"]
    return out


def _pct(mask):
    """Share of True values as a percent with 1 decimal (0.0 for an empty group)."""
    return round(100 * float(mask.mean()), 1) if len(mask) else 0.0


def run_on_everyone(settings, account_id=None):
    """CONTRACT: returns dict with
      horizon            the goal in months used for "under the goal"
      pct_under_shock    % of all customers whose official runway after the shock is under the goal
      pct_under_opt      same, after the optimizer
      by_type            {type: (pct_shock, pct_opt)}
      rank_longer_pct    % of all customers whose runway after the shock is LONGER than this customer's
      rank_in_type_pct   same, among customers of this customer's type
    Extra keys (added, nothing removed): type_counts {type: n}, n_customers,
      pct_under_capped (EI-cap adjusted view, R11; label it as not official), account_type."""
    goal = goal_months(settings)
    t = everyone_table(settings)

    by_type, type_counts = {}, {}
    for name in TYPES:
        g = t[t["type"] == name]
        by_type[name] = (_pct(g["runway_shock"] < goal), _pct(g["runway_opt"] < goal))
        type_counts[name] = int(len(g))

    out = {"horizon": goal,
           "pct_under_shock": _pct(t["runway_shock"] < goal),
           "pct_under_opt": _pct(t["runway_opt"] < goal),
           "pct_under_capped": _pct(t["runway_capped"] < goal),
           "by_type": by_type, "type_counts": type_counts, "n_customers": int(len(t)),
           "rank_longer_pct": None, "rank_in_type_pct": None, "account_type": None}

    if account_id is not None and int(account_id) in t.index:
        me = t.loc[int(account_id)]
        same = t[t["type"] == me["type"]]
        out["rank_longer_pct"] = _pct(t["runway_shock"] > me["runway_shock"])
        out["rank_in_type_pct"] = _pct(same["runway_shock"] > me["runway_shock"])
        out["account_type"] = me["type"]
    return out
