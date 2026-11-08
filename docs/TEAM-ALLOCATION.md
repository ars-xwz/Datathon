@AGENTS.md
@PLAN.md

## Team allocation (who owns what)

Each person works on their own branch and only edits the files they own. Before editing a file, check the owner below. If the person you're working with doesn't own it, stop and tell them to ask the owner.

| Person | Steps | Files they own | Branch |
|---|---|---|---|
| **Angela** | 1 Ask, 2 Confirm (agent) | `engine/twist.py`, `engine/session.py`, `pipeline.py` | `step12-agent` |
| **Angela** | 6 Everyone | `engine/everyone.py` | `step6-everyone` |
| **Basmah** | 3 Customer | `engine/metrics.py`, `engine/customer_types.py` | `step3-customer` |
| **Basmah** | Screen for all 6 steps | `app.py`, `engine/explain.py` | `screen` |
| **Arshiya** | 4 Shock, 5 Plan (optimizer) | `engine/shocks.py`, `engine/optimizer.py`, `engine/goalplan.py` | `step45-shock-plan` |

Shared files (`AGENTS.md`, `PLAN.md`, `CLAUDE.md`, `README.md`, `requirements.txt`): Angela edits these. Others ask her. Exception: whoever adds a library adds it to `requirements.txt` in their PR and says so.

Tests: each person writes tests for their own files (`tests/test_customer.py` Basmah, `tests/test_plan.py` Arshiya, `tests/test_twist.py` and `tests/test_everyone.py` Angela). `tests/test_smoke.py` must keep passing for everyone.

## Pull request order
1. **Step 3** (Basmah): merge first; everything uses the customer numbers. Must also expose the whole customer table (e.g. `all_customers()`) for step 6.
2. **Steps 1-2** (Angela): any time, independent.
3. **Steps 4-5** (Arshiya): after #1. Write the shock and optimizer math so it can also run on many customers at once (step 6 reuses it).
4. **Step 6** (Angela): after #1 and #3. Reuses Basmah's table and Arshiya's functions; never rewrites their math. Test V11: everyone-runway equals single-customer runway for every account.
5. **Screen** (Basmah): open as a draft PR early, merge last.

After any merge to `main`, everyone runs `git pull origin main` on their branch and starts a fresh Claude Code session.

## Check values (from the prototype; tiny rounding differences are fine)
- Account 23595: I 6,802.4 · S 6,746.2 · F 2,713.4 · H 2,141.4 · B 17,350.5 · P 0 · cash 3,681.2 · bills 2,141.4 · transfers 562.6 · Savings-first
- Account 55447: P 3,658.58
- Type counts: Savings-first 2,348 · Trim 1,127 · Pension-protected 737 · Stabilize first 288
- 23595, job loss 55% + bills +15%, moderate limits: after shock 5.2 months; aim "max" cuts cash $1,104 / bills $214 / transfers $281 → 10.1 months; aim "cheapest" (goal 6) about $411 → 6.0 months
- Goal plan 23595: "Save $28/month for 103 months to reach $20,238"
- Everyone, same twist, goal 6: 38.7% under 6 months after shock → 11% with optimizer; by type Stabilize first 76→42, Pension-protected 2.6→0, Savings-first 58.9→14.5, Trim 10.6→3.1; 23595 rank 66.7% (48.8% within type)

## Claude Code rules
- Only edit files owned by the person you're working with. Never edit a teammate's file without them confirming the owner agreed.
- Do not change the dict keys a function returns (the CONTRACT in each docstring) without the user confirming the team agreed.
- Leave `# PLACEHOLDER` values alone unless the user gives the team's decision.
- Run `python tests/test_smoke.py` before suggesting a commit.
- Do not run `/init` or rewrite this file. Personal instructions go in `CLAUDE.local.md` (gitignored).
