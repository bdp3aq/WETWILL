import unittest

from clickydraft_assistant.turn import current_overall_pick_number, infer_draft_order
from clickydraft_assistant.models import Pick


def make_pick(pick_id, fantasy_team_id):
    return Pick(
        id=pick_id,
        fantasy_team_id=fantasy_team_id,
        draftable_player_id=pick_id * 100,
        round=1,
        pos_in_round=pick_id,
        keeper=False,
        auto_drafted=False,
        delete_action=False,
        skip_action=False,
    )


class TestInferDraftOrder(unittest.TestCase):
    def test_none_until_full_round_one_seen(self):
        picks = [make_pick(1, 10), make_pick(2, 20)]
        self.assertIsNone(infer_draft_order(picks, num_teams=4))

    def test_order_from_first_n_distinct_teams(self):
        picks = [make_pick(i, team_id) for i, team_id in enumerate([10, 20, 30, 40], start=1)]
        order = infer_draft_order(picks, num_teams=4)
        self.assertEqual(order.team_order, [10, 20, 30, 40])

    def test_snake_reverses_on_even_rounds(self):
        order = infer_draft_order(
            [make_pick(i, t) for i, t in enumerate([10, 20, 30, 40], start=1)], num_teams=4
        )
        # Round 1 (picks 1-4): 10, 20, 30, 40
        self.assertEqual(order.team_on_clock(1), 10)
        self.assertEqual(order.team_on_clock(4), 40)
        # Round 2 (picks 5-8) snakes back: 40, 30, 20, 10
        self.assertEqual(order.team_on_clock(5), 40)
        self.assertEqual(order.team_on_clock(8), 10)
        # Round 3 forward again
        self.assertEqual(order.team_on_clock(9), 10)

    def test_extra_picks_beyond_first_round_dont_affect_inferred_order(self):
        picks = [make_pick(i, t) for i, t in enumerate([10, 20, 30, 40, 40, 30], start=1)]
        order = infer_draft_order(picks, num_teams=4)
        self.assertEqual(order.team_order, [10, 20, 30, 40])


class TestCurrentOverallPickNumber(unittest.TestCase):
    def test_next_pick_number(self):
        self.assertEqual(current_overall_pick_number(0), 1)
        self.assertEqual(current_overall_pick_number(5), 6)


if __name__ == "__main__":
    unittest.main()
