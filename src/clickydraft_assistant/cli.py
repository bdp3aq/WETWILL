"""Entry point: wires the API client, draft state, ranking engine, and
console display into the polling loop described in API_NOTES.md.

Recommendation display is the default and only always-on behavior. An
opt-in autopick safety net (autopick.py) can additionally fire as a last
resort — see that module's docstring and README.md "Autopick safety net"
for the full scope and safety gating before ever enabling it.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import deque
from pathlib import Path

from rich.console import Console
from rich.live import Live

from .api_client import ClickyDraftAuthError, ClickyDraftClient
from .autopick import evaluate_autopick
from .config import AppConfig
from .display import render_screen
from .draft_timer import read_seconds_remaining
from .fallback_rankings import XlsxAdpFallback
from .models import Pick, Player, Team
from .projections import CSVProjectionSource, ProjectionLookup
from .ranking import rank_available_players
from .roster import compute_roster_needs
from .state import DraftState
from .turn import current_overall_pick_number, infer_draft_order

console = Console()


def _resolve_team_id(teams: list[Team], team_name: str) -> int | None:
    target = team_name.strip().lower()
    for team in teams:
        if team.team_name.strip().lower() == target:
            return team.id
    return None


def build_state(client: ClickyDraftClient) -> tuple[DraftState, list[Team], dict]:
    settings = client.get_league_settings()
    teams = [Team.from_api(t) for t in settings.get("fantasyTeams", [])]
    players_raw = client.get_draftable_players()
    players = [Player.from_api(p) for p in players_raw]
    state = DraftState(players=players, teams=teams)

    picks_raw = client.get_picks()
    picks = [Pick.from_api(p) for p in picks_raw]
    keeper_count = state.ingest_keepers(picks)
    console.print(f"[bold]Loaded[/] {len(players)} players, {len(teams)} teams, {keeper_count} keeper picks.")
    return state, teams, settings


def run_loop(config: AppConfig, once: bool = False, confirm_autopick_submit: bool = False) -> None:
    if not config.cookie:
        console.print(
            f"[yellow]Warning:[/] no cookie found in ${config.cookie_env_var}. "
            "Capture one from DevTools -> Network -> Cookie header and export it. "
            "See README.md."
        )

    console.print(f"[bold]Live draft board:[/] {config.board_url}")

    client = ClickyDraftClient(
        league_id=config.league_id,
        league_instance_id=config.league_instance_id,
        cookie=config.cookie,
    )

    try:
        state, teams, initial_settings = build_state(client)
    except ClickyDraftAuthError as exc:
        console.print(f"[red]Auth error:[/] {exc}")
        sys.exit(1)

    my_team_id = config.my_team_id
    if my_team_id is None and config.my_team_name:
        my_team_id = _resolve_team_id(teams, config.my_team_name)
        if my_team_id is None:
            console.print(f"[red]Could not find a team named '{config.my_team_name}' in league settings.[/]")
            console.print("Teams found: " + ", ".join(t.team_name for t in teams))
            sys.exit(1)
    if my_team_id is None:
        console.print(
            "[yellow]No my_team_id/my_team_name configured — roster-needs weighting is disabled, "
            "showing pure point-value + scarcity rankings.[/]"
        )

    projection_source = None
    if config.projections_csv and Path(config.projections_csv).exists():
        projection_source = CSVProjectionSource(config.projections_csv)
    else:
        console.print(
            f"[yellow]No projections CSV found at '{config.projections_csv}' — rankings will be empty "
            "until ClickyDraft populates projectedStats or a CSV is provided. See README.md.[/]"
        )
    projection_lookup = ProjectionLookup(csv_source=projection_source)

    fallback_source = None
    if config.fallback_rankings_xlsx and Path(config.fallback_rankings_xlsx).exists():
        fallback_source = XlsxAdpFallback(config.fallback_rankings_xlsx)
        console.print(
            f"[dim]Loaded ADP fallback ordering from '{config.fallback_rankings_xlsx}' "
            "(used only for players with no stat-based projection).[/]"
        )

    if config.autopick.enabled:
        console.print(
            f"[bold yellow]Autopick safety net ARMED[/] (trigger: "
            f"{config.autopick.trigger_seconds_remaining:.0f}s remaining on Bradley's clock). "
            f"{'Submission is CONFIRMED — it will actually pick if it fires.' if confirm_autopick_submit else 'Dry-run only (pass --confirm-autopick-submit to allow real submission).'}"
        )

    recent_events: deque = deque(maxlen=50)

    def poll_once() -> None:
        picks_raw = client.get_picks()
        picks = [Pick.from_api(p) for p in picks_raw]
        events = state.update(picks)
        for event in events:
            recent_events.append((state.team_name(event.pick.fantasy_team_id), event))

        needs = (
            compute_roster_needs(state.roster_players(my_team_id))
            if my_team_id is not None
            else compute_roster_needs([])
        )
        ranked = rank_available_players(
            state.available_players(),
            projection_lookup,
            roster_needs=needs if my_team_id is not None else None,
            num_teams=config.num_teams,
            fallback_source=fallback_source,
        )

        real_picks_sorted = sorted((p for p in picks if p.is_real_pick), key=lambda p: p.id)
        draft_order = infer_draft_order(real_picks_sorted, config.num_teams)
        overall_pick_number = current_overall_pick_number(len(real_picks_sorted))
        seconds_remaining = read_seconds_remaining(picks_raw, initial_settings)
        decision = evaluate_autopick(
            my_team_id=my_team_id,
            draft_order=draft_order,
            overall_pick_number=overall_pick_number,
            seconds_remaining=seconds_remaining,
            trigger_seconds_remaining=config.autopick.trigger_seconds_remaining,
            top_available=ranked,
            enabled=config.autopick.enabled,
        )
        if decision.should_fire:
            player_name = decision.player.player.full_name
            if not confirm_autopick_submit:
                console.print(
                    f"[yellow]\\[DRY RUN][/] Autopick would submit [bold]{player_name}[/] now "
                    f"({decision.reason}). Pass --confirm-autopick-submit to allow real submission "
                    "once submit_pick is implemented."
                )
            else:
                try:
                    client.submit_pick(decision.player.player.draftable_player_id, my_team_id)
                    console.print(f"[bold red]AUTO-PICKED[/] {player_name} ({decision.reason})")
                except NotImplementedError as exc:
                    console.print(
                        f"[yellow]\\[DRY RUN][/] Autopick would submit [bold]{player_name}[/] now "
                        f"({decision.reason}) but submit_pick isn't implemented yet: {exc}"
                    )

        screen = render_screen(
            ranked,
            needs,
            config.top_n,
            recent_events,
            state,
            board_url=config.board_url,
            autopick_status=decision.reason if config.autopick.enabled else None,
        )
        return screen

    if once:
        console.print(poll_once())
        return

    with Live(poll_once(), console=console, refresh_per_second=2) as live:
        while True:
            time.sleep(config.poll_interval_seconds)
            try:
                live.update(poll_once())
            except ClickyDraftAuthError as exc:
                console.print(f"[red]Auth error, stopping:[/] {exc}")
                break


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="ClickyDraft live draft assistant — recommendations by default, "
        "plus an opt-in autopick safety net (see README.md)."
    )
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML (default: config.yaml)")
    parser.add_argument("--once", action="store_true", help="Poll once and print, instead of looping live.")
    parser.add_argument(
        "--confirm-autopick-submit",
        action="store_true",
        help="Required, in addition to config autopick.enabled, before the autopick safety net will "
        "actually submit a pick rather than just logging a dry-run. Double opt-in by design.",
    )
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    if not config_path.exists():
        console.print(f"[red]Config file not found: {config_path}[/] — copy config.example.yaml to get started.")
        sys.exit(1)

    config = AppConfig.load(config_path)
    run_loop(config, once=args.once, confirm_autopick_submit=args.confirm_autopick_submit)


if __name__ == "__main__":
    main()
