"""
Windows System Tray integration for My Widgets.
"""

import logging
from typing import TYPE_CHECKING
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu

if TYPE_CHECKING:
    from .widget_manager import WidgetManager
    from .settings import SettingsManager

logger = logging.getLogger(__name__)


def create_app_icon(size: int = 64) -> QIcon:
    """Generates a clean vector-rendered desktop widget icon."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Background rounded square
    painter.setBrush(QBrush(QColor(24, 27, 36)))
    painter.setPen(QPen(QColor(56, 189, 248), 2))
    painter.drawRoundedRect(4, 4, size - 8, size - 8, 12, 12)

    # Inner widget bars
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(56, 189, 248)))
    painter.drawRoundedRect(12, 16, size - 24, 8, 4, 4)

    painter.setBrush(QBrush(QColor(129, 140, 248)))
    painter.drawRoundedRect(12, 28, int((size - 24) * 0.6), 6, 3, 3)

    painter.setBrush(QBrush(QColor(16, 185, 129)))
    painter.drawEllipse(size - 22, size - 22, 10, 10)

    painter.end()
    return QIcon(pixmap)


class AppTrayIcon(QSystemTrayIcon):
    """System tray icon and context menu."""

    settings_clicked = Signal()
    exit_clicked = Signal()

    def __init__(self, widget_manager: 'WidgetManager', settings: 'SettingsManager', parent=None):
        self.app_icon = create_app_icon()
        super().__init__(self.app_icon, parent)
        self.widget_manager = widget_manager
        self.settings = settings

        self.setToolTip("My Widgets")
        self._build_menu()
        self.activated.connect(self._on_tray_activated)

        # Update checkmarks when widget visibility changes
        self.widget_manager.widget_visibility_changed.connect(self._sync_menu_state)

    def _build_menu(self):
        self.tray_menu = QMenu()
        self.tray_menu.setStyleSheet("""
            QMenu {
                background-color: #1A1D24;
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3B82F6;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.10);
                margin: 4px 8px;
            }
        """)

        # Title & Open Dashboard
        title_action = self.tray_menu.addAction("My Widgets")
        title_action.setEnabled(False)
        
        open_dash_action = self.tray_menu.addAction("🪟 Open Dashboard")
        open_dash_action.triggered.connect(self.settings_clicked.emit)
        self.tray_menu.addSeparator()

        # Laptop usage widget toggle
        self.action_laptop_usage = QAction("Laptop Usage", self.tray_menu, checkable=True)
        self.action_laptop_usage.setChecked(self.widget_manager.is_widget_visible("laptop_usage"))
        self.action_laptop_usage.toggled.connect(lambda checked: self._toggle_widget("laptop_usage", checked))
        self.tray_menu.addAction(self.action_laptop_usage)

        # Music player widget toggle
        self.action_music_player = QAction("Music Player", self.tray_menu, checkable=True)
        self.action_music_player.setChecked(self.widget_manager.is_widget_visible("music_player"))
        self.action_music_player.toggled.connect(lambda checked: self._toggle_widget("music_player", checked))
        self.tray_menu.addAction(self.action_music_player)

        # GitHub radar widget toggle
        self.action_github_radar = QAction("GitHub Radar", self.tray_menu, checkable=True)
        self.action_github_radar.setChecked(self.widget_manager.is_widget_visible("github_radar"))
        self.action_github_radar.toggled.connect(lambda checked: self._toggle_widget("github_radar", checked))
        self.tray_menu.addAction(self.action_github_radar)

        self.tray_menu.addSeparator()

        # Show / Hide all
        show_all_action = self.tray_menu.addAction("Show Widgets")
        show_all_action.triggered.connect(self.widget_manager.show_all)

        hide_all_action = self.tray_menu.addAction("Hide Widgets")
        hide_all_action.triggered.connect(self.widget_manager.hide_all)

        settings_action = self.tray_menu.addAction("Settings")
        settings_action.triggered.connect(self.settings_clicked.emit)

        self.tray_menu.addSeparator()

        exit_action = self.tray_menu.addAction("Exit")
        exit_action.triggered.connect(self.exit_clicked.emit)

        self.setContextMenu(self.tray_menu)

    def _toggle_widget(self, widget_id: str, checked: bool):
        if checked:
            self.widget_manager.show_widget(widget_id)
        else:
            self.widget_manager.hide_widget(widget_id)

    def _sync_menu_state(self, widget_id: str, is_visible: bool):
        if widget_id == "laptop_usage":
            self.action_laptop_usage.blockSignals(True)
            self.action_laptop_usage.setChecked(is_visible)
            self.action_laptop_usage.blockSignals(False)
        elif widget_id == "music_player":
            self.action_music_player.blockSignals(True)
            self.action_music_player.setChecked(is_visible)
            self.action_music_player.blockSignals(False)
        elif widget_id == "github_radar":
            self.action_github_radar.blockSignals(True)
            self.action_github_radar.setChecked(is_visible)
            self.action_github_radar.blockSignals(False)

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.settings_clicked.emit()
