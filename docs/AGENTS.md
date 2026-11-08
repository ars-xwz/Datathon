# AGENTS.md: Tangerine "Resilience Rewired" (Sheridan Datathon 2026)

Context for coding agents working in this repo. Read this first, then `README.md` (official challenge brief and data dictionary), then `PLAN.md` (requirement IDs, module layout, tests, tasks). When you build something, say which requirement ID it covers.

## Who we are
- Team of 3 students, first datathon, beginner-to-intermediate Python.
- **Explain code simply** and add short comments. Prefer readable pandas over clever one-liners.
- **Do not make product decisions for the team.** Anything listed under "Open decisions" must be asked about, not assumed. Use clearly labelled placeholders if code needs a value to run.
- Hacking ends **Sunday Nov 8, 12:00 PM ET** (Devpost closes). Live judging Sunday 1-2:30 PM.

## The challenge (summary of README.md)
Build a financial resilience engine for real (anonymized) bank customers:
1. **Know the customer:** for any `account_id`, show income, bills/fixed costs, savings buffer, months of runway.
2. **Take a shock:** job loss with EI, higher bills, surprise repair, or a mix; adjustable size.
3. **Make a plan:** a goal plan (e.g. emergency fund) AND a backup plan if the shock hits, from the customer's own numbers.

**Live judging:** a judge picks an `account_id` and reads a twist card ("laid off, EI pays 55% for 6 months, do they make it?" / "furnace repair costs one month of typical spending" / "job loss + household bills up 15% same month"). We run it live and explain in about 3 minutes.
Scoring: **Discovery 35%, Data Use 25%, Communication 25%, Impact 15%.**

## Official definitions (judges pre-computed answers with these; match EXACTLY)
From `data/monthly_summary.csv`, per account:
- **I** = median of `money_in`
- **F** = median of `household_bills + insurance + loan_payments` (display only)
- **S** = median of `money_out`
- **B** = mean of `avg_daily_balance` over the account's **last 6 rows sorted by month**
- **H** = median of `household_bills`
- **P** = `monthly_payment` from `loans.csv` if the loan is still running at end of 2025, else 0

```
buffer_left = B - one_off_costs
gap         = spending_after_shock - income_after_shock
if buffer_left <= 0:  runway = 0
elif gap <= 0:        runway = "no shortfall (120+)"
else:                 runway = min(buffer_left / gap, 120)      # rounded to 1 decimal
```
Job loss EI 55% → income = 0.55 × I. Bills up 15% → spending = S + 0.15 × H. Repair = one month of spending → one_off = S.

## Our workflow (DECIDED)

```
Judge types the twist (or a follow-up) word for word
        │
        ▼
1. TRANSLATE  ── language model turns words into settings (JSON), given the PREVIOUS settings too
        │        └─ fails or >8 sec → backup keyword parser (merges new values into previous settings)
        ▼
2. CHECK      ── code validates settings (sensible ranges)
        ▼
3. SHOW       ── "Here's what I understood" (editable) + short request history
        ▼
4. KNOW       ── official profile (I, F, S, H, B, P) + CUSTOMER TYPE with reason
        ▼
5. SHOCK      ── three runways: (a) today, no shock · (b) after shock = OFFICIAL · (c) after shock + optimizer
        ▼
6. OPTIMIZE   ── cuts on three levers only → runway (c)
        ▼
7. EXPLAIN    ── side-by-side calculation breakdown + one template sentence; goal plan
        ▼
8. EVERYONE   ── same twist run on all 4,500 customers: % under goal after shock vs after optimizer,
                 by type, plus this customer's rank (overall and within type)
```

### Three main features
1. **Agent that remembers requests.** Keeps the current account + settings between questions. A follow-up ("what if bills also go up 15%?") updates only what it mentions.
2. **Customer classification** (first match wins):
   1. **Stabilize first:** any month with `days_below_zero > 0`. Plan: stop going below zero first.
   2. **Pension-protected:** median `pension_in` ≥ 30% of I. A layoff doesn't cut a pension.
   3. **Savings-first:** 0.55 × I > $3,159/month (2026 EI max $729/week × 52 / 12). Cuts often aren't enough; build savings first.
   4. **Trim:** everyone else. Standard optimizer.
3. **Optimizer.** Levers: **cash withdrawals, household bills, other transfers out ONLY.** Not insurance (risky advice in a crisis), not card spending (median $0 for almost all customers). Brute force all combinations of cut levels within limits.
   - Phrase cuts as "lower monthly cash withdrawals by $X". 76% of spending is cash and we can't see what it pays for. Never invent categories like "restaurants".

### Agent rules (the language model never calculates)
Settings schema (anything not mentioned keeps its default, or its previous value for follow-ups):
```python
TWIST_SCHEMA = {
    "account_id":              None,   # if stated
    "income_multiplier":       1.0,    # job loss with EI -> 0.55
    "apply_ei_cap":            False,  # adjusted view only, never the official number
    "bills_increase_pct":      0.0,    # "bills/rent up 15%" -> 15
    "one_off_amount":          0.0,    # "$2,000 repair" -> 2000
    "one_off_months_spending": 0.0,    # "a full month of typical spending" -> 1 (code computes 1 × S)
    "horizon_months":          None,   # "do they make it 6 months?" -> 6 (answer = runway >= 6)
}
```
- Use structured output / function calling; 8-second timeout; then the backup parser.
- CHECK ranges: income_multiplier 0-1.5, bills_increase_pct -50 to 300, one-offs ≥ 0, horizon 1-120.
- Show which parser was used ("Interpreted by: AI / backup").
- Explanations are f-string templates filled with engine output. The model may reword finished text but must not change any number.

### Calculation breakdown (how we explain differences to judges)
Columns: **Today | After shock | After optimizer.** Rows: income, spending, each cut (cash / bills / transfers), monthly shortfall, savings, runway.
- All three columns use the same README formula. **Only the spending row changes between "After shock" and "After optimizer".**
- "After shock" is the judges' number and is never altered.
- One sentence, e.g. "Cutting $1,600/month lowers the shortfall from $3,326 to $1,726, so the same $17,351 lasts 10.1 months instead of 5.2."

### Twist on everyone
- Vectorized version of the same formula over all customers; must equal the single-customer result for every account (test V11).
- A $ one-off applies the same dollars to everyone; a "months of spending" one-off scales per customer.

## Findings from exploration (keep numbers consistent; recompute when settings change)
- Types: Savings-first 2,348 · Trim 1,127 · Pension-protected 737 · Stabilize first 288.
- Under 6 months on EI (official 55%): Stabilize first 75% · Savings-first 54% · Trim 9% · Pension-protected 1% · overall 35%.
- 74% of customers look safe today (spend ≤ income); 21% of those wouldn't last 6 months after a layoff.
- With the EI cap, working customers under 6 months: 42% → 61%.
- 27 of 76 loan defaulters went below zero BEFORE taking the loan; none of 606 good borrowers ever went below zero. (Stabilize-first is defined by below-zero months, so "all Stabilize-first loan customers defaulted" is partly by definition; use the before-the-loan number.)
- 76% of all spending is cash withdrawals.
- With PLACEHOLDER optimizer settings (moderate limits, max cuts): under 6 months on EI goes 35% → 8% overall; Stabilize first stays at 40%.
- "What people cut when income drops" didn't work (account spending drops to zero with income). Don't use it.

## Open decisions (ASK, don't assume)
- Cut limits: same for every type or per type; gentle (cash 20% / bills 5% / transfers 25%), moderate (30/10/50), strong (50/20/100), or user-selectable. Placeholder: moderate.
- Optimizer aim: longest runway with max allowed cuts / smallest cuts that reach the goal / both. Placeholder: max allowed cuts.
- Step size (5% or 10%), meaning of "best" and tie-break (only matters if aim = smallest cuts).
- Goal when the twist gives none (e.g. furnace twist).
- Goal plan: fund size, share of surplus to save, what to say when it would take years, where it appears on screen. Placeholder: 3 × S, 50% of surplus.
- App format and LLM provider.

## Data (in `data/`; see README.md)
- `monthly_summary.csv` (185k rows): main file. In: `cash_deposits`, `transfers_in`, `pension_in`, `interest_in`. Out: `household_bills`, `insurance`, `loan_payments`, `bank_fees`, `cash_withdrawals_genuine`, `card_withdrawals`, `transfers_out_other`. Balances: `month_end_balance`, `min_balance`, `avg_daily_balance`, `days_below_zero`.
- `loans.csv` (682): `status` A/B/C/D, `defaulted`. Also `accounts`, `clients`, `dispositions`, `cards`, `districts`, `standing_orders`.
- `transactions.csv` (102.6 MB) is NOT in git (over GitHub's 100 MB limit) and isn't needed.
- Districts are from the original non-Canadian dataset. Canadian sources only size shocks and must be cited.

## Submission checklist (Devpost)
Demo video (2-3 min; aim for 2) · public repo · write-up (what it does + biggest finding) · links to every outside source · credit PKDD'99 Financial dataset (https://relational.fel.cvut.cz/dataset/Financial) and canada.ca EI pages · all 3 members listed.
