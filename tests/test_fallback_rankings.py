import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openpyxl import Workbook

from clickydraft_assistant.fallback_rankings import XlsxAdpFallback
from clickydraft_assistant.models import Player


def make_player(pid, name):
    first, last = name.split(" ", 1)
    return Player(draftable_player_id=pid, first_name=first, last_name=last, positions=["WR"])


class TestXlsxAdpFallback(unittest.TestCase):
    def _write_workbook(self, path, sheet_rows):
        wb = Workbook()
        wb.remove(wb.active)
        for sheet_name, rows in sheet_rows.items():
            ws = wb.create_sheet(sheet_name)
            for row in rows:
                ws.append(row)
        wb.save(path)

    def test_reads_rank_from_repeating_column_blocks(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "rankings.xlsx"
            rows = [
                [None, "Player", None, "ADP", None, "Player", None, "ADP"],
                [None, 1, "Justin Jefferson", 1.2, None, 25, "Deebo Samuel", 30.1],
                [None, 2, "Breece Hall*", 2.5, None, 26, "Someone Else", 40.0],
            ]
            self._write_workbook(path, {"Full PPR": rows})

            fallback = XlsxAdpFallback(path)
            self.assertEqual(fallback.get_rank(make_player(1, "Justin Jefferson")), 1.0)
            self.assertEqual(fallback.get_rank(make_player(2, "Deebo Samuel")), 25.0)

    def test_strips_rookie_asterisk_for_matching(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "rankings.xlsx"
            rows = [[None, 2, "Breece Hall*", 2.5]]
            self._write_workbook(path, {"Full PPR": rows})

            fallback = XlsxAdpFallback(path)
            self.assertEqual(fallback.get_rank(make_player(1, "Breece Hall")), 2.0)

    def test_averages_rank_across_sheets(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "rankings.xlsx"
            self._write_workbook(
                path,
                {
                    "Full PPR": [[None, 10, "Player One", 12.0]],
                    "12 PPR": [[None, 20, "Player One", 22.0]],
                },
            )
            fallback = XlsxAdpFallback(path)
            self.assertEqual(fallback.get_rank(make_player(1, "Player One")), 15.0)

    def test_unknown_player_returns_none(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "rankings.xlsx"
            self._write_workbook(path, {"Full PPR": [[None, 1, "Someone", 1.0]]})
            fallback = XlsxAdpFallback(path)
            self.assertIsNone(fallback.get_rank(make_player(99, "Nobody Here")))

    def test_missing_file_yields_no_ranks(self):
        fallback = XlsxAdpFallback("/nonexistent/path.xlsx")
        self.assertIsNone(fallback.get_rank(make_player(1, "Anyone Here")))


if __name__ == "__main__":
    unittest.main()
