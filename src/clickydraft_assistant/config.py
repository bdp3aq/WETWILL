"""Loads the tool's YAML config (league IDs, polling, projections source, etc)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class AppConfig:
    league_id: int
    league_instance_id: int
    my_team_id: int | None
    my_team_name: str | None
    poll_interval_seconds: float
    projections_csv: str | None
    num_teams: int
    cookie_env_var: str
    top_n: int

    @property
    def cookie(self) -> str | None:
        return os.environ.get(self.cookie_env_var)

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
            num_teams=int(raw.get("num_teams", 14)),
            cookie_env_var=raw.get("cookie_env_var", "CLICKYDRAFT_COOKIE"),
            top_n=int(raw.get("top_n", 15)),
        )
