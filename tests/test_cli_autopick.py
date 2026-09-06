"""Integration test: the autopick safety net must fire at most once per
pick slot, even across many polls -- a lagging get_picks() response after
a real submission (or a submission failure) must never cause a duplicate
attempt. See cli.py's `already_attempted_pick_number` guard.
"""

import unittest
from pathlib import Path
from unittest.mock import patch

from clickydraft_assistant import cli
from clickydraft_assistant.projections import CSVProjectionSource
from clickydraft_assistant.config import AppConfig, AutopickConfig

PLAYERS_RAW = [
    {"draftablePlayerId": 1, "firstName": "Christian", "lastName": "McCaffrey", "positions": ["RB"], "teamAbbr": "SF"},
    {"draftablePlayerId": 2, "firstName": "Justin", "lastName": "Jefferson", "positions": ["WR"], "teamAbbr": "MIN"},
    {"draftablePlayerId": 3, "firstName": "Ja", "lastName": "Chase", "positions": ["WR"], "teamAbbr": "CIN"},
]
SETTINGS = {"fantasyTeams": [{"id": 10, "teamName": "Bradley"}, {"id": 20, "teamName": "Rival"}]}
PICK1 = {
    "id": 1, "fantasyTeamId": 20, "draftablePlayerId": 2, "draftablePlayer": PLAYERS_RAW[1],
    "round": 1, "posInRound": 1, "keeper": False, "autoDrafted": False,
    "deleteAction": False, "skipAction": False,
}
PICK2 = {
    "id": 2, "fantasyTeamId": 10, "draftablePlayerId": 1, "draftablePlayer": PLAYERS_RAW[0],
    "round": 1, "posInRound": 2, "keeper": False, "autoDrafted": False,
    "deleteAction": False, "skipAction": False,
}


class StopLoop(Exception):
    pass


class FakeClientNeverReflectsSubmission:
    """Simulates a lagging server: get_picks() never shows the pick this
    tool submits, so without the one-shot guard the safety net would keep
    re-firing on every subsequent poll."""

    def __init__(self, *_a, **_k):
        self.call = 0
        self.submitted = []

    def get_league_settings(self):
        return SETTINGS

    def get_draftable_players(self):
        return PLAYERS_RAW

    def get_picks(self):
        self.call += 1
        if self.call >= 6:
            raise StopLoop()
        return [] if self.call == 1 else [PICK1, PICK2]

    def submit_pick(self, **kwargs):
        self.submitted.append(kwargs)
        return {"id": 999, **kwargs}


class TestAutopickFiresOnlyOncePerSlot(unittest.TestCase):
    def test_does_not_duplicate_submit_across_many_polls(self):
        client_holder = {}

        def make_client(*a, **k):
            client_holder["client"] = FakeClientNeverReflectsSubmission(*a, **k)
            return client_holder["client"]

        with patch("clickydraft_assistant.cli.ClickyDraftClient", side_effect=make_client), \
             patch.object(CSVProjectionSource, "get_stats", return_value={"rec_yds": 90, "rec": 6}), \
             patch("clickydraft_assistant.cli.time.sleep", lambda _s: None), \
             patch("clickydraft_assistant.turn_clock.time.monotonic", side_effect=lambda: 1000.0):
            # elapsed_seconds always computes to 0 the first time a pick number is
            # seen (monotonic pinned), which is enough here since wait_seconds=0.
            cfg = AppConfig(
                league_id=1, league_instance_id=1, my_team_id=10, my_team_name=None,
                poll_interval_seconds=0.0,
                projections_csv=str(Path(__file__).resolve().parent.parent / "data" / "projections.example.csv"),
                fallback_rankings_xlsx=None, num_teams=2, cookie_env_var="CLICKYDRAFT_COOKIE",
                top_n=5, autopick=AutopickConfig(enabled=True, wait_seconds=0.0),
            )
            try:
                cli.run_loop(cfg, once=False, confirm_autopick_submit=True)
            except StopLoop:
                pass

        submitted = client_holder["client"].submitted
        self.assertEqual(len(submitted), 1, f"expected exactly one submission, got {submitted}")
        self.assertEqual(submitted[0]["draftable_player_id"], 3)


if __name__ == "__main__":
    unittest.main()
