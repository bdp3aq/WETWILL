"""Player projection lookup.

ClickyDraft's `draftablePlayer.projectedStats` field is `null` in the only
sample response we have (see API_NOTES.md open questions), so the primary
source here is an external CSV of raw per-player stat projections that get
run through scoring.score_player(). If a live league instance *does*
populate `projectedStats` with recognizable keys, that takes precedence.

CSV format (see data/projections.example.csv): one row per player with
`first_name`, `last_name`, `team_abbr`, `position` plus any of the stat
columns used by scoring.py (missing columns default to 0).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .models import Player, normalize_position

# Columns that aren't raw stats — everything else in a CSV row is treated
# as a stat key and coerced to float.
_NON_STAT_COLUMNS = frozenset({"first_name", "last_name", "team_abbr", "position"})


def _name_key(first_name: str, last_name: str) -> str:
    return f"{first_name.strip().lower()}|{last_name.strip().lower()}"


@dataclass
class ProjectionEntry:
    stats: dict
    position: str


class ProjectionSource:
    """Base interface: look up raw projected stats for a player."""

    def get_stats(self, player: Player) -> dict | None:
        raise NotImplementedError


class CSVProjectionSource(ProjectionSource):
    def __init__(self, csv_path: str | Path):
        self.csv_path = Path(csv_path)
        # Primary key includes team (handles duplicate names); fallback key
        # is name-only in case a player was traded since the CSV was built.
        self._by_name_and_team: dict[str, ProjectionEntry] = {}
        self._by_name_only: dict[str, ProjectionEntry] = {}
        self._load()

    def _load(self) -> None:
        if not self.csv_path.exists():
            return
        with self.csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                first = row.get("first_name", "")
                last = row.get("last_name", "")
                team = (row.get("team_abbr") or "").strip().upper()
                position = normalize_position((row.get("position") or "").strip().upper())
                stats = {}
                for key, raw_value in row.items():
                    if key in _NON_STAT_COLUMNS or raw_value in (None, ""):
                        continue
                    try:
                        stats[key] = float(raw_value)
                    except ValueError:
                        continue
                entry = ProjectionEntry(stats=stats, position=position)
                name_key = _name_key(first, last)
                self._by_name_and_team[f"{name_key}|{team}"] = entry
                self._by_name_only[name_key] = entry

    def get_stats(self, player: Player) -> dict | None:
        name_key = _name_key(player.first_name, player.last_name)
        team = (player.team_abbr or "").strip().upper()
        entry = self._by_name_and_team.get(f"{name_key}|{team}") or self._by_name_only.get(name_key)
        return entry.stats if entry else None


def stats_from_projected_stats_field(player: Player) -> dict | None:
    """Best-effort use of `draftablePlayer.projectedStats` if ClickyDraft ever
    populates it for this league. Only used when it's a non-empty dict with
    keys our scoring engine recognizes.
    """
    projected = player.projected_stats
    if not projected or not isinstance(projected, dict):
        return None
    return projected


class ProjectionLookup:
    """Tries the embedded ClickyDraft field first, then falls back to the CSV source."""

    def __init__(self, csv_source: ProjectionSource | None = None):
        self.csv_source = csv_source

    def get_stats(self, player: Player) -> dict:
        embedded = stats_from_projected_stats_field(player)
        if embedded:
            return embedded
        if self.csv_source is not None:
            csv_stats = self.csv_source.get_stats(player)
            if csv_stats:
                return csv_stats
        return {}

    def has_projection(self, player: Player) -> bool:
        return bool(self.get_stats(player))
