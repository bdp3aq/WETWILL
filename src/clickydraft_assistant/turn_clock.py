"""Wall-clock "how long has it been Bradley's turn" tracking for the
autopick safety net.

Replaces the earlier plan of reading a ClickyDraft-provided countdown
timer — confirmed there isn't a discoverable one (nothing changed across
League Settings or Picks while polling during a real turn; see
scripts/watch_for_timer_field.py and API_NOTES.md's timer open item).
Instead this measures the only clock we actually have: how long THIS
PROCESS has observed the current pick slot as Bradley's, with no new
real pick landing for it yet.

Caveat, by construction: this can only measure time since the tool
itself started observing the turn. If the tool is started (or restarted)
partway through Bradley's own turn, the clock restarts from zero at that
moment rather than reflecting how long it's actually been his turn. This
is a conservative bias — it can only delay firing, never fire early — but
it does mean the tool needs to be running continuously through the draft
for the wait threshold to mean what it says.
"""

from __future__ import annotations

import time


class TurnClock:
    def __init__(self):
        self._current_pick_number: int | None = None
        self._turn_started_at: float | None = None

    def elapsed_seconds(self, overall_pick_number: int) -> float:
        """Call once per poll with the pick number currently on the clock.
        Returns seconds elapsed since this process first observed that pick
        number as current; resets to 0 whenever the pick number changes
        (a new turn began, whether Bradley's or someone else's).
        """
        now = time.monotonic()
        if overall_pick_number != self._current_pick_number:
            self._current_pick_number = overall_pick_number
            self._turn_started_at = now
        return now - self._turn_started_at
