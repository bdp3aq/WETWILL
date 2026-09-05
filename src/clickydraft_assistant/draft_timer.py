"""Reading "seconds left on the current pick" — UNCONFIRMED, stubbed out.

The sample Pick object in API_NOTES.md has a `draftTimer` field that's
`null` on a completed pick, so its meaning for an *in-progress* turn is
unknown: it might appear on a placeholder "next pick" record, live only on
the websocket stream (which this project deliberately doesn't use — see
API_NOTES.md), or come from a League Settings field not yet seen in a real
response.

This stub always returns None, which — by design — means the autopick
safety net (autopick.py) can never fire: an unknown timer state is treated
as "don't act," not "assume it's urgent." That's intentional and safe.

To make the autopick safety net actually usable, this needs one more round
of live-session capture (same idea as scripts/inspect_api.py): watch
DevTools -> Network (and the WS frames tab, if it does turn out to live on
the websocket) while your own pick timer counts down, find where a
remaining-seconds or deadline value shows up, and implement the real
parsing here.
"""

from __future__ import annotations

from typing import Any


def read_seconds_remaining(picks_raw: list[dict[str, Any]], league_settings: dict[str, Any]) -> float | None:
    return None
