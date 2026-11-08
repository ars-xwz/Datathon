"""The screen (all 6 steps). OWNER: Basmah.

Run:   python app.py      then open http://localhost:8000

A small local web server using only Python's standard library (no extra installs, works offline).
It serves the design page (web/index.html) and answers its questions with the team's engine:
  POST /api/understand   steps 1-2: words -> settings          (pipeline.understand)
  POST /api/run          steps 3-6: settings -> every number   (pipeline.run)
                         + each customer's runway for the globe (everyone.everyone_table)
  GET  /api/customers    account ids + types, to place the dots on the globe
  POST /api/reset        forget the current twist (history is kept)
The page never calculates anything itself; every number comes from here.
"""
import json
import math
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

import numpy as np

from pipeline import understand, run
from engine.session import Session
from engine.metrics import all_customers
from engine.customer_types import TYPES
from engine.everyone import everyone_table
from engine.shocks import ei_cap_view, goal_months
from engine.twist import problems

HERE = Path(__file__).resolve().parent
PAGE = HERE / "web" / "index.html"
PORT = 8000

session = Session()                      # one judge, one screen: a single shared memory is enough
TABLE = all_customers()                  # loaded once (step 3 table)
IDS = [int(a) for a in TABLE.index]      # the globe uses this order for every array we send


def to_json(obj):
    """json.dumps that understands numpy numbers and turns NaN/inf into null."""
    def clean(x):
        if isinstance(x, dict):
            return {str(k): clean(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [clean(v) for v in x]
        if isinstance(x, (np.integer,)):
            return int(x)
        if isinstance(x, (np.floating, float)):
            x = float(x)
            return None if (math.isnan(x) or math.isinf(x)) else x
        if isinstance(x, np.bool_):
            return bool(x)
        return x
    return json.dumps(clean(obj)).encode("utf-8")


def history():
    """Recent requests for the history panel (newest first)."""
    return [{"text": t, "settings": s, "parser": p} for t, s, p in session.recent(8)]


def customers_payload():
    """Account ids + type index (0-3, in TYPES order) for placing the dots."""
    type_index = {name: k for k, name in enumerate(TYPES)}
    ratio = (TABLE["B"] / TABLE["S"].where(TABLE["S"] > 0, 1)).round(2)
    return {"ids": IDS, "types": TYPES,
            "t": [type_index[x] for x in TABLE["type"]],
            "order": [float(r) for r in ratio]}          # savings / spending, only used to arrange dots


def do_understand(body):
    """Steps 1-2: translate the twist text into settings (never calculates)."""
    settings, used = understand(body.get("text", ""), session)
    return {"settings": settings, "parser_used": used, "problems": problems(settings)}


def do_run(body):
    """Steps 3-6: run the engine on confirmed settings and return everything the screen needs."""
    settings = dict(session.settings)
    settings.update(body.get("settings") or {})
    out = run(settings, session, body.get("text", ""), body.get("parser_used", "manual"))
    t = everyone_table(settings).reindex(IDS)
    goal = goal_months(settings)
    out["ei_cap"] = ei_cap_view(out["profile"], settings)
    out["settings"] = settings
    out["goal_used"] = goal
    out["globe"] = {"runway_shock": t["runway_shock"].round(1).tolist(),     # 120 = no shortfall
                    "runway_opt": t["runway_opt"].round(1).tolist()}
    out["history"] = history()
    return out


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload, kind="application/json"):
        data = payload if isinstance(payload, bytes) else to_json(payload)
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            # the page gets the customer list (ids + types) built in, so the globe can draw right away
            html = PAGE.read_text(encoding="utf-8").replace("__CUSTOMERS__", to_json(customers_payload()).decode())
            self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path == "/api/customers":
            self._send(200, customers_payload())
        elif self.path == "/api/history":
            self._send(200, {"history": history(), "settings": session.settings})
        else:
            self._send(404, {"error": "Not found"})

    def do_POST(self):
        try:
            body = self._body()
            if self.path == "/api/understand":
                self._send(200, do_understand(body))
            elif self.path == "/api/run":
                self._send(200, do_run(body))
            elif self.path == "/api/reset":
                session.reset()
                self._send(200, {"settings": session.settings, "history": history()})
            else:
                self._send(404, {"error": "Not found"})
        except ValueError as e:                       # bad settings / unknown account: show the message
            self._send(400, {"error": str(e)})
        except Exception as e:                        # never crash the demo; show what went wrong
            self._send(500, {"error": f"Something went wrong: {e}"})

    def log_message(self, fmt, *args):                # keep the terminal quiet
        pass


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"Screen running at {url}  (press Ctrl+C to stop)")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
