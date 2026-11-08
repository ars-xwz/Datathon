"""R9: calculation breakdown + sentences. OWNER: Basmah. STATUS: done.

Turns the engine's numbers into what the screen shows. It never calculates anything new
except formatting and the monthly shortfall (spending - income), which is the same
subtraction the README runway formula uses.
"""


def money(x):
    """$6,802 style. Negative amounts get a real minus sign: -$1,104."""
    return f"-${abs(x):,.0f}" if x < 0 else f"${x:,.0f}"


def fmt_rw(r):
    """Runway for display: '5.2 months', or the README string 'no shortfall (120+)'."""
    return r if isinstance(r, str) else f"{r} months"


def shortfall(spending, income):
    """Monthly shortfall for display: the gap the savings must cover, or 'none'."""
    gap = spending - income
    return money(gap) if gap > 0 else "none"


def explain(p, ctype, reason, shocked, opt, goal, crowd):
    """CONTRACT: returns dict with 'table' (list of rows: label, today, after_shock, after_opt)
    and 'sentences' (list of strings). Every number comes from the inputs.
    Columns: Today | After shock (official, never altered) | After optimizer.
    Only the spending row (and so the shortfall and runway) differs between the last two."""
    c = opt["cuts"]
    spend_opt = shocked["spending"] - opt["total_cut"]
    table = [
        ("Income", money(p["I"]), money(shocked["income"]), money(shocked["income"])),
        ("Spending", money(p["S"]), money(shocked["spending"]), money(spend_opt)),
        ("  cut: cash withdrawals", "", "", money(-c["cash"])),
        ("  cut: household bills", "", "", money(-c["bills"])),
        ("  cut: transfers out", "", "", money(-c["transfers"])),
        ("Monthly shortfall", shortfall(p["S"], p["I"]),
         shortfall(shocked["spending"], shocked["income"]), shortfall(spend_opt, shocked["income"])),
        ("Savings", money(p["B"]), money(shocked["buffer_left"]), money(shocked["buffer_left"])),
        ("Runway", fmt_rw(shocked["runway_today"]), fmt_rw(shocked["runway_shock"]), fmt_rw(opt["runway_opt"])),
    ]

    # one sentence that explains the difference between "after shock" and "after optimizer"
    gap_shock = shocked["spending"] - shocked["income"]
    gap_opt = spend_opt - shocked["income"]
    if gap_shock <= 0:
        why = "Income still covers spending after this shock, so no cuts are needed."
    elif opt["total_cut"] <= 0:
        why = "No cuts are possible on cash withdrawals, bills or transfers for this customer."
    else:
        new_gap = money(gap_opt) if gap_opt > 0 else "nothing"
        why = (f"Cutting {money(opt['total_cut'])}/month lowers the shortfall from {money(gap_shock)} "
               f"to {new_gap}, so the same {money(shocked['buffer_left'])} lasts "
               f"{fmt_rw(opt['runway_opt'])} instead of {fmt_rw(shocked['runway_shock'])}.")
    if opt.get("reached") is False and opt.get("extra_savings_needed", 0) > 0:
        why += (f" Even with the biggest allowed cuts they don't reach {crowd['horizon']} months: "
                f"they'd need {money(opt['extra_savings_needed'])} more in savings.")

    sentences = [
        f"Customer type: {ctype}. {reason}",
        f"After the shock: {fmt_rw(shocked['runway_shock'])} (official). "
        f"With the plan: {fmt_rw(opt['runway_opt'])}.",
        why,
        f"Across all customers, this twist puts {crowd['pct_under_shock']}% under {crowd['horizon']} months; "
        f"{crowd['pct_under_opt']}% after the optimizer.",
        f"Goal plan: {goal['message']}",
    ]
    return {"table": table, "sentences": sentences}
