import unittest

from clickydraft_assistant.models import Player
from clickydraft_assistant.roster import compute_roster_needs


def make_player(position: str, pid: int) -> Player:
    return Player(draftable_player_id=pid, first_name="P", last_name=str(pid), positions=[position])


class TestRosterNeeds(unittest.TestCase):
    def test_empty_roster_needs_everything(self):
        needs = compute_roster_needs([])
        self.assertEqual(needs.open_starter_slots["QB"], 1)
        self.assertEqual(needs.open_starter_slots["WR"], 2)
        self.assertEqual(needs.open_starter_slots["RB"], 2)
        self.assertEqual(needs.open_starter_slots["TE"], 1)
        self.assertEqual(needs.open_starter_slots["K"], 1)
        self.assertEqual(needs.open_starter_slots["DEF"], 1)
        self.assertEqual(needs.open_flex_slots, 1)
        self.assertEqual(needs.bench_slots_filled, 0)

    def test_extra_wr_fills_flex_not_bench(self):
        roster = [make_player("WR", 1), make_player("WR", 2), make_player("WR", 3)]
        needs = compute_roster_needs(roster)
        self.assertEqual(needs.open_starter_slots["WR"], 0)
        self.assertEqual(needs.open_flex_slots, 0)
        self.assertEqual(needs.bench_slots_filled, 0)

    def test_fourth_wr_goes_to_bench_once_flex_is_full(self):
        roster = [make_player("WR", i) for i in range(4)]
        needs = compute_roster_needs(roster)
        self.assertEqual(needs.open_starter_slots["WR"], 0)
        self.assertEqual(needs.open_flex_slots, 0)
        self.assertEqual(needs.bench_slots_filled, 1)

    def test_full_starting_lineup_reports_no_open_starters(self):
        roster = (
            [make_player("QB", 1)]
            + [make_player("WR", i) for i in range(2, 4)]
            + [make_player("RB", i) for i in range(4, 6)]
            + [make_player("TE", 6)]
            + [make_player("K", 7)]
            + [make_player("DEF", 8)]
        )
        needs = compute_roster_needs(roster)
        self.assertTrue(all(v == 0 for v in needs.open_starter_slots.values()))
        self.assertEqual(needs.open_flex_slots, 1)
        self.assertFalse(needs.needs_position("QB"))
        self.assertTrue(needs.flex_open_for("RB"))
        self.assertFalse(needs.flex_open_for("QB"))

    def test_dst_alias_normalizes_to_def(self):
        roster = [make_player("DST", 1)]
        needs = compute_roster_needs(roster)
        self.assertEqual(needs.open_starter_slots["DEF"], 0)


if __name__ == "__main__":
    unittest.main()
