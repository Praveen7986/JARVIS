"""Unit tests for StorageManager and SettingsManager."""

import tempfile
import os
import shutil
import unittest
from pathlib import Path
from app.storage import StorageManager
from app.settings import SettingsManager, DEFAULT_SETTINGS


class TestStorageAndSettings(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage = StorageManager(data_dir=Path(self.temp_dir))
        self.settings = SettingsManager(self.storage)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_usage_save_and_retrieve(self):
        date_str = "2026-09-22"
        self.assertEqual(self.storage.get_day_usage(date_str), 0)

        self.storage.set_day_usage(date_str, 3600)
        self.assertEqual(self.storage.get_day_usage(date_str), 3600)

        # Update
        self.storage.set_day_usage(date_str, 5400)
        self.assertEqual(self.storage.get_day_usage(date_str), 5400)

    def test_corrupted_json_recovery(self):
        # Write corrupted content to usage_data.json
        with open(self.storage.usage_file, "w", encoding="utf-8") as f:
            f.write("{invalid_json: true, broken...")

        # Should recover cleanly without crashing and return empty dict
        data = self.storage.load_usage_data()
        self.assertIsInstance(data, dict)
        self.assertEqual(len(data), 0)

    def test_settings_persistence(self):
        self.assertTrue(self.settings.is_first_launch())
        self.settings.set_first_launch(False)
        self.assertFalse(self.settings.is_first_launch())

        # Widget config
        cfg = self.settings.get_widget_config("laptop_usage")
        self.assertEqual(cfg["idle_threshold_seconds"], 300)

        self.settings.update_widget_config("laptop_usage", {"idle_threshold_seconds": 600})
        updated = self.settings.get_widget_config("laptop_usage")
        self.assertEqual(updated["idle_threshold_seconds"], 600)


if __name__ == "__main__":
    unittest.main()
