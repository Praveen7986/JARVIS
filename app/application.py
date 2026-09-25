"""
Central Application Controller for My Widgets.
Manages lifecycle, widget manager, tracker engine, system tray, and first-launch onboarding.
"""

import logging
import sys
from PySide6.QtCore import Qt, QAbstractNativeEventFilter
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QPushButton, QFrame,
    QGraphicsDropShadowEffect
)
from PySide6.QtGui import QFont, QColor
from .storage import StorageManager
from .settings import SettingsManager
from .widget_manager import WidgetManager
from .tray import AppTrayIcon
from .utils.win_power import PowerSessionWatcher
from .main_window import MainWindow
from widgets.laptop_usage.tracker import LaptopUsageTracker
from widgets.laptop_usage.widget import LaptopUsageWidget
from widgets.laptop_usage.settings_dialog import LaptopUsageSettingsDialog
from widgets.music_player.widget import MusicPlayerWidget
from widgets.github_radar.widget import GitHubRadarWidget

logger = logging.getLogger(__name__)


class WinEventFilter(QAbstractNativeEventFilter):
    """Native event filter to capture Windows Power Broadcast and Session changes."""

    def __init__(self, watcher: PowerSessionWatcher):
        super().__init__()
        self.watcher = watcher

    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            # On Windows, message is MSG struct pointer
            import ctypes
            from ctypes import wintypes

            class MSG(ctypes.Structure):
                _fields_ = [
                    ("hwnd", wintypes.HWND),
                    ("message", wintypes.UINT),
                    ("wParam", wintypes.WPARAM),
                    ("lParam", wintypes.LPARAM),
                    ("time", wintypes.DWORD),
                    ("pt", wintypes.POINT),
                ]

            try:
                msg = MSG.from_address(int(message))
                self.watcher.handle_native_event(msg.message, msg.wParam, msg.lParam)
            except Exception:
                pass
        return False, 0


class WelcomeDialog(QDialog):
    """First-launch onboarding modal."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to My Widgets")
        self.setFixedSize(380, 260)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._setup_ui()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)

        container = QFrame(self)
        container.setObjectName("welcomeContainer")
        container.setStyleSheet("""
            #welcomeContainer {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(28, 32, 44, 0.98),
                    stop:1 rgba(16, 18, 26, 0.98));
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 18px;
            }
            QLabel {
                color: #FFFFFF;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3B82F6, stop:1 #6366F1);
                border: none;
                border-radius: 10px;
                color: #FFFFFF;
                font-weight: 600;
                font-size: 14px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2563EB, stop:1 #4F46E5);
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 220))
        shadow.setOffset(0, 10)
        container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        title = QLabel("My Widgets")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(title)

        subtitle = QLabel("Welcome to your desktop dashboard")
        subtitle.setStyleSheet("color: #38BDF8; font-size: 13px; font-weight: 600;")
        layout.addWidget(subtitle)

        desc = QLabel("Your widgets will appear directly on your desktop and track your daily laptop usage in real-time.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94A3B8; font-size: 12px; line-height: 1.4;")
        layout.addWidget(desc)

        layout.addStretch()

        btn_add = QPushButton("Add Laptop Usage Widget")
        btn_add.clicked.connect(self.accept)
        layout.addWidget(btn_add)

        root_layout.addWidget(container)


class MyWidgetsApp:
    """Master Application Coordinator."""

    def __init__(self, qapp: QApplication):
        self.qapp = qapp
        self.qapp.setQuitOnLastWindowClosed(False)

        # 1. Storage & Settings
        self.storage = StorageManager()
        self.settings = SettingsManager(self.storage)

        # 2. Power & Session Watcher
        self.power_watcher = PowerSessionWatcher()
        self.native_event_filter = WinEventFilter(self.power_watcher)
        self.qapp.installNativeEventFilter(self.native_event_filter)

        # 3. Laptop Usage Tracker
        cfg = self.settings.get_widget_config("laptop_usage")
        idle_thresh = cfg.get("idle_threshold_seconds", 300)
        self.tracker = LaptopUsageTracker(
            storage=self.storage,
            power_watcher=self.power_watcher,
            idle_threshold_seconds=idle_thresh
        )

        # 4. Widget Manager
        self.widget_manager = WidgetManager(self.settings, self.storage)
        self._register_widgets()

        # 5. Main Application Hub Window
        self.main_window = MainWindow(
            widget_manager=self.widget_manager,
            settings=self.settings,
            storage=self.storage,
            tracker=self.tracker
        )

        # 6. System Tray
        self.tray = AppTrayIcon(self.widget_manager, self.settings)
        self.tray.settings_clicked.connect(self.show_main_window)
        self.tray.exit_clicked.connect(self.quit)
        self.tray.show()

    def _register_widgets(self):
        """Register widget factories for laptop_usage and music_player."""
        def create_laptop_widget(widget_id: str, widget_manager):
            widget = LaptopUsageWidget(widget_id=widget_id, widget_manager=widget_manager, tracker=self.tracker)
            widget.settings_requested.connect(self._open_laptop_settings)
            return widget

        def create_music_widget(widget_id: str, widget_manager):
            widget = MusicPlayerWidget(widget_id=widget_id, widget_manager=widget_manager)
            widget.settings_requested.connect(self.show_main_window)
            return widget

        def create_github_widget(widget_id: str, widget_manager):
            widget = GitHubRadarWidget(widget_id=widget_id, widget_manager=widget_manager)
            widget.settings_requested.connect(self.show_main_window)
            return widget

        self.widget_manager.register_widget_type("laptop_usage", create_laptop_widget)
        self.widget_manager.register_widget_type("music_player", create_music_widget)
        self.widget_manager.register_widget_type("github_radar", create_github_widget)

    def run(self):
        """Initializes and launches the main application dashboard and widgets."""
        self.tracker.start()

        # Show the main application interface
        self.main_window.show_and_raise()

        # Restore active widgets on desktop
        if not self.settings.is_first_launch():
            self.widget_manager.show_all_active()
        else:
            # First launch: enable laptop usage widget by default
            self.settings.set_first_launch(False)
            self.widget_manager.show_widget("laptop_usage")

    def show_main_window(self):
        """Brings the main application window to the front."""
        self.main_window.show_and_raise()

    def _open_laptop_settings(self, widget_id: str = "laptop_usage"):
        self.show_main_window()

    def _open_general_settings(self):
        self.show_main_window()

    def quit(self):
        """Clean shutdown."""
        logger.info("Quitting My Widgets...")
        self.tracker.stop()
        self.widget_manager.hide_all()
        self.main_window.hide()
        self.tray.hide()
        self.qapp.quit()
