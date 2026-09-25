"""Unit tests for LaptopUsageTracker and duration formatting."""

import tempfile
import time
import shutil
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication
from app.storage import StorageManager
from widgets.laptop_usage.tracker import LaptopUsageTracker

# Create headless QApplication for QObject signals / timers in tests
app = QApplication.instance() or QApplication([])


class TestTracker(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage = StorageManager(data_dir=Path(self.temp_dir))
        self.tracker = LaptopUsageTracker(
            storage=self.storage,
            power_watcher=None,
            idle_threshold_seconds=5
        )

    def tearDown(self):
        self.tracker.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_format_duration(self):
        self.assertEqual(LaptopUsageTracker.format_duration(0), "00:00")
        self.assertEqual(LaptopUsageTracker.format_duration(125), "02:05")
        self.assertEqual(LaptopUsageTracker.format_duration(600), "0h 10m")
        self.assertEqual(LaptopUsageTracker.format_duration(3600), "1h 00m")
        self.assertEqual(LaptopUsageTracker.format_duration(20538), "5h 42m")

    def test_active_idle_transition(self):
        # Initial state
        self.assertEqual(self.tracker.get_current_usage_seconds(), 0)

        # Simulate user active
        now = time.time()
        self.tracker._transition_to_active(now=now, idle_seconds=0.5)
        self.assertTrue(self.tracker.is_active)

        # Advance time by 3 seconds
        self.tracker.active_start_time = now - 3.0
        self.assertGreaterEqual(self.tracker.get_current_usage_seconds(), 3)

        # Transition to idle (user was idle for 2 seconds)
        self.tracker._transition_to_idle(idle_seconds=2.0)
        self.assertFalse(self.tracker.is_active)

    def test_midnight_rollover(self):
        # Set usage for yesterday
        self.tracker.current_date_str = "2026-09-21"
        self.tracker.persisted_today_seconds = 7200
        self.tracker.is_active = False

        # Trigger midnight rollover
        self.tracker._handle_midnight_rollover("2026-09-22")

        # Today should be 0
        self.assertEqual(self.tracker.current_date_str, "2026-09-22")
        self.assertEqual(self.tracker.persisted_today_seconds, 0)
        self.assertEqual(self.tracker.get_current_usage_seconds(), 0)

        # Yesterday's data must be preserved in storage
        self.assertEqual(self.storage.get_day_usage("2026-09-21"), 7200)
        self.assertEqual(self.storage.get_day_usage("2026-09-22"), 0)


if __name__ == "__main__":
    unittest.main()
