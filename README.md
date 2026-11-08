# Delta-or-Die · Will they make it?

**Tangerine track "Resilience Rewired" · Sheridan Datathon 2026 (Nov 7–8)**

A financial resilience agent for 4,500 real, anonymized bank customers. Type a customer and a "what if" in plain words, such as a layoff on EI, higher bills or a surprise repair. The app shows how many months their savings would last before and after the shock, builds a personal plan that stretches those savings, and runs the same twist on every customer to show who is most at risk.

Every number comes from our Python code using the challenge's official formulas. The language model only reads the twist and turns it into settings; it never calculates.

---

## What it does

The screen walks through six cards:

| # | Card | What it shows |
|---|---|---|
| 1 | **Read the twist** | Type the twist exactly as written, or pick an example. |
| 2 | **Here's what I understood** | The settings the agent read (account, income after the shock, bills change, one-off cost, goal in months), who read them (the AI or the backup parser), and sliders to fix anything before running. |
| 3 | **Customer** | Runway today, before any shock; income, spending, fixed costs, household bills and savings; the customer's type and why. |
| 4 | **Shock** | The **official runway after the shock** (the number judges check), whether they make the goal, what the shock changed, and an EI-cap adjusted view, clearly labelled as not official. |
| 5 | **Plan** | The backup plan: specific monthly cuts to cash withdrawals, household bills and other transfers, and the runway they buy. A sentence explains the difference. Also an emergency-fund goal plan and advice for the customer's type. |
| 6 | **Everyone** | The same twist on all 4,500 customers: % who fall short after the shock vs with the plan, by type, and where this customer ranks. |

**The globe:** each dot is one customer, coloured by type and grouped into one "continent" per type. Within a type, dots are sorted by how many months of spending their savings cover. Position is not geography. From the Shock card on, customers whose runway is under the goal sink and turn grey. Switching to "With the plan" shows who the plan rescues. Clicking a dot loads that customer.

**Memory:** follow-ups such as "What if it's 9 months instead?" keep the account and the rest of the twist, and change only what they mention. Naming a different account starts a fresh twist. Past requests can be reloaded from the history.

---

## Findings

Data: 4,500 accounts, 682 loans. Shock: layoff with EI at 55% of usual income, goal 6 months, unless stated.

**1. An overdraft before the loan predicts default.**
All **27** borrowers who went below zero before taking out their loan defaulted (27 of 27). Among the other 655 borrowers, **7.5%** (49) did. None of the **606** borrowers who repaid ever went below zero. The warning sign is in data the bank already has before it lends. Our engine flags these customers as "Stabilize first".

**2. Looking safe today is not the same as being resilient.**
**74%** of customers spend less than they earn, so on a normal month they look fine. Yet **699** of them (21%) would run out of savings within 6 months of a layoff on EI. That is why the app always shows the runway after a shock next to the runway today.

**3. The official EI rule makes higher earners look safer than they are.**
The challenge assumes EI pays 55% of income, but real EI stops at **$729/week (about $3,159/month in 2026)**. For the 2,348 Savings-first customers, the rule overstates EI by a median of **$3,737/month**.

| Customers | Under 6 months, official 55% rule | Under 6 months, real EI cap |
|---|---|---|
| Savings-first | 54% | 83% |
| All working customers (not Pension-protected) | 42% | 61% |

We keep the official number as the main answer, so it matches the judges', and show the capped one next to it, labelled.

**4. What the plan fixes, and who it can't save.**
Cutting only cash withdrawals, household bills and other transfers out, the share who can't last 6 months falls from **35.1% to 6.5%**. Even with the strongest cuts allowed, **1 in 5 Stabilize-first customers (20.1%)** still falls short: cutting spending isn't enough for them.

With household bills also up 15%:

| Type | Customers | Under 6 months after the shock | With the plan |
|---|---|---|---|
| Stabilize first | 288 | 76.0% | 22.2% |
| Pension-protected | 737 | 2.6% | 0.4% |
| Savings-first | 2,348 | 58.9% | 14.5% |
| Trim | 1,127 | 10.6% | 3.1% |
| **Everyone** | 4,500 | **38.7%** | **9.8%** |

**Supporting facts**
- **76%** of all spending is cash withdrawals. The bank can't see what that cash pays for, so plans say "lower monthly cash withdrawals by $X" instead of guessing categories like restaurants.
- Emergency fund (3 months of spending): **2,526** customers already have one, **565** could build it within 2 years by saving half their monthly surplus, **541** would take longer, and **868** have no surplus to save from.
- Furnace twist (a repair costing one month of spending): **181** customers would have no savings left, and **8.7%** would fall under 6 months of runway.

**Caveats:** the overdraft finding rests on 27 borrowers, so it is a strong signal in this data, not a proven rule. The optimizer limits and goal-plan settings are our team's choices (see Settings); the numbers above use the settings currently in the code.

---

## How it works

### Official numbers (match the challenge exactly)
From `data/monthly_summary.csv`, per account:

| | Definition |
|---|---|
| I (income) | median of `money_in` |
| S (spending) | median of `money_out` |
| F (fixed costs) | median of `household_bills + insurance + loan_payments` |
| H (household bills) | median of `household_bills` |
| B (savings buffer) | mean of `avg_daily_balance` over the account's last 6 months |
| P (loan payment) | `monthly_payment` from `loans.csv` if the loan is still running (status C or D), else 0 |

**Runway** = (savings − one-off cost) ÷ (spending after shock − income after shock), capped at 120 months. If savings are gone, runway is 0. If income still covers spending, it's "no shortfall (120+)".
**Shocks:** a layoff with EI at 55% means income = 0.55 × I. Bills up 15% means spending = S + 0.15 × H. A repair worth one month of spending means a one-off cost of S.

### Customer types (first match wins)
1. **Stabilize first:** the balance went below zero in any month.
2. **Pension-protected:** pension is 30% or more of income (a layoff doesn't cut a pension).
3. **Savings-first:** 55% of income is above the 2026 EI maximum ($3,159/month).
4. **Trim:** everyone else.

Counts: Savings-first 2,348 · Trim 1,127 · Pension-protected 737 · Stabilize first 288.

### The plan (optimizer)
- **Levers:** cash withdrawals, household bills, other transfers out. Insurance is left out (cutting it during a crisis is risky advice), and card spending is left out (it's $0 for almost every customer).
- **Limits by type** (cash / bills / transfers): Stabilize first 50% / 20% / 100% · Savings-first and Trim 30% / 10% / 50% · Pension-protected 20% / 5% / 25%.
- **Search:** every combination of cuts in 5% steps (60 to 1,155 combinations per customer), keeping the one with the longest runway; ties go to the fewest dollars cut. If even the biggest allowed cuts can't reach the goal, it reports the extra savings needed.
- **Speed:** numpy runs each combination for all 4,500 customers at once, about a million small calculations, which takes well under a second.
- **Goal plan:** an emergency fund of 3 months of spending, saving half the monthly surplus.

### The agent
1. **Translate:** the AI (Claude Haiku via the Anthropic API, or OpenAI) returns only the settings the twist mentions, as structured JSON. If there's no key, no internet, no answer within 8 seconds or an out-of-range answer, a backup keyword parser is used instead. The backup parser handles 34 tested phrasings, including "let go", "income falls 30%", "bills double", "six months" and "half a year".
2. **Check:** the settings are validated (sensible ranges, an account is named).
3. **Show:** "Here's what I understood", editable before running.
4. **Calculate:** our Python engine does every number.
5. **Explain:** template sentences filled with the engine's numbers.

Memory lives in our code, not the AI: follow-ups merge into the previous settings.

---

## Run it

Needs Python 3.10+ and two libraries. The app itself uses only Python's built-in web server.
```
git clone https://github.com/ars-xwz/Datathon
cd Datathon
python -m pip install -r requirements.txt
python app.py
```
Then open **http://localhost:8000**. Press Ctrl+C in the terminal to stop.

**Optional: the AI translator.** Create a file named `.env` next to `app.py`:
```
ANTHROPIC_API_KEY=sk-ant-...
```
(If your key isn't tied to a workspace, also add `ANTHROPIC_WORKSPACE_ID=...`. For OpenAI, use `OPENAI_API_KEY=...` and `LLM_MODEL=...`.) `.env` is in `.gitignore`, so it is never committed. Without it, the app uses the backup parser.

Try the AI on its own:
```
python -m engine.twist "Account 23595 gets let go and rent creeps up 15%"
```

**Command-line demo:** `python demo.py`

**Tests:**
```
python tests/test_smoke.py
python tests/test_customer.py
python tests/test_twist.py      # 34 judge-style phrasings, never calls the real AI
python tests/test_ai.py         # AI translator with fake answers (works offline)
python tests/test_everyone.py   # everyone-numbers match single-customer numbers
python tests/test_plan.py       # slow: checks the optimizer customer by customer
```

**Check values** (account 23595, layoff EI 55% + bills +15%): income $6,802 · spending $6,746 · savings $17,351 · runway today: no shortfall · after the shock: **5.2 months** · with the plan: **10.1 months** (cuts $1,104 cash, $214 bills, $281 transfers) · everyone: 38.7% → 9.8%.

---

## Project structure

```
app.py                 web server: serves the page, answers its requests with the engine
web/index.html         the screen (six cards, globe, How it works, Findings)
pipeline.py            the whole workflow: understand() then run()
engine/
  metrics.py           official customer numbers + runway formula (one table for all customers)
  customer_types.py    the four customer types
  shocks.py            shock math, one customer or everyone; EI-cap view
  optimizer.py         cut search, one customer or everyone; per-type limits; type advice
  goalplan.py          emergency-fund plan
  everyone.py          the same twist on all 4,500 customers
  twist.py             AI translator + backup parser + validation
  session.py           memory of the current twist + history
  explain.py           breakdown table and sentences
tests/                 tests for each part
data/                  the challenge CSVs (transactions.csv is not included: over GitHub's 100 MB limit, and not needed)
demo.py                command-line demo
```

---

## Settings and assumptions

| Setting | Value | Where |
|---|---|---|
| Default goal when a twist gives none | 6 months | `engine/shocks.py` (`DEFAULT_HORIZON`) |
| Optimizer aim | longest runway (`"max"`); `"cheapest"` also built | `engine/optimizer.py` (`AIM`) |
| Cut limits | by type, see above | `engine/optimizer.py` (`LIMITS_BY_TYPE`) |
| Cut step | 5% | `engine/optimizer.py` (`STEP`) |
| Emergency fund | 3 months of spending, saving 50% of surplus | `engine/goalplan.py` |
| EI cap (adjusted view only) | $729/week × 52 ÷ 12 ≈ $3,159/month | `engine/customer_types.py` (`EI_MAX`) |
| Pension threshold | 30% of income | `engine/customer_types.py` |

Treating `money_in` as insurable earnings for the EI cap is an assumption; the official number never uses the cap.

---

## Devpost write-up notes

**Inspiration:** most budgeting advice treats everyone the same. Tangerine's challenge asked who survives a shock and what would help. We wanted the answer to be personal, and to show the bank where the risk sits across all its customers.

**What it does:** see "What it does" above.

**How we built it:** Python and pandas for the engine, numpy for the all-customer optimizer, a standard-library web server, and one HTML page with a canvas globe. Claude Haiku turns judges' words into settings through structured output; a keyword parser is the fallback. We split the work by step (agent, customer numbers, shock and plan, everyone, screen), agreed on function contracts first, and tested each part against hand-checked values.

**Challenges:**
- Matching the official formulas exactly while also showing a more realistic EI-capped view without confusing the two.
- 76% of spending is untracked cash, so the plan can't name spending categories.
- Making the AI safe for live judging: it never does math, and falls back to the parser.
- Keeping "everyone" and "one customer" numbers identical (tested on every account).

**Accomplishments:** a live engine that answers any account and twist in under a second; findings that tie directly to the engine (customer types and plan limits come from what the data showed); the globe that shows a twist hitting all 4,500 customers at once.

**What we learned:** an average or a monthly surplus hides fragility; overdraft history is a strong early warning; small modelling choices (EI cap, cut limits) change the story, so they must be stated.

**What's next:** test the overdraft signal on more loans; add income-side levers; use real spending categories if the bank has them; let customers set their own cut limits.

---

## Sources and credits

- **Data:** PKDD'99 Discovery Challenge Financial dataset (real anonymized bank data), CTU Prague Relational Dataset Repository: https://relational.fel.cvut.cz/dataset/Financial
- **EI maximum (2026):** Government of Canada, maximum insurable earnings for 2026: https://www.canada.ca/en/employment-social-development/programs/ei/ei-list/ei-employers/premium-reduction-program/2026-maximum-insurable-earnings.html
- **EI regular benefits:** Government of Canada: https://www.canada.ca/en/services/benefits/ei/ei-regular-benefit.html
- **AI:** Claude Haiku via the Anthropic API (optional; only translates the twist into settings).

## Team
Angela (agent, parser, everyone) · Arshiya (shock, optimizer, goal plan) · Basmah (customer numbers, customer types, screen and design)
