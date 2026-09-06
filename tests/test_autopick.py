import unittest

from clickydraft_assistant.autopick import evaluate_autopick
from clickydraft_assistant.models import Player
from clickydraft_assistant.ranking import RankedPlayer
from clickydraft_assistant.turn import DraftOrder


def ranked(pid, has_projection=True, score=10.0):
    player = Player(draftable_player_id=pid, first_name="P", last_name=str(pid), positions=["WR"])
    return RankedPlayer(
        player=player,
        projected_points=score,
        replacement_points=0.0,
        vor=score,
        need_bonus=0.0,
        final_score=score,
        has_projection=has_projection,
    )


class TestEvaluateAutopick(unittest.TestCase):
    def setUp(self):
        self.order = DraftOrder(team_order=[10, 20, 30, 40])
        self.top = [ranked(1, score=20.0), ranked(2, score=10.0)]

    def _evaluate(self, **overrides):
        kwargs = dict(
            my_team_id=10,
            draft_order=self.order,
            overall_pick_number=1,
            elapsed_seconds_on_turn=200.0,
            wait_seconds=180.0,
            top_available=self.top,
            enabled=True,
        )
        kwargs.update(overrides)
        return evaluate_autopick(**kwargs)

    def test_disabled_never_fires(self):
        decision = self._evaluate(enabled=False)
        self.assertFalse(decision.should_fire)

    def test_no_team_id_never_fires(self):
        decision = self._evaluate(my_team_id=None)
        self.assertFalse(decision.should_fire)

    def test_no_draft_order_yet_never_fires(self):
        decision = self._evaluate(draft_order=None)
        self.assertFalse(decision.should_fire)

    def test_not_my_turn_never_fires(self):
        decision = self._evaluate(overall_pick_number=2)  # team 20's slot
        self.assertFalse(decision.should_fire)

    def test_just_became_my_turn_does_not_fire_immediately(self):
        decision = self._evaluate(elapsed_seconds_on_turn=0.0)
        self.assertFalse(decision.should_fire)

    def test_not_enough_idle_time_yet_does_not_fire(self):
        decision = self._evaluate(elapsed_seconds_on_turn=90.0, wait_seconds=180.0)
        self.assertFalse(decision.should_fire)

    def test_no_real_projection_available_never_fires(self):
        decision = self._evaluate(top_available=[ranked(1, has_projection=False)])
        self.assertFalse(decision.should_fire)

    def test_fires_once_idle_threshold_reached(self):
        decision = self._evaluate(elapsed_seconds_on_turn=180.0, wait_seconds=180.0)
        self.assertTrue(decision.should_fire)
        self.assertEqual(decision.player.player.draftable_player_id, 1)

    def test_fires_when_well_past_threshold(self):
        decision = self._evaluate(elapsed_seconds_on_turn=300.0, wait_seconds=180.0)
        self.assertTrue(decision.should_fire)

    def test_skips_fallback_only_players_for_top_pick(self):
        # Best-scored entry has no real projection; only the second one does.
        top = [ranked(1, has_projection=False), ranked(2, has_projection=True, score=5.0)]
        decision = self._evaluate(top_available=top)
        self.assertTrue(decision.should_fire)
        self.assertEqual(decision.player.player.draftable_player_id, 2)


if __name__ == "__main__":
    unittest.main()
