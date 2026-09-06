import unittest
from unittest.mock import patch

from clickydraft_assistant.turn_clock import TurnClock


class TestTurnClock(unittest.TestCase):
    def test_elapsed_is_zero_the_moment_a_pick_number_first_appears(self):
        with patch("time.monotonic", return_value=100.0):
            clock = TurnClock()
            self.assertEqual(clock.elapsed_seconds(5), 0.0)

    def test_elapsed_grows_while_pick_number_stays_the_same(self):
        clock = TurnClock()
        with patch("time.monotonic", return_value=100.0):
            clock.elapsed_seconds(5)
        with patch("time.monotonic", return_value=145.0):
            self.assertEqual(clock.elapsed_seconds(5), 45.0)
        with patch("time.monotonic", return_value=280.0):
            self.assertEqual(clock.elapsed_seconds(5), 180.0)

    def test_elapsed_resets_when_pick_number_changes(self):
        clock = TurnClock()
        with patch("time.monotonic", return_value=100.0):
            clock.elapsed_seconds(5)
        with patch("time.monotonic", return_value=200.0):
            clock.elapsed_seconds(5)  # still pick 5, 100s elapsed
        with patch("time.monotonic", return_value=205.0):
            # pick moved to 6 -- a new turn started, clock resets
            self.assertEqual(clock.elapsed_seconds(6), 0.0)
        with patch("time.monotonic", return_value=215.0):
            self.assertEqual(clock.elapsed_seconds(6), 10.0)

    def test_reverting_to_a_previously_seen_pick_number_still_resets(self):
        # Defensive: this shouldn't happen in practice (pick numbers only
        # advance), but the clock should never report stale elapsed time.
        clock = TurnClock()
        with patch("time.monotonic", return_value=100.0):
            clock.elapsed_seconds(5)
        with patch("time.monotonic", return_value=300.0):
            clock.elapsed_seconds(6)
        with patch("time.monotonic", return_value=301.0):
            self.assertEqual(clock.elapsed_seconds(5), 0.0)


if __name__ == "__main__":
    unittest.main()
