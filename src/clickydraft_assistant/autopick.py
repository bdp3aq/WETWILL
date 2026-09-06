"""Opt-in autopick safety net — NOT full auto-draft.

Scope, agreed explicitly before building this (see README.md "Autopick
safety net" and CLAUDE.md): this tool stays recommendation-first. Manual
picking in the ClickyDraft UI is always the default. This module only
ever fires as a last-resort fallback when Bradley hasn't picked himself
for a while on his own turn — so an idle/missed slot goes to *this
tool's* top recommendation instead of to ClickyDraft's own autopick
(which knows nothing about this league's custom scoring).

There is no discoverable ClickyDraft countdown timer to key off of
(confirmed: nothing changed across League Settings or Picks while polling
during a real turn — see scripts/watch_for_timer_field.py and
API_NOTES.md). So instead of "seconds left on ClickyDraft's own clock,"
the trigger is wall-clock time THIS TOOL has observed Bradley's turn
sitting idle with no pick from him — see turn_clock.py. That means the
timer requires the tool to be running continuously through the draft; if
it's started partway through his own turn, the clock (safely) restarts
from zero at that moment rather than assuming it's already close.

Safety conditions, ALL of which must hold before it fires:
  1. `enabled` is True in config (default False — opt-in only).
  2. It is unambiguously Bradley's turn (see turn.py — inferred from real
     pick history, not a guess).
  3. Bradley hasn't already picked this turn (obviously).
  4. This tool has observed his turn sitting idle for at least
     `wait_seconds` (default 180s / 3 minutes) — see turn_clock.py.
  5. There's an actual top-ranked recommendation with a real projection
     to submit (never falls back to an ADP-fallback-only player, and
     never submits nothing).

Even with all of that true, whether a pick actually gets submitted still
depends on the double opt-in in cli.py (`--confirm-autopick-submit`) —
without it this only ever produces a "WOULD AUTO-PICK" dry-run decision.
"""

from __future__ import annotations

from dataclasses import dataclass

from .ranking import RankedPlayer
from .turn import DraftOrder


@dataclass
class AutopickDecision:
    should_fire: bool
    reason: str
    player: RankedPlayer | None = None


def evaluate_autopick(
    my_team_id: int | None,
    draft_order: DraftOrder | None,
    overall_pick_number: int,
    elapsed_seconds_on_turn: float,
    wait_seconds: float,
    top_available: list[RankedPlayer],
    enabled: bool,
) -> AutopickDecision:
    if not enabled:
        return AutopickDecision(False, "autopick safety net is disabled (config: autopick.enabled)")

    if my_team_id is None:
        return AutopickDecision(False, "no my_team_id configured — can't tell whose turn it is")

    if draft_order is None:
        return AutopickDecision(False, "draft order not yet known (need round-1 picks from every team first)")

    team_on_clock = draft_order.team_on_clock(overall_pick_number)
    if team_on_clock != my_team_id:
        return AutopickDecision(False, "not Bradley's turn")

    if elapsed_seconds_on_turn < wait_seconds:
        return AutopickDecision(
            False,
            f"Bradley's turn for {elapsed_seconds_on_turn:.0f}s so far, waiting until {wait_seconds:.0f}s",
        )

    top_real = next((r for r in top_available if r.has_projection), None)
    if top_real is None:
        return AutopickDecision(False, "no available player with a real projection to fall back to")

    return AutopickDecision(
        True,
        f"no pick from Bradley after {elapsed_seconds_on_turn:.0f}s on his turn — firing safety net",
        player=top_real,
    )
