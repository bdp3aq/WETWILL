"""Data models mirroring the ClickyDraft API payloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

# Positions that fill the flex ("W/R/T") roster slot.
FLEX_ELIGIBLE_POSITIONS = frozenset({"WR", "RB", "TE"})

# ClickyDraft sometimes uses "DST", the league's roster slot is named "DEF".
DEFENSE_ALIASES = frozenset({"DEF", "DST"})


def normalize_position(position: str) -> str:
    """Collapse position spelling variants (DST/DEF) to the league's canonical name."""
    if position in DEFENSE_ALIASES:
        return "DEF"
    return position


@dataclass
class Team:
    id: int
    team_name: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Team":
        return cls(id=data["id"], team_name=data.get("teamName", f"Team {data['id']}"))


@dataclass
class Player:
    """A draftable player. Keyed by the top-level `draftablePlayerId` from a pick,
    which is what picks reference — see API_NOTES.md for the id-vs-draftablePlayerId caveat.
    """

    draftable_player_id: int
    first_name: str
    last_name: str
    positions: list[str]
    team_abbr: Optional[str] = None
    team_full_name: Optional[str] = None
    bye_week: Optional[int] = None
    exp: Optional[int] = None
    projected_stats: Optional[dict[str, Any]] = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def primary_position(self) -> str:
        if not self.positions:
            return "UNK"
        return normalize_position(self.positions[0])

    @property
    def normalized_positions(self) -> list[str]:
        return [normalize_position(p) for p in self.positions]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Player":
        return cls(
            draftable_player_id=data["draftablePlayerId"] if "draftablePlayerId" in data else data["id"],
            first_name=data.get("firstName", ""),
            last_name=data.get("lastName", ""),
            positions=list(data.get("positions") or []),
            team_abbr=data.get("teamAbbr"),
            team_full_name=data.get("teamFullName"),
            bye_week=data.get("byeWeek"),
            exp=data.get("exp"),
            projected_stats=data.get("projectedStats"),
            raw=data,
        )


@dataclass
class Pick:
    id: int
    fantasy_team_id: int
    draftable_player_id: int
    round: Optional[int]
    pos_in_round: Optional[int]
    keeper: bool
    auto_drafted: bool
    delete_action: bool
    skip_action: bool
    player: Optional[Player] = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_real_pick(self) -> bool:
        """A pick that actually consumes a player and a roster slot."""
        return not self.delete_action and not self.skip_action

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Pick":
        player_data = data.get("draftablePlayer")
        return cls(
            id=data["id"],
            fantasy_team_id=data.get("fantasyTeamId"),
            draftable_player_id=data["draftablePlayerId"],
            round=data.get("round"),
            pos_in_round=data.get("posInRound"),
            keeper=bool(data.get("keeper")),
            auto_drafted=bool(data.get("autoDrafted")),
            delete_action=bool(data.get("deleteAction")),
            skip_action=bool(data.get("skipAction")),
            player=Player.from_api(player_data) if player_data else None,
            raw=data,
        )
