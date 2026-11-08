"""Smoke test: the pipeline runs end to end. Keep this passing at all times."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.session import Session
from pipeline import understand, run

def test_pipeline_runs():
    s = Session()
    settings, used = understand("account 23595 laid off EI 55%", s)
    out = run(settings, s, "x", used)
    assert "view" in out and len(out["view"]["table"]) > 0

if __name__ == "__main__":
    test_pipeline_runs(); print("smoke test passed")
