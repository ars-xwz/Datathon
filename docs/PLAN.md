# PLAN.md: Requirements, Design, Verification, Implementation
Tangerine "Resilience Rewired" · Sheridan Datathon 2026 · Team of 3

Every requirement has an ID. Each design module lists the requirements it covers, and each test lists the requirement it checks. Nothing outside the requirements gets built before the MVP is done.

Priority: **MUST** = needed to be judged well. **SHOULD** = after MVP. **COULD** = only if time is left.
Roles A / B / C are placeholders: the team assigns people.

---

## 1. Requirements

### 1.1 Functional requirements

| ID | Priority | Requirement | Acceptance criteria |
|---|---|---|---|
| **R1** | MUST | **Customer profile.** For any `account_id`, compute I, F, S, H, B, P exactly per README. | Matches hand calculation (V1) for 3 accounts to 1 decimal. Runs for all 4,500 accounts. |
| **R2** | MUST | **Customer type.** Exactly one type, first match wins: Stabilize first → Pension-protected → Savings-first → Trim (rules in AGENTS.md). Show the reason. | Counts: Savings-first 2,348 · Trim 1,127 · Pension-protected 737 · Stabilize first 288. |
| **R3** | MUST | **Shock settings.** Income multiplier, bills increase %, one-off $, one-off in months of spending, horizon; any combination; all editable. | Every README twist can be entered and edited. |
| **R4** | MUST | **Three runways.** (a) today, no shock; (b) after shock = official README number; (c) after shock + optimizer cuts. Horizon verdict (runway ≥ horizon) for (b) and (c). | (a) and (b) match hand calculation for each README twist on 3 accounts. |
| **R5** | MUST | **Optimizer.** Levers: cash withdrawals, household bills, other transfers out only. Brute force all cut combinations within limits. Aim and limits per open decisions D-1, D-2. Reports when the goal can't be reached and the extra savings needed. | Chosen cuts give runway (c); brute-force check finds nothing better under the chosen aim (V4). |
| **R6** | MUST | **Goal plan.** Emergency-fund plan from the customer's own numbers; handles "already funded" and "no surplus". Settings per D-5. | A plan for every account; no negative or infinite months shown. |
| **R7** | MUST | **Agent pipeline.** Translate → check → show (editable) → calculate → explain. LLM only translates; backup keyword parser if LLM fails or takes >8 s. | All README twists produce correct settings with both parsers. Works with Wi-Fi off (V6). |
| **R8** | MUST | **Agent memory.** Keeps current account + settings; follow-ups change only what they mention. Shows a short request history. | Scripted follow-up sequence gives expected settings at each step (V12). |
| **R9** | MUST | **Calculation breakdown.** Side-by-side Today / After shock / After optimizer: income, spending, each cut, shortfall, savings, runway. Only the spending row differs between (b) and (c). One template sentence explaining the difference. | Every runway in the table equals savings ÷ shortfall from the same table (V8). |
| **R10** | MUST | **Twist on everyone.** Same twist on all customers: % under the horizon after shock vs after optimizer, overall and by type; this customer's rank overall and within type. | Under 2 s. Equals single-customer result for every account (V11). |
| **R11** | SHOULD | **EI-cap adjusted view.** Labelled, shown next to the official number, never replaces it. | Shown and labelled for a Savings-first account. |
| **R12** | SHOULD | **Discovery summary** (pitch/write-up numbers): types, "looks safe today" share, before-the-loan overdraft signal. | Numbers match AGENTS.md findings (recomputed with final settings). |
| **R13** | COULD | Balance timeline chart for (b) and (c). | Lines hit zero at the runway month. |
| **R14** | COULD | Overdraft early-warning flag. | Shows for Stabilize-first accounts with a loan. |

### 1.2 Non-functional requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| **N1** | All numbers come from code; the LLM never calculates. | Code review: only validated settings come from the LLM. |
| **N2** | Paste twist → answer under 30 s; calculation alone under 2 s (including "everyone"). | Timed on 5 runs (V9). |
| **N3** | No crash on any account or valid settings. | V5, V7 pass. |
| **N4** | The official runway (b) is always visible and unaltered. | Visual check. |
| **N5** | Works offline except the LLM step. | V6. |
| **N6** | Readable code; every function has a one-line docstring. | Review. |

### 1.3 Submission requirements

| ID | Requirement | Due |
|---|---|---|
| **S1** | Devpost draft + Tangerine track + 3 members | ✅ Done |
| **S2** | Demo video (aim for 2 min) | Sun 12 PM |
| **S3** | Public code repo (without `transactions.csv`) | Sun 12 PM |
| **S4** | Write-up: what it does + biggest finding | Sun 12 PM |
| **S5** | Sources: PKDD'99 dataset credit, canada.ca EI pages | Sun 12 PM |
| **S6** | At least one member at the judging table | Sun 1-2:30 PM |

### 1.4 Open decisions (team decides; code uses labelled placeholders until then)

| ID | Decision | Options | Placeholder |
|---|---|---|---|
| **D-1** | Cut limits | Same for all types or per type; gentle 20/5/25 · moderate 30/10/50 · strong 50/20/100 (cash/bills/transfers %); or user-selectable | Moderate, same for all |
| **D-2** | Optimizer aim | Longest runway with max allowed cuts · smallest cuts to reach the goal · both | Max allowed cuts |
| **D-3** | Step size, "best", tie-break | 5% or 10%; fewest dollars / fewest changes; tie-break rule (only if D-2 uses smallest cuts) | 5%, fewest dollars, fewest levers |
| **D-4** | Goal when the twist has none | Fixed default · pre-shock runway · ask the judge | 6 months |
| **D-5** | Goal plan | Fund size, share of surplus, wording when it takes years, placement on screen | 3 × S, 50% of surplus |
| **D-6** | App format + LLM provider | — | — |

Decided: three main features; workflow; three runways; levers = cash, bills, transfers; twist on everyone; calculation breakdown.

---

## 2. Design

### 2.1 Module layout

```
data/                 CSVs (transactions.csv git-ignored)
engine/
  data.py        load once, build customer table for all accounts (cached)   → R1, R10
  metrics.py     official I, F, S, H, B, P; runway()                          → R1, R4
  customer_types.py classify() → type + reason                                   → R2
  shocks.py      apply_shock() → runways (a), (b); EI-cap view                → R3, R4, R11
  optimizer.py   optimize() → cuts + runway (c), or "can't reach" + extra $   → R5
  goalplan.py    goal_plan()                                                  → R6
  everyone.py    run_on_everyone() vectorized; rank                           → R10
  twist.py       llm_parse(), fallback_parse(), validate(), merge()           → R7, R8
  session.py     current settings + request history                          → R8
  explain.py     breakdown table + template sentences                         → R9
app.py           user interface (D-6)
tests/           golden values, twist phrasings, follow-ups, bulk, everyone=single
```

### 2.2 Workflow

```
Judge types the twist (or a follow-up) word for word
        │
        ▼
1. TRANSLATE  ── LLM → settings (JSON), given previous settings
        │        └─ fails or >8 sec → backup keyword parser, merged into previous settings
        ▼
2. CHECK      ── validate ranges
        ▼
3. SHOW       ── "Here's what I understood" (editable) + request history
        ▼
4. KNOW       ── profile + customer type with reason
        ▼
5. SHOCK      ── runways (a) today · (b) after shock [official] · (c) after optimizer
        ▼
6. OPTIMIZE   ── three levers → runway (c)
        ▼
7. EXPLAIN    ── breakdown table + one sentence; goal plan
        ▼
8. EVERYONE   ── same twist on all customers; by type; this customer's rank
```

### 2.3 Key interfaces

```python
settings, parser_used = parse_twist(text, previous=session.settings)   # R7, R8
session.update(text, settings)                                          # R8
p = get_profile(account_id)            # I, F, S, H, B, P, lever medians (cash, bills, transfers)
ctype, reason = classify(account_id)
shocked = apply_shock(p, settings)     # income, spending, buffer_left, runway_today, runway_shock, verdict
opt = optimize(p, shocked, settings, ctype)   # cuts {cash, bills, transfers}, runway_opt, reached?, extra_savings
goal = goal_plan(p, ctype)
crowd = run_on_everyone(settings)      # pct_under_shock, pct_under_opt (overall + by type), rank, rank_in_type
view = explain(p, ctype, shocked, opt, goal, crowd)   # breakdown table + sentences
```

### 2.4 Shock math (official, used in every column)
```
income   = income_multiplier × I
spending = S + (bills_increase_pct / 100) × H
one_off  = one_off_amount + one_off_months_spending × S
(a) today:  runway(B, S, I)
(b) shock:  runway(B − one_off, spending, income)
(c) optim:  runway(B − one_off, spending − total_cuts, income)
```
EI-cap view (R11): income = min(income_multiplier × I, 3159), labelled.

### 2.5 Optimizer
- Levers = monthly medians per customer: `cash_withdrawals_genuine`, `household_bills`, `transfers_out_other`.
- Each lever cut 0% up to its limit (D-1) in steps (D-3); brute force every combination (a few hundred to a few thousand, instant).
- Aim per D-2. If the goal can't be reached at max cuts: report best runway and `extra savings = horizon × (shortfall at max cuts) − buffer_left`.
- Type hooks: Pension-protected (job loss only cuts non-pension income), Stabilize first (plan step 1 = stop going below zero), Savings-first (show savings-first plan when cuts can't reach the goal).

### 2.6 Twist on everyone
- Uses the customer table from `data.py`; same formula, vectorized with numpy.
- Rank = share of customers whose runway (b) is longer; also within type.

---

## 3. Verification

| ID | Test | Checks |
|---|---|---|
| **V1** | Golden values: 3 accounts calculated by hand (I, S, H, B, runways for the 3 README twists). Engine matches to 1 decimal. | R1, R4 |
| **V2** | Type counts match R2. | R2 |
| **V3** | Twist parsing: 3 README twists + 12 rephrasings; both parsers give expected settings. | R7 |
| **V4** | Optimizer: 5 cases incl. one impossible; result matches brute-force expectation under the chosen aim. | R5 |
| **V5** | Bulk: all 4,500 accounts × 3 README twists, zero exceptions. | N3 |
| **V6** | Wi-Fi off: a twist still works via backup parser. | R7, N5 |
| **V7** | Edge accounts: 49649 (shortest history), 21132 / 22682 (zero income), 32078 / 36407 (buffer ≤ 0), a pensioner, a defaulted loan, a running loan, no household bills. | N3 |
| **V8** | Breakdown: every runway = savings ÷ shortfall in the same table; (b) unchanged. | R9, N4 |
| **V9** | Timing: 5 runs, paste → answer under 30 s. | N2 |
| **V10** | Mock judging ×3: random account + twist, 1 + 3 + 1 minutes. | All |
| **V11** | Everyone = single: zero mismatches over all accounts × 3 README twists. | R10 |
| **V12** | Follow-ups: "account 23595 laid off, EI 55%" → "what if bills also go up 15%?" → "make it 9 months". Settings correct at each step. | R8 |

---

## 4. Implementation

### 4.1 Milestones
| Milestone | Time | Done when |
|---|---|---|
| **M1** | Sat ~10:30 PM | R1, R3, R4 (a)+(b) working; V1 passes |
| **M2** | Sun 12:00 AM | MVP without the LLM: R2, R5 (placeholders OK), R6, R9, backup parser, basic UI; V2, V4, V8 pass |
| **M3** | Sun 3:00 AM | R7 with LLM, R8 memory, R10 everyone; V3, V5, V6, V7, V11, V12 pass |
| Sleep | 3:00-7:00 AM | Stagger if needed |
| **M4** | Sun 10:00 AM | Open decisions final, numbers recomputed (R12), R11; feature freeze; V9, V10 pass |
| **M5** | Sun 11:30 AM | Video, write-up, sources, public repo submitted |

### 4.2 Tasks

| Task | Role | Est. | Depends on | Req |
|---|---|---|---|---|
| T1 Skeleton: all functions in 2.3 returning placeholder values | A | 20m | — | — |
| T2 `data.py` + `metrics.py` (official numbers, runway, customer table for all accounts) | A | 1h | T1 | R1 |
| T3 Hand-calculate golden values | B | 45m | — | V1 |
| T4 `shocks.py`: runways (a), (b), verdict | A | 45m | T2 | R3, R4 |
| T5 Check vs golden values | A + B | 30m | T3, T4 | V1 |
| T6 `customer_types.py` | A | 45m | T2 | R2 |
| T7 `optimizer.py` with placeholders + brute-force test | B | 1.5h | T4 | R5, V4 |
| T8 `goalplan.py` with placeholders | B | 45m | T2 | R6 |
| T9 `twist.py`: schema, validate, fallback parser, merge for follow-ups | C | 1h | — | R7, R8 |
| T10 `explain.py`: breakdown + sentences | C | 45m | T4, T7 | R9 |
| T11 `app.py`: twist box → understood (editable) → breakdown → plans | C | 1.5h | T9, T10 | R3, R7, R9 |
| T12 M2 integration: 5 accounts end to end | All | 30m | T11 | M2 |
| T13 `everyone.py` + panel in app | A | 1h | T4, T7 | R10, V11 |
| T14 `session.py` + history panel + LLM translator | C | 1.5h | T9 | R7, R8, V12 |
| T15 Tests V3, V5, V6, V7 | A | 1h | T12 | — |
| T16 Team decides D-1 to D-5; recompute findings (R12) | All + B | 45m | T7, T13 | R12 |
| T17 EI-cap view | A | 30m | T4 | R11 |
| T18 Pitch script (lead with the finding) | B | 45m | T16 | — |
| T19 Mock judging ×3, fix issues | All | 1h | M3 | V10 |
| T20 Video, write-up, sources, public repo, submit | C + B | 1.5h | M4 | S2-S5 |

### 4.3 Rules while building
- Nothing SHOULD/COULD before M2.
- Placeholders are labelled in code (`# PLACEHOLDER: decision D-1`) so they're easy to find and change.
- Commit often; `main` must run after M2.
- A task 50% over its estimate → tell the team and decide whether to cut it.
- Any change to a definition or setting gets written into 1.4 and AGENTS.md.
