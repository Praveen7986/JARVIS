"""Unit tests for Music Player widget and AudioPlayerEngine."""

import unittest
from PySide6.QtWidgets import QApplication
from widgets.music_player.player import AudioPlayerEngine
from widgets.music_player.widget import MusicPlayerWidget

app = QApplication.instance() or QApplication([])


class TestMusicPlayer(unittest.TestCase):

    def setUp(self):
        self.engine = AudioPlayerEngine()

    def test_engine_initial_playlist(self):
        self.assertGreaterEqual(len(self.engine.playlist), 1)
        cur = self.engine.current_track()
        self.assertIsNotNone(cur)
        self.assertIn("title", cur)

    def test_engine_next_prev_tracks(self):
        initial_idx = self.engine.current_index
        self.engine.next_track()
        self.assertEqual(self.engine.current_index, (initial_idx + 1) % len(self.engine.playlist))

        self.engine.previous_track()
        self.assertEqual(self.engine.current_index, initial_idx)

    def test_time_formatting(self):
        self.assertEqual(AudioPlayerEngine.format_time(0), "00:00")
        self.assertEqual(AudioPlayerEngine.format_time(65000), "01:05")
        self.assertEqual(AudioPlayerEngine.format_time(214000), "03:34")

    def test_widget_instantiation(self):
        widget = MusicPlayerWidget(widget_id="music_player", engine=self.engine)
        self.assertEqual(widget.get_display_title(), "Music Player")
        self.assertIsNotNone(widget.lbl_title)
        self.assertIsNotNone(widget.lbl_artist)


if __name__ == "__main__":
    unittest.main()
