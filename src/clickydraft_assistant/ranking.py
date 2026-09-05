"""Turns projected fantasy points into a single "who should Bradley take next"
ranking, per API_NOTES.md step 4: raw point value *and* positional
scarcity / roster needs, not just a static points-based board.

Method (documented here since it's a judgment call, not something the spec
pins down):

1. Projected points per player = league custom scoring applied to that
   player's projected raw stats (scoring.py + projections.py).
2. Value Over Replacement (VOR) per position = player's points minus the
   points of the "replacement level" player still available at that
   position — approximated as the Nth-best remaining player at the
   position, where N scales with team count and how many starters share
   that position (RB/WR get a wider replacement rank since they also fill
   the flex spot).
3. A flat need bonus is added when the player would fill one of Bradley's
   still-open starting slots (bigger bonus for a dedicated slot than for
   only the flex slot), so a merely-good player who plugs a real hole
   outranks a slightly-better player at an already-full position.
4. final_score = VOR + need_bonus, sorted descending.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Player, normalize_position
from .projections import ProjectionLookup
from .roster import RosterNeeds
from .scoring import ScoringSettings, score_player

# How many "replacement level" ranks deep to look, expressed as a multiple
# of team count. RB/WR are wider because they also compete for the flex slot.
REPLACEMENT_RANK_MULTIPLIER: dict[str, float] = {
    "QB": 1.0,
    "RB": 2.5,
    "WR": 2.5,
    "TE": 1.0,
    "K": 1.0,
    "DEF": 1.0,
}

NEED_BONUS_STARTER = 6.0
NEED_BONUS_FLEX = 3.0


@dataclass
class RankedPlayer:
    player: Player
    projected_points: float
    replacement_points: float
    vor: float
    need_bonus: float
    final_score: float
    has_projection: bool

    @property
    def position(self) -> str:
        return self.player.primary_position


def _replacement_rank(position: str, num_teams: int) -> int:
    multiplier = REPLACEMENT_RANK_MULTIPLIER.get(position, 1.0)
    return max(1, round(num_teams * multiplier))


def _replacement_levels(points_by_position: dict[str, list[float]], num_teams: int) -> dict[str, float]:
    levels = {}
    for position, points_list in points_by_position.items():
        ranked = sorted(points_list, reverse=True)
        rank = _replacement_rank(position, num_teams)
        index = min(rank, len(ranked)) - 1
        levels[position] = ranked[index] if ranked and index >= 0 else 0.0
    return levels


def _need_bonus(position: str, needs: RosterNeeds | None) -> float:
    if needs is None:
        return 0.0
    if needs.needs_position(position):
        return NEED_BONUS_STARTER
    if needs.flex_open_for(position):
        return NEED_BONUS_FLEX
    return 0.0


def rank_available_players(
    available_players: list[Player],
    projection_lookup: ProjectionLookup,
    roster_needs: RosterNeeds | None = None,
    scoring_settings: ScoringSettings | None = None,
    num_teams: int = 14,
) -> list[RankedPlayer]:
    scoring_settings = scoring_settings or ScoringSettings()

    projected: dict[int, tuple[float, bool]] = {}
    points_by_position: dict[str, list[float]] = {}
    for player in available_players:
        stats = projection_lookup.get_stats(player)
        has_projection = bool(stats)
        points = score_player(player.primary_position, stats, scoring_settings) if has_projection else 0.0
        projected[player.draftable_player_id] = (points, has_projection)
        if has_projection:
            points_by_position.setdefault(player.primary_position, []).append(points)

    replacement_levels = _replacement_levels(points_by_position, num_teams)

    ranked: list[RankedPlayer] = []
    for player in available_players:
        points, has_projection = projected[player.draftable_player_id]
        position = player.primary_position
        replacement = replacement_levels.get(position, 0.0)
        vor = points - replacement if has_projection else float("-inf")
        bonus = _need_bonus(position, roster_needs)
        final_score = vor + bonus if has_projection else float("-inf")
        ranked.append(
            RankedPlayer(
                player=player,
                projected_points=points,
                replacement_points=replacement,
                vor=vor,
                need_bonus=bonus,
                final_score=final_score,
                has_projection=has_projection,
            )
        )

    ranked.sort(key=lambda r: r.final_score, reverse=True)
    return ranked
