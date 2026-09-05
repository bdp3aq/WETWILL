import unittest

from clickydraft_assistant.models import Player
from clickydraft_assistant.projections import ProjectionLookup, ProjectionSource
from clickydraft_assistant.ranking import rank_available_players
from clickydraft_assistant.roster import compute_roster_needs


class FakeProjectionSource(ProjectionSource):
    def __init__(self, stats_by_id):
        self.stats_by_id = stats_by_id

    def get_stats(self, player):
        return self.stats_by_id.get(player.draftable_player_id)


def make_player(pid, position, name=None):
    name = name or f"Player{pid}"
    return Player(draftable_player_id=pid, first_name=name, last_name="X", positions=[position])


class FakeFallbackSource:
    def __init__(self, rank_by_id):
        self.rank_by_id = rank_by_id

    def get_rank(self, player):
        return self.rank_by_id.get(player.draftable_player_id)


class TestRanking(unittest.TestCase):
    def test_higher_projected_points_ranks_first_within_position(self):
        players = [make_player(1, "RB"), make_player(2, "RB")]
        stats = {1: {"rush_yds": 100}, 2: {"rush_yds": 50}}
        lookup = ProjectionLookup(csv_source=FakeProjectionSource(stats))
        ranked = rank_available_players(players, lookup, num_teams=14)
        self.assertEqual(ranked[0].player.draftable_player_id, 1)

    def test_players_without_projection_rank_last(self):
        players = [make_player(1, "RB"), make_player(2, "RB")]
        stats = {1: {"rush_yds": 10}}
        lookup = ProjectionLookup(csv_source=FakeProjectionSource(stats))
        ranked = rank_available_players(players, lookup, num_teams=14)
        self.assertEqual(ranked[0].player.draftable_player_id, 1)
        self.assertFalse(ranked[1].has_projection)

    def test_need_bonus_can_flip_ranking_of_close_players(self):
        # RB2 is slightly better on raw points, but Bradley has no open WR slot
        # and does have an open RB slot filled elsewhere in this test via needs.
        rb = make_player(1, "RB")
        wr = make_player(2, "WR")
        stats = {1: {"rush_yds": 100}, 2: {"rec_yds": 105}}  # ~10 vs ~10.5 points, WR slightly ahead
        lookup = ProjectionLookup(csv_source=FakeProjectionSource(stats))

        # Roster already has 2 WRs and flex filled by a WR -> WR need is fully satisfied,
        # but RB slots are still open.
        roster = [make_player(10, "WR"), make_player(11, "WR"), make_player(12, "WR")]
        needs = compute_roster_needs(roster)
        self.assertTrue(needs.needs_position("RB"))
        self.assertFalse(needs.needs_position("WR"))
        self.assertFalse(needs.flex_open_for("WR"))

        ranked = rank_available_players([rb, wr], lookup, roster_needs=needs, num_teams=14)
        self.assertEqual(ranked[0].player.draftable_player_id, 1)  # RB wins due to need bonus

    def test_replacement_level_reduces_vor_in_deep_position(self):
        # 20 RBs where the top one is only slightly ahead of a deep, similar pool
        # -> small VOR. Two QBs where QB1 is far ahead of QB2 (the QB replacement
        # level) -> large VOR, even though QB1's raw points are similar to the top RB.
        rbs = [make_player(i, "RB") for i in range(1, 21)]
        qb1 = make_player(100, "QB")
        qb2 = make_player(101, "QB")
        stats = {i: {"rush_yds": 100} for i in range(1, 21)}
        stats[1] = {"rush_yds": 105}  # top RB, only marginally ahead of the deep pool
        stats[100] = {"pass_yds": 500}  # QB1, far ahead of the only other QB
        stats[101] = {"pass_yds": 100}  # QB2, the QB replacement level
        lookup = ProjectionLookup(csv_source=FakeProjectionSource(stats))

        ranked = rank_available_players(rbs + [qb1, qb2], lookup, num_teams=14)
        qb1_entry = next(r for r in ranked if r.player.draftable_player_id == 100)
        top_rb_entry = next(r for r in ranked if r.player.draftable_player_id == 1)
        self.assertGreater(qb1_entry.vor, top_rb_entry.vor)


class TestFallbackRankingNeverOutranksRealProjection(unittest.TestCase):
    def test_fallback_only_orders_players_without_a_projection(self):
        # Player 1 has a weak but real projection; player 2 has none but a
        # great (rank 1) ADP fallback rank. The real projection must still win.
        weak_real = make_player(1, "WR")
        strong_adp_no_stats = make_player(2, "WR")
        stats = {1: {"rec_yds": 10}}  # tiny real projection
        lookup = ProjectionLookup(csv_source=FakeProjectionSource(stats))
        fallback = FakeFallbackSource({2: 1.0})  # best possible ADP rank

        ranked = rank_available_players(
            [weak_real, strong_adp_no_stats], lookup, num_teams=14, fallback_source=fallback
        )
        self.assertEqual(ranked[0].player.draftable_player_id, 1)
        self.assertTrue(ranked[0].has_projection)
        self.assertFalse(ranked[1].has_projection)

    def test_fallback_players_ordered_by_rank_among_themselves(self):
        p1 = make_player(1, "WR")
        p2 = make_player(2, "WR")
        lookup = ProjectionLookup(csv_source=FakeProjectionSource({}))
        fallback = FakeFallbackSource({1: 50.0, 2: 5.0})

        ranked = rank_available_players([p1, p2], lookup, num_teams=14, fallback_source=fallback)
        self.assertEqual(ranked[0].player.draftable_player_id, 2)  # better (lower) ADP rank first
        self.assertEqual(ranked[1].player.draftable_player_id, 1)

    def test_player_with_neither_projection_nor_fallback_ranks_last(self):
        has_fallback = make_player(1, "WR")
        has_nothing = make_player(2, "WR")
        lookup = ProjectionLookup(csv_source=FakeProjectionSource({}))
        fallback = FakeFallbackSource({1: 10.0})

        ranked = rank_available_players([has_fallback, has_nothing], lookup, num_teams=14, fallback_source=fallback)
        self.assertEqual(ranked[0].player.draftable_player_id, 1)
        self.assertEqual(ranked[1].player.draftable_player_id, 2)


if __name__ == "__main__":
    unittest.main()
