# Tangerine Resilience Rewired · Sheridan Datathon 2026

Financial resilience agent: type a customer + a "what if", get three runways (today / after shock / after optimizer), a personal plan, and how the same twist hits every customer.

## Run
```
pip install -r requirements.txt
python demo.py
python -m pytest tests     # or: python tests/test_smoke.py
```
Put the CSVs from the Tangerine data folder into `data/` (NOT transactions.csv; it's over GitHub's 100 MB limit).

See AGENTS.md (context) and PLAN.md (requirements, tasks).

Data: PKDD'99 Discovery Challenge Financial dataset, CTU Prague Relational Dataset Repository (https://relational.fel.cvut.cz/dataset/Financial).
