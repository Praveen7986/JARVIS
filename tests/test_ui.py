"""Integration tests verifying full UI and App initialization."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication
from app.storage import StorageManager
from app.settings import SettingsManager
from app.widget_manager import WidgetManager
from app.tray import AppTrayIcon, create_app_icon
from widgets.laptop_usage.widget import LaptopUsageWidget
from widgets.laptop_usage.settings_dialog import LaptopUsageSettingsDialog
from widgets.laptop_usage.tracker import LaptopUsageTracker

app = QApplication.instance() or QApplication([])


class TestUIAndComponents(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage = StorageManager(data_dir=Path(self.temp_dir))
        self.settings = SettingsManager(self.storage)
        self.tracker = LaptopUsageTracker(storage=self.storage, idle_threshold_seconds=10)
        self.widget_manager = WidgetManager(self.settings, self.storage)
        self.widget_manager.register_widget_type(
            "laptop_usage",
            lambda widget_id, widget_manager: LaptopUsageWidget(
                widget_id=widget_id, widget_manager=widget_manager, tracker=self.tracker
            )
        )

    def tearDown(self):
        self.tracker.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_icon_generation(self):
        icon = create_app_icon(64)
        self.assertFalse(icon.isNull())

    def test_tray_initialization(self):
        tray = AppTrayIcon(self.widget_manager, self.settings)
        self.assertIsNotNone(tray.contextMenu())

    def test_widget_creation_and_signals(self):
        widget = LaptopUsageWidget(
            widget_id="laptop_usage",
            widget_manager=self.widget_manager,
            tracker=self.tracker
        )
        self.assertEqual(widget.get_display_title(), "Laptop Usage")

        # Simulate update
        widget._on_usage_updated(3600, True, "1h 00m", "2026-09-22")
        self.assertEqual(widget.time_label.text(), "1h 00m")
        self.assertEqual(widget.status_text.text(), "Active")

        widget._on_status_changed(False)
        self.assertEqual(widget.status_text.text(), "Idle")

    def test_settings_dialog(self):
        cfg = self.settings.get_widget_config("laptop_usage")
        dialog = LaptopUsageSettingsDialog(cfg)
        self.assertEqual(dialog.threshold_combo.currentData(), 300)

    def test_main_window_tabs_and_toggles(self):
        from app.main_window import MainWindow
        win = MainWindow(self.widget_manager, self.settings, self.storage, self.tracker)
        self.assertEqual(win.stack.count(), 4)

        # Switch to Analytics
        win._switch_page(2)
        self.assertEqual(win.stack.currentIndex(), 2)

        # Toggle widget from main window
        win._handle_widget_toggle("laptop_usage", True)
        self.assertTrue(self.widget_manager.is_widget_visible("laptop_usage"))

        win._handle_widget_toggle("laptop_usage", False)
        self.assertFalse(self.widget_manager.is_widget_visible("laptop_usage"))


if __name__ == "__main__":
    unittest.main()
