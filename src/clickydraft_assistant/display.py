"""Console rendering: live recommendation board + recent pick feed.

Display only — this module never submits anything back to ClickyDraft.
"""

from __future__ import annotations

from collections import deque

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .ranking import RankedPlayer
from .roster import RosterNeeds
from .state import PickEvent


def _format_needs(needs: RosterNeeds) -> str:
    open_slots = [pos for pos, count in needs.open_starter_slots.items() for _ in range(count)]
    if needs.open_flex_slots:
        open_slots += ["FLEX"] * needs.open_flex_slots
    if not open_slots:
        return "all starting slots filled"
    return ", ".join(open_slots)


def render_recommendations_table(ranked: list[RankedPlayer], needs: RosterNeeds, top_n: int) -> Table:
    table = Table(title=f"Top {top_n} Recommendations — open needs: {_format_needs(needs)}")
    table.add_column("#", justify="right")
    table.add_column("Player")
    table.add_column("Pos")
    table.add_column("NFL Team")
    table.add_column("Proj Pts", justify="right")
    table.add_column("VOR", justify="right")
    table.add_column("Need+", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Bye", justify="right")

    for i, r in enumerate(ranked[:top_n], start=1):
        if not r.has_projection:
            proj, vor, bonus, score = ("—", "—", "—", "—")
        else:
            proj = f"{r.projected_points:.1f}"
            vor = f"{r.vor:+.1f}"
            bonus = f"{r.need_bonus:+.1f}" if r.need_bonus else "0.0"
            score = f"{r.final_score:.1f}"
        table.add_row(
            str(i),
            r.player.full_name,
            r.position,
            r.player.team_abbr or "-",
            proj,
            vor,
            bonus,
            score,
            str(r.player.bye_week) if r.player.bye_week else "-",
        )
    return table


def render_recent_picks(events: deque[tuple[str, PickEvent]], state, limit: int = 10) -> Panel:
    lines = []
    for team_name, event in list(events)[-limit:][::-1]:
        player = event.pick.player
        name = player.full_name if player else f"player {event.pick.draftable_player_id}"
        if event.kind == "pick":
            keeper_tag = " (keeper)" if event.pick.keeper else ""
            lines.append(f"[green]R{event.pick.round}[/] {team_name} selects {name}{keeper_tag}")
        else:
            lines.append(f"[red]undo[/] {team_name}'s pick of {name} was removed")
    body = Text.from_markup("\n".join(lines) if lines else "No picks yet.")
    return Panel(body, title="Recent Picks")


def render_screen(
    ranked: list[RankedPlayer],
    needs: RosterNeeds,
    top_n: int,
    events: deque,
    state,
    board_url: str | None = None,
) -> Group:
    parts = []
    if board_url:
        parts.append(Text.from_markup(f"[bold]Live draft board:[/] {board_url}"))
    parts.append(render_recommendations_table(ranked, needs, top_n))
    parts.append(render_recent_picks(events, state))
    return Group(*parts)
