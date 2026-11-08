"""Run the whole pipeline in the terminal. Works from minute one with stubs."""
from engine.session import Session
from pipeline import understand, run

s = Session()
text = "Account 23595 loses their job (EI at 55%) and household bills go up 15%. Do they make it 6 months?"
settings, used = understand(text, s)
print("UNDERSTOOD:", settings, f"(via {used})")
out = run(settings, s, text, used)
for row in out["view"]["table"]:
    print(f"{row[0]:<26}{str(row[1]):>14}{str(row[2]):>16}{str(row[3]):>16}")
print()
for line in out["view"]["sentences"]:
    print("-", line)
