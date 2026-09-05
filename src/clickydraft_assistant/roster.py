"""Roster construction rules and open-need tracking for a fantasy team.

League roster (from API_NOTES.md): QB, WR, WR, RB, RB, TE, W/R/T, K, DEF,
plus 7 bench slots (16 total). This module figures out, given a team's
currently rostered players, which *starting* slots are still open so the
ranking engine can bias recommendations toward real needs.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .models import FLEX_ELIGIBLE_POSITIONS, Player, normalize_position

# Dedicated (non-flex, non-bench) starting slots and how many of each.
DEFAULT_STARTER_SLOTS: dict[str, int] = {
    "QB": 1,
    "WR": 2,
    "RB": 2,
    "TE": 1,
    "K": 1,
    "DEF": 1,
}
DEFAULT_FLEX_SLOTS = 1  # W/R/T
DEFAULT_BENCH_SLOTS = 7


@dataclass
class RosterNeeds:
    """Result of evaluating a team's roster against the slot requirements."""

    open_starter_slots: dict[str, int] = field(default_factory=dict)  # position -> count still open
    open_flex_slots: int = 0
    bench_slots_filled: int = 0
    bench_slots_total: int = DEFAULT_BENCH_SLOTS

    def needs_position(self, position: str) -> bool:
        return self.open_starter_slots.get(normalize_position(position), 0) > 0

    def flex_open_for(self, position: str) -> bool:
        return self.open_flex_slots > 0 and normalize_position(position) in FLEX_ELIGIBLE_POSITIONS

    @property
    def bench_open(self) -> bool:
        return self.bench_slots_filled < self.bench_slots_total


def compute_roster_needs(
    rostered_players: list[Player],
    starter_slots: dict[str, int] | None = None,
    flex_slots: int = DEFAULT_FLEX_SLOTS,
    bench_slots: int = DEFAULT_BENCH_SLOTS,
) -> RosterNeeds:
    """Greedily fills dedicated starter slots first (by position count), then
    the flex slot from any leftover WR/RB/TE, then treats everything else as
    bench. This mirrors how a real roster gets built and is order-independent
    since only position *counts* matter, not draft order.
    """
    starter_slots = dict(starter_slots or DEFAULT_STARTER_SLOTS)
    counts = Counter(normalize_position(pos) for p in rostered_players for pos in p.normalized_positions[:1])

    open_starters: dict[str, int] = {}
    leftover_flex_eligible = 0
    for position, needed in starter_slots.items():
        have = counts.get(position, 0)
        used = min(have, needed)
        open_starters[position] = needed - used
        if position in FLEX_ELIGIBLE_POSITIONS:
            leftover_flex_eligible += have - used

    flex_used = min(leftover_flex_eligible, flex_slots)
    open_flex = flex_slots - flex_used
    leftover_after_flex = leftover_flex_eligible - flex_used

    non_flex_leftover = sum(
        counts.get(pos, 0) - min(counts.get(pos, 0), needed)
        for pos, needed in starter_slots.items()
        if pos not in FLEX_ELIGIBLE_POSITIONS
    )
    bench_filled = min(len(rostered_players), leftover_after_flex + non_flex_leftover)
    # Fallback: if the above undercounts (e.g. duplicate accounting), clamp to roster size.
    bench_filled = min(bench_filled, bench_slots)

    return RosterNeeds(
        open_starter_slots=open_starters,
        open_flex_slots=max(open_flex, 0),
        bench_slots_filled=bench_filled,
        bench_slots_total=bench_slots,
    )
