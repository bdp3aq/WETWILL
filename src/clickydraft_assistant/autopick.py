"""Opt-in autopick safety net — NOT full auto-draft.

Scope, agreed explicitly before building this (see README.md "Autopick
safety net" and CLAUDE.md): this tool stays recommendation-first. Manual
picking in the ClickyDraft UI is always the default. This module only
ever fires as a last-resort fallback when Bradley hasn't picked himself
and his own pick timer is about to run out — so a missed slot goes to
*this tool's* top recommendation instead of to ClickyDraft's own
autopick (which knows nothing about this league's custom scoring).

Safety conditions, ALL of which must hold before it fires:
  1. `enabled` is True in config (default False — opt-in only).
  2. It is unambiguously Bradley's turn (see turn.py — inferred from real
     pick history, not a guess).
  3. Bradley hasn't already picked this turn (obviously).
  4. A confirmed, non-None reading of seconds-remaining on the clock puts
     it at or below `trigger_seconds_remaining`. If the timer reading is
     unavailable or its meaning hasn't been confirmed against a live
     session (see API_NOTES.md open item on `draftTimer`), the safety net
     NEVER fires — an unknown timer state is treated as "don't act", not
     "assume it's urgent".
  5. There's an actual top-ranked recommendation with a real projection
     to submit (never falls back to an ADP-fallback-only player, and
     never submits nothing).

Even with all of that true, whether a pick actually gets submitted still
depends on `ClickyDraftClient.submit_pick` being implemented for real
(api_client.py) and on the double opt-in described there — until then
this only ever produces a "WOULD AUTO-PICK" dry-run decision.
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
    seconds_remaining: float | None,
    trigger_seconds_remaining: float,
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

    if seconds_remaining is None:
        return AutopickDecision(
            False,
            "timer reading unavailable/unconfirmed — treating as unknown, not urgent (see API_NOTES.md)",
        )

    if seconds_remaining > trigger_seconds_remaining:
        return AutopickDecision(False, f"{seconds_remaining:.0f}s left, above the {trigger_seconds_remaining:.0f}s trigger")

    top_real = next((r for r in top_available if r.has_projection), None)
    if top_real is None:
        return AutopickDecision(False, "no available player with a real projection to fall back to")

    return AutopickDecision(
        True,
        f"{seconds_remaining:.0f}s left on Bradley's clock — firing safety net",
        player=top_real,
    )
