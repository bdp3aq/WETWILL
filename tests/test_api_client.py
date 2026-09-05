import unittest
from unittest.mock import MagicMock

from clickydraft_assistant.api_client import ClickyDraftAPIError, ClickyDraftAuthError, ClickyDraftClient


def make_client(session):
    return ClickyDraftClient(league_id=305751, league_instance_id=305775, cookie="JSESSIONID=fake", session=session)


class TestSubmitPick(unittest.TestCase):
    def test_posts_expected_url_and_body_shape(self):
        session = MagicMock()
        response = MagicMock(ok=True, status_code=200)
        response.json.return_value = {"id": 999}
        session.post.return_value = response
        client = make_client(session)

        result = client.submit_pick(
            fantasy_team_id=3322760,
            draftable_player_id=70347,
            round_number=8,
            pos_in_round=7,
        )

        self.assertEqual(result, {"id": 999})
        session.post.assert_called_once()
        _, kwargs = session.post.call_args
        self.assertEqual(
            session.post.call_args[0][0],
            "https://clickydraft.com/draftapp/leagues/305751/league-instances/305775/picks/",
        )
        self.assertEqual(
            kwargs["json"],
            {
                "leagueId": 305751,
                "leagueInstanceId": 305775,
                "fantasyTeamId": 3322760,
                "draftablePlayerId": 70347,
                "round": 8,
                "posInRound": 7,
                "keeper": False,
                "autoDrafted": False,
                "id": None,
                "value": None,
                "skipped": None,
            },
        )
        self.assertEqual(kwargs["headers"]["X-Requested-With"], "XMLHttpRequest")

    def test_auth_error_on_401(self):
        session = MagicMock()
        session.post.return_value = MagicMock(ok=False, status_code=401)
        client = make_client(session)
        with self.assertRaises(ClickyDraftAuthError):
            client.submit_pick(fantasy_team_id=1, draftable_player_id=2, round_number=1, pos_in_round=1)

    def test_api_error_on_non_ok_response(self):
        session = MagicMock()
        session.post.return_value = MagicMock(ok=False, status_code=500, text="boom")
        client = make_client(session)
        with self.assertRaises(ClickyDraftAPIError):
            client.submit_pick(fantasy_team_id=1, draftable_player_id=2, round_number=1, pos_in_round=1)

    def test_does_not_retry_on_failure(self):
        # Retrying a write call risks a duplicate pick submission -- submit_pick
        # must only ever make a single attempt, unlike the GET helper.
        session = MagicMock()
        session.post.return_value = MagicMock(ok=False, status_code=500, text="boom")
        client = make_client(session)
        with self.assertRaises(ClickyDraftAPIError):
            client.submit_pick(fantasy_team_id=1, draftable_player_id=2, round_number=1, pos_in_round=1)
        self.assertEqual(session.post.call_count, 1)


if __name__ == "__main__":
    unittest.main()
