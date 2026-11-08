"""R8: agent memory. OWNER: Angela. STATUS: working minimal version."""
from engine.twist import TWIST_SCHEMA

class Session:
    """Keeps current settings and a history of requests."""
    def __init__(self):
        self.settings = dict(TWIST_SCHEMA)
        self.history = []          # list of (text, settings, parser_used)

    def update(self, text, settings, parser_used):
        self.settings = dict(settings)
        self.history.append((text, dict(settings), parser_used))
