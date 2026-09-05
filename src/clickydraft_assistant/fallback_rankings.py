"""Fallback-only ordering for players with no stat-based projection.

This is intentionally *not* the primary ranking signal — see API_NOTES.md
("Notice several of these deviate meaningfully from Yahoo defaults... this
is exactly why generic ADP/rankings won't cut it"). Generic ADP ignores
this league's custom scoring entirely, so it must never outrank a player
who *does* have a real point-value projection. Its only job is to give a
sane order to the players ranking.py otherwise has nothing to say about,
instead of leaving them in arbitrary order at the bottom of the board.

Reads `data/Top-144 Player Rankings.xlsx` (Bradley-supplied), which has two
sheets ("Full PPR", "12 PPR") of overall-rank/player/ADP triples laid out
in repeating column blocks, no positions or raw stats. When a player
appears on both sheets, its fallback rank is the average of the two.
"""

from __future__ import annotations

import re
from pathlib import Path

from openpyxl import load_workbook

from .models import Player

_ROOKIE_MARKER = re.compile(r"\*+$")


def _clean_name(name: str) -> str:
    return _ROOKIE_MARKER.sub("", name).strip().lower()


class XlsxAdpFallback:
    def __init__(self, xlsx_path: str | Path):
        self.xlsx_path = Path(xlsx_path)
        self._ranks_by_name: dict[str, list[float]] = {}
        if self.xlsx_path.exists():
            self._load()

    def _load(self) -> None:
        wb = load_workbook(self.xlsx_path, data_only=True)
        for sheet in wb.worksheets:
            for row in sheet.iter_rows(values_only=True):
                # Layout is repeating (spacer, rank, player, ADP) blocks — see the
                # sample dump in the module docstring/README for the real shape.
                for col_start in range(1, len(row), 4):
                    block = row[col_start : col_start + 2]
                    if len(block) < 2:
                        continue
                    rank, name = block
                    if not isinstance(rank, (int, float)) or not isinstance(name, str):
                        continue
                    self._ranks_by_name.setdefault(_clean_name(name), []).append(float(rank))

    def get_rank(self, player: Player) -> float | None:
        ranks = self._ranks_by_name.get(_clean_name(player.full_name))
        if not ranks:
            return None
        return sum(ranks) / len(ranks)
