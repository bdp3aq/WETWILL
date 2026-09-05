import unittest

from clickydraft_assistant.models import Pick, Player, Team
from clickydraft_assistant.state import DraftState


def player_payload(draftable_player_id, name="Test Player", position="RB"):
    return {
        "id": draftable_player_id + 90000,
        "draftablePlayerId": draftable_player_id,
        "firstName": name.split()[0],
        "lastName": name.split()[-1],
        "positions": [position],
        "teamAbbr": "XXX",
        "byeWeek": 7,
    }


def pick_payload(
    pick_id,
    fantasy_team_id,
    draftable_player_id,
    keeper=False,
    delete_action=False,
    skip_action=False,
    round_=1,
):
    return {
        "id": pick_id,
        "fantasyTeamId": fantasy_team_id,
        "draftablePlayerId": draftable_player_id,
        "draftablePlayer": player_payload(draftable_player_id),
        "round": round_,
        "posInRound": 1,
        "keeper": keeper,
        "autoDrafted": False,
        "deleteAction": delete_action,
        "skipAction": skip_action,
    }


def make_state(num_players=5):
    players = [Player.from_api(player_payload(i)) for i in range(1, num_players + 1)]
    teams = [Team(id=100, team_name="Bradley's Team"), Team(id=200, team_name="Rival Team")]
    return DraftState(players=players, teams=teams)


class TestKeeperIngestion(unittest.TestCase):
    def test_keeper_picks_removed_from_pool_and_credited_to_roster(self):
        state = make_state()
        keeper_picks = [Pick.from_api(pick_payload(1, 100, 1, keeper=True))]
        count = state.ingest_keepers(keeper_picks)
        self.assertEqual(count, 1)
        self.assertNotIn(1, state.available_player_ids)
        self.assertEqual(len(state.roster_players(100)), 1)

    def test_non_keeper_picks_ignored_at_ingest(self):
        state = make_state()
        picks = [Pick.from_api(pick_payload(1, 100, 1, keeper=False))]
        count = state.ingest_keepers(picks)
        self.assertEqual(count, 0)
        self.assertIn(1, state.available_player_ids)


class TestPickDiffing(unittest.TestCase):
    def test_new_real_pick_is_applied(self):
        state = make_state()
        events = state.update([Pick.from_api(pick_payload(1, 100, 1))])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kind, "pick")
        self.assertNotIn(1, state.available_player_ids)

    def test_skip_action_pick_does_not_consume_player(self):
        state = make_state()
        events = state.update([Pick.from_api(pick_payload(1, 100, 1, skip_action=True))])
        self.assertEqual(len(events), 0)
        self.assertIn(1, state.available_player_ids)

    def test_delete_action_undoes_a_previously_applied_pick(self):
        state = make_state()
        state.update([Pick.from_api(pick_payload(1, 100, 1))])
        self.assertNotIn(1, state.available_player_ids)

        events = state.update([Pick.from_api(pick_payload(1, 100, 1, delete_action=True))])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kind, "undo")
        self.assertIn(1, state.available_player_ids)
        self.assertEqual(len(state.roster_players(100)), 0)

    def test_repolling_same_pick_is_not_double_counted(self):
        state = make_state()
        pick = Pick.from_api(pick_payload(1, 100, 1))
        state.update([pick])
        events = state.update([pick])
        self.assertEqual(len(events), 0)
        self.assertEqual(len(state.roster_players(100)), 1)

    def test_multiple_picks_across_polls(self):
        state = make_state()
        state.update([Pick.from_api(pick_payload(1, 100, 1))])
        events = state.update(
            [
                Pick.from_api(pick_payload(1, 100, 1)),
                Pick.from_api(pick_payload(2, 200, 2)),
            ]
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].pick.draftable_player_id, 2)
        self.assertEqual(len(state.available_players()), 3)


if __name__ == "__main__":
    unittest.main()
