"""Custom point-value scoring engine for the Wet Willie Brigade Yahoo league.

Values below come from API_NOTES.md ("League Scoring") and deliberately
deviate from Yahoo's defaults (5pt passing TDs, 0.33 PPR, yardage bonus
thresholds, custom DST points-allowed tiers) — that's the whole reason this
tool exists instead of using generic ADP/rankings.

Stat dicts are intentionally loose (missing keys default to 0) so partial
projections still produce a usable, if lower, point total instead of
crashing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import normalize_position


def _yardage_points(yards: float, per_point: float, bonuses: list[tuple[float, float]]) -> float:
    """`per_point` yards = 1 fantasy point, plus flat bonuses once yardage crosses each threshold."""
    points = yards / per_point
    for threshold, bonus in bonuses:
        if yards >= threshold:
            points += bonus
    return points


def _fg_points(makes_by_bucket: dict[str, float], per_bucket: dict[str, float]) -> float:
    return sum(makes_by_bucket.get(bucket, 0) * value for bucket, value in per_bucket.items())


def _points_allowed_tier_score(points_allowed: float, tiers: list[tuple[float, float, float]]) -> float:
    """`tiers` is a list of (low, high, value); high=None/inf means unbounded."""
    for low, high, value in tiers:
        if points_allowed >= low and (high is None or points_allowed <= high):
            return value
    return 0.0


@dataclass
class ScoringSettings:
    """League scoring coefficients. Defaults mirror API_NOTES.md exactly;
    override individual fields if the league's settings ever change.
    """

    # Offense
    completion: float = 0.125
    pass_yards_per_point: float = 20.0
    pass_yards_bonuses: list[tuple[float, float]] = field(default_factory=lambda: [(555, 20)])
    pass_td: float = 5.0
    interception_thrown: float = -2.0
    rush_yards_per_point: float = 10.0
    rush_yards_bonuses: list[tuple[float, float]] = field(
        default_factory=lambda: [(100, 3), (200, 3), (297, 20)]
    )
    rush_td: float = 6.0
    reception: float = 0.33
    rec_yards_per_point: float = 10.0
    rec_yards_bonuses: list[tuple[float, float]] = field(
        default_factory=lambda: [(100, 4), (200, 4), (337, 20)]
    )
    rec_td: float = 6.0
    return_td: float = 6.0
    two_point_conversion: float = 2.0
    fumble_lost: float = -2.0
    off_fumble_return_td: float = 6.0

    # Kicker
    fg_buckets: dict[str, float] = field(
        default_factory=lambda: {
            "fg_0_19": 1.0,
            "fg_20_29": 2.0,
            "fg_30_39": 3.0,
            "fg_40_49": 4.0,
            "fg_50_plus": 5.0,
        }
    )
    fg_missed: float = 0.0
    pat_made: float = 1.0
    pat_missed: float = 0.0

    # DST
    sack: float = 1.0
    def_interception: float = 2.0
    fumble_recovery: float = 2.0
    def_td: float = 5.1
    safety: float = 2.0
    block_kick: float = 1.7
    kick_punt_return_td: float = 6.0
    points_allowed_tiers: list[tuple[float, float, float]] = field(
        default_factory=lambda: [
            (0, 0, 12.75),
            (1, 6, 8.5),
            (7, 13, 5.97),
            (14, 20, 2.55),
            (21, 27, 0.85),
            (28, 34, 0.0),
            (35, float("inf"), -2.0),
        ]
    )
    fourth_down_stop: float = 1.0
    three_and_out_forced: float = 1.0
    extra_point_returned: float = 2.0


def score_offense(stats: dict, s: ScoringSettings) -> float:
    points = 0.0
    points += stats.get("pass_comp", 0) * s.completion
    points += _yardage_points(stats.get("pass_yds", 0), s.pass_yards_per_point, s.pass_yards_bonuses)
    points += stats.get("pass_td", 0) * s.pass_td
    points += stats.get("pass_int", 0) * s.interception_thrown
    points += _yardage_points(stats.get("rush_yds", 0), s.rush_yards_per_point, s.rush_yards_bonuses)
    points += stats.get("rush_td", 0) * s.rush_td
    points += stats.get("rec", 0) * s.reception
    points += _yardage_points(stats.get("rec_yds", 0), s.rec_yards_per_point, s.rec_yards_bonuses)
    points += stats.get("rec_td", 0) * s.rec_td
    points += stats.get("ret_td", 0) * s.return_td
    points += stats.get("two_pt", 0) * s.two_point_conversion
    points += stats.get("fumbles_lost", 0) * s.fumble_lost
    points += stats.get("off_fum_ret_td", 0) * s.off_fumble_return_td
    return points


def score_kicker(stats: dict, s: ScoringSettings) -> float:
    points = _fg_points(stats, s.fg_buckets)
    points += stats.get("fg_miss", 0) * s.fg_missed
    points += stats.get("pat_made", 0) * s.pat_made
    points += stats.get("pat_miss", 0) * s.pat_missed
    return points


def score_dst(stats: dict, s: ScoringSettings) -> float:
    points = 0.0
    points += stats.get("sacks", 0) * s.sack
    points += stats.get("def_int", 0) * s.def_interception
    points += stats.get("fum_rec", 0) * s.fumble_recovery
    points += stats.get("def_td", 0) * s.def_td
    points += stats.get("safety", 0) * s.safety
    points += stats.get("block_kick", 0) * s.block_kick
    points += stats.get("kick_punt_ret_td", 0) * s.kick_punt_return_td
    if "points_allowed" in stats:
        points += _points_allowed_tier_score(stats["points_allowed"], s.points_allowed_tiers)
    points += stats.get("fourth_down_stops", 0) * s.fourth_down_stop
    points += stats.get("three_and_outs", 0) * s.three_and_out_forced
    points += stats.get("xp_returned", 0) * s.extra_point_returned
    return points


def score_player(position: str, stats: dict, settings: ScoringSettings | None = None) -> float:
    """Route to the right scoring function based on (normalized) position."""
    settings = settings or ScoringSettings()
    pos = normalize_position(position)
    if pos == "K":
        return score_kicker(stats, settings)
    if pos == "DEF":
        return score_dst(stats, settings)
    return score_offense(stats, settings)
