"""R8: agent memory. OWNER: Angela.
Keeps the current settings (so follow-ups only change what they mention) and a request history."""
from engine.twist import TWIST_SCHEMA


class Session:
    """Keeps current settings and a history of requests."""

    def __init__(self):
        self.settings = dict(TWIST_SCHEMA)
        self.history = []          # list of (text, settings, parser_used), oldest first

    def update(self, text, settings, parser_used):
        """Call after a successful run: remember these settings and log the request."""
        self.settings = dict(settings)
        self.history.append((text, dict(settings), parser_used))

    def recent(self, n=8):
        """Most recent requests first, for the history panel."""
        return list(reversed(self.history[-n:]))

    def reset(self):
        """Forget the current twist (history is kept)."""
        self.settings = dict(TWIST_SCHEMA)
