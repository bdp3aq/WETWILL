"""Whose turn is it right now?

Needed for the opt-in autopick safety net (see autopick.py) so it can never
fire on someone else's turn. Deliberately doesn't depend on any
unconfirmed League Settings field for draft order — it infers the snake
order purely from the sequence of real (non-deleted, non-skipped) picks
already made, which we're fetching every poll anyway. This means turn
detection works from pick #1 onward without needing a new API field
confirmed first, at the cost of not knowing the order before any picks
(including keepers) exist yet.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Pick


@dataclass
class DraftOrder:
    team_order: list[int]  # round-1 pick order, team ids

    def team_on_clock(self, overall_pick_number: int) -> int | None:
        """`overall_pick_number` is 1-indexed (the Nth real pick of the draft).
        Returns the fantasy_team_id whose turn it is, snake-reversing on
        even rounds, or None if the order isn't known yet.
        """
        n = len(self.team_order)
        if n == 0 or overall_pick_number < 1:
            return None
        round_index = (overall_pick_number - 1) // n  # 0-based
        pos_in_round = (overall_pick_number - 1) % n  # 0-based
        if round_index % 2 == 1:  # even rounds (2nd, 4th, ...) snake back
            pos_in_round = n - 1 - pos_in_round
        return self.team_order[pos_in_round]


def infer_draft_order(real_picks_in_order: list[Pick], num_teams: int) -> DraftOrder | None:
    """Reconstruct round-1 draft order from the first `num_teams` real picks
    seen so far, in the order they were made. Keeper picks count toward this
    the same as any other real pick, since they occupy round-1 slots too.
    Returns None until at least `num_teams` real picks have been observed.
    """
    ordered_team_ids: list[int] = []
    seen = set()
    for pick in real_picks_in_order:
        if pick.fantasy_team_id in seen:
            continue
        ordered_team_ids.append(pick.fantasy_team_id)
        seen.add(pick.fantasy_team_id)
        if len(ordered_team_ids) == num_teams:
            return DraftOrder(team_order=ordered_team_ids)
    return None


def current_overall_pick_number(real_pick_count: int) -> int:
    """The pick number that's now on the clock, given how many real picks
    have already landed."""
    return real_pick_count + 1


def round_and_pos_in_round(overall_pick_number: int, num_teams: int) -> tuple[int, int]:
    """1-indexed (round, posInRound) for a given overall pick number, matching
    the field values ClickyDraft itself sends on pick submission (confirmed
    via a captured real request — see API_NOTES.md "Pick submission").
    `posInRound` is the plain sequential slot within the round (1..num_teams),
    not snake-mirrored — e.g. round 8, posInRound 7 is the 7th pick made in
    round 8, regardless of which physical draft-order seat that team sits in.
    """
    round_index = (overall_pick_number - 1) // num_teams  # 0-based
    pos_in_round = (overall_pick_number - 1) % num_teams  # 0-based
    return round_index + 1, pos_in_round + 1
