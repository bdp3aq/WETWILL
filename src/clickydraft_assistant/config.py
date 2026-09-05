"""Loads the tool's YAML config (league IDs, polling, projections source, etc)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class AutopickConfig:
    """See autopick.py for the full safety gating this config feeds into.
    Off by default — this is an opt-in safety net, never full auto-draft.
    """

    enabled: bool = False
    trigger_seconds_remaining: float = 10.0

    @classmethod
    def from_raw(cls, raw: dict | None) -> "AutopickConfig":
        raw = raw or {}
        return cls(
            enabled=bool(raw.get("enabled", False)),
            trigger_seconds_remaining=float(raw.get("trigger_seconds_remaining", 10.0)),
        )


@dataclass
class AppConfig:
    league_id: int
    league_instance_id: int
    my_team_id: int | None
    my_team_name: str | None
    poll_interval_seconds: float
    projections_csv: str | None
    fallback_rankings_xlsx: str | None
    num_teams: int
    cookie_env_var: str
    top_n: int
    autopick: AutopickConfig

    @property
    def cookie(self) -> str | None:
        return os.environ.get(self.cookie_env_var)

    @property
    def board_url(self) -> str:
        """The live draft-room page Bradley actually drafts from (distinct from the
        dashboard/settings URL — see API_NOTES.md "Bradley's League")."""
        return f"https://clickydraft.com/draftapp/board/{self.league_instance_id}"

    @classmethod
    def load(cls, path: str | Path) -> "AppConfig":
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        return cls(
            league_id=int(raw["league_id"]),
            league_instance_id=int(raw["league_instance_id"]),
            my_team_id=raw.get("my_team_id"),
            my_team_name=raw.get("my_team_name"),
            poll_interval_seconds=float(raw.get("poll_interval_seconds", 1.5)),
            projections_csv=raw.get("projections_csv"),
            fallback_rankings_xlsx=raw.get("fallback_rankings_xlsx"),
            num_teams=int(raw.get("num_teams", 14)),
            cookie_env_var=raw.get("cookie_env_var", "CLICKYDRAFT_COOKIE"),
            top_n=int(raw.get("top_n", 15)),
            autopick=AutopickConfig.from_raw(raw.get("autopick")),
        )
