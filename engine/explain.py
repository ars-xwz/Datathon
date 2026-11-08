"""R9: calculation breakdown + sentences. OWNER: Frontend teammate. STATUS: STUB."""

def fmt_rw(r):
    return r if isinstance(r, str) else f"{r} months"

def explain(p, ctype, reason, shocked, opt, goal, crowd):
    """CONTRACT: returns dict with 'table' (list of rows: label, today, after_shock, after_opt)
    and 'sentences' (list of strings). Every number comes from the inputs."""
    c = opt["cuts"]
    table = [
        ("Income", p["I"], shocked["income"], shocked["income"]),
        ("Spending", p["S"], shocked["spending"], shocked["spending"] - opt["total_cut"]),
        ("  cut: cash withdrawals", "", "", -c["cash"]),
        ("  cut: household bills", "", "", -c["bills"]),
        ("  cut: transfers out", "", "", -c["transfers"]),
        ("Savings", p["B"], shocked["buffer_left"], shocked["buffer_left"]),
        ("Runway", fmt_rw(shocked["runway_today"]), fmt_rw(shocked["runway_shock"]), fmt_rw(opt["runway_opt"])),
    ]
    sentences = [
        f"Customer type: {ctype}. {reason}",
        f"After the shock: {fmt_rw(shocked['runway_shock'])} (official). With the plan: {fmt_rw(opt['runway_opt'])}.",
        f"Across all customers, this twist puts {crowd['pct_under_shock']}% under {crowd['horizon']} months; "
        f"{crowd['pct_under_opt']}% after the optimizer.",
        f"Goal plan: {goal['message']}",
    ]
    return {"table": table, "sentences": sentences}
