import unittest

from clickydraft_assistant.scoring import ScoringSettings, score_dst, score_kicker, score_offense, score_player


class TestOffenseScoring(unittest.TestCase):
    def setUp(self):
        self.settings = ScoringSettings()

    def test_basic_qb_line(self):
        stats = {"pass_comp": 24, "pass_yds": 300, "pass_td": 3, "pass_int": 1}
        expected = 24 * 0.125 + 300 / 20 + 3 * 5 + 1 * -2
        self.assertAlmostEqual(score_offense(stats, self.settings), expected)

    def test_passing_yardage_bonus_threshold(self):
        under = score_offense({"pass_yds": 554}, self.settings)
        over = score_offense({"pass_yds": 555}, self.settings)
        # Crossing the threshold adds a flat +20 on top of the per-yard rate.
        self.assertAlmostEqual(over - under, 20 + 1 / 20)

    def test_rushing_yardage_bonuses_stack(self):
        # 297 yards crosses all three rushing bonus thresholds (100, 200, 297).
        points = score_offense({"rush_yds": 297}, self.settings)
        expected = 297 / 10 + 3 + 3 + 20
        self.assertAlmostEqual(points, expected)

    def test_receiving_yardage_bonus_at_100_only(self):
        points = score_offense({"rec_yds": 150}, self.settings)
        expected = 150 / 10 + 4
        self.assertAlmostEqual(points, expected)

    def test_reception_and_fumble_values(self):
        points = score_offense({"rec": 5, "fumbles_lost": 1}, self.settings)
        self.assertAlmostEqual(points, 5 * 0.33 - 2)

    def test_missing_stats_default_to_zero(self):
        self.assertEqual(score_offense({}, self.settings), 0.0)


class TestKickerScoring(unittest.TestCase):
    def test_field_goal_buckets_and_pat(self):
        stats = {"fg_0_19": 1, "fg_30_39": 2, "fg_50_plus": 1, "fg_miss": 3, "pat_made": 4, "pat_miss": 1}
        settings = ScoringSettings()
        expected = 1 * 1 + 2 * 3 + 1 * 5 + 3 * 0 + 4 * 1 + 1 * 0
        self.assertAlmostEqual(score_kicker(stats, settings), expected)


class TestDSTScoring(unittest.TestCase):
    def setUp(self):
        self.settings = ScoringSettings()

    def test_points_allowed_tiers(self):
        cases = {
            0: 12.75,
            3: 8.5,
            6: 8.5,
            7: 5.97,
            13: 5.97,
            14: 2.55,
            20: 2.55,
            21: 0.85,
            27: 0.85,
            28: 0.0,
            34: 0.0,
            35: -2.0,
            50: -2.0,
        }
        for points_allowed, expected in cases.items():
            with self.subTest(points_allowed=points_allowed):
                self.assertAlmostEqual(
                    score_dst({"points_allowed": points_allowed}, self.settings), expected
                )

    def test_defensive_td_and_block_kick_values(self):
        stats = {"sacks": 3, "def_int": 2, "def_td": 1, "block_kick": 1}
        expected = 3 * 1 + 2 * 2 + 1 * 5.1 + 1 * 1.7
        self.assertAlmostEqual(score_dst(stats, self.settings), expected)


class TestScorePlayerDispatch(unittest.TestCase):
    def test_dispatches_by_position(self):
        settings = ScoringSettings()
        self.assertAlmostEqual(
            score_player("K", {"pat_made": 2}, settings), score_kicker({"pat_made": 2}, settings)
        )
        self.assertAlmostEqual(
            score_player("DST", {"sacks": 1}, settings), score_dst({"sacks": 1}, settings)
        )
        self.assertAlmostEqual(
            score_player("RB", {"rush_yds": 50}, settings), score_offense({"rush_yds": 50}, settings)
        )


if __name__ == "__main__":
    unittest.main()
