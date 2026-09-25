"""Unit tests for GitHub Contribution Calendar Widget and Service."""

import unittest
from unittest.mock import patch, MagicMock
from PySide6.QtWidgets import QApplication
from widgets.github_radar.github_service import fetch_github_data, fetch_github_calendar_html
from widgets.github_radar.widget import GitHubRadarWidget, FullContributionCalendarView

app = QApplication.instance() or QApplication([])


class TestGitHubRadar(unittest.TestCase):

    def test_full_calendar_view(self):
        view = FullContributionCalendarView()
        sample_days = [
            {"date": "2026-09-20", "level": 0, "count": 0, "tooltip": "No contributions"},
            {"date": "2026-09-21", "level": 1, "count": 2, "tooltip": "2 contributions"},
            {"date": "2026-09-22", "level": 2, "count": 5, "tooltip": "5 contributions"},
            {"date": "2026-09-23", "level": 4, "count": 17, "tooltip": "17 contributions"},
        ]
        month_pos = [{"month": "Sep", "col": 0}]
        view.set_data(sample_days, month_pos, theme="emerald")
        self.assertEqual(len(view.days_data), 4)
        self.assertEqual(len(view.month_positions), 1)

    @patch("urllib.request.urlopen")
    def test_fetch_calendar_html(self, mock_urlopen):
        sample_html = b"""
        <h2>21 contributions in 2026</h2>
        <table><tbody>
            <tr>
                <td data-date="2026-08-05" data-level="4" id="c1"></td>
                <td data-date="2026-09-16" data-level="4" id="c2"></td>
            </tr>
        </tbody></table>
        <tool-tip for="c1">2 contributions on August 5th.</tool-tip>
        <tool-tip for="c2">17 contributions on September 16th.</tool-tip>
        """
        mock_resp = MagicMock()
        mock_resp.read.return_value = sample_html
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        res = fetch_github_calendar_html("Praveen7986")
        self.assertEqual(res["total_contributions"], 21)
        self.assertEqual(len(res["days"]), 2)
        self.assertEqual(res["days"][0]["level"], 4)
        self.assertEqual(res["days"][1]["count"], 17)

    def test_widget_instantiation(self):
        widget = GitHubRadarWidget(widget_id="github_radar")
        self.assertEqual(widget.get_display_title(), "GitHub Contribution Calendar")
        self.assertIsNotNone(widget.card_frame)
        self.assertIsNotNone(widget.calendar_view)
        self.assertIsNotNone(widget.lbl_total_header)


if __name__ == "__main__":
    unittest.main()
