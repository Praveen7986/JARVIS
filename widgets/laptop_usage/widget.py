"""
Laptop Usage Widget UI Component.
Renders the frameless dark-glass Windows 11 widget showing active usage,
status indicator (Active/Idle), daily progress bar, and right-click actions.
"""

import logging
from typing import Optional
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont, QAction, QColor, QPainter, QBrush, QPen
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QFrame,
    QMenu, QMessageBox, QWidget
)
from app.base_widget import BaseWidget
from .tracker import LaptopUsageTracker
from .settings_dialog import LaptopUsageSettingsDialog

logger = logging.getLogger(__name__)


class ModernProgressBar(QProgressBar):
    """Custom sleek progress bar with rounded corners and gradient fill."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextVisible(False)
        self.setFixedHeight(6)
        self.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.10);
                border-radius: 3px;
                border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #38BDF8, stop:1 #818CF8);
                border-radius: 3px;
            }
        """)


class LaptopUsageWidget(BaseWidget):
    """
    Frameless, draggable desktop widget displaying laptop active usage time.
    """

    def __init__(self, widget_id: str = "laptop_usage", widget_manager=None, tracker: Optional[LaptopUsageTracker] = None, parent=None):
        self.tracker = tracker
        super().__init__(widget_id=widget_id, widget_manager=widget_manager, parent=parent)

        self._setup_ui()
        self._wire_tracker()
        self.load_state()

    def get_display_title(self) -> str:
        return "Laptop Usage"

    def set_tracker(self, tracker: LaptopUsageTracker):
        """Attaches tracker to this widget and connects signals."""
        self.tracker = tracker
        self._wire_tracker()

    def _wire_tracker(self):
        if not self.tracker:
            return
        self.tracker.usage_updated.connect(self._on_usage_updated)
        self.tracker.status_changed.connect(self._on_status_changed)

    def _setup_ui(self):
        self.resize(320, 180)
        self.setMinimumSize(280, 160)

        # Outer layout
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(12, 12, 12, 12)

        # Card container with glassmorphism style
        self.card = QFrame(self)
        self.card.setObjectName("cardFrame")
        self.card.setStyleSheet("""
            #cardFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(24, 27, 36, 0.88),
                    stop:1 rgba(14, 16, 22, 0.94));
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 18px;
            }
        """)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(8)

        # 1. Header Bar: Title & Status Indicator
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)

        self.title_label = QLabel("LAPTOP USAGE")
        self.title_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.55);
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.5px;
            font-family: 'Segoe UI', system-ui, sans-serif;
        """)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        # Status badge (Active / Idle)
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #10B981; font-size: 10px; margin-right: -2px;")
        self.status_text = QLabel("Active")
        self.status_text.setStyleSheet("""
            color: #10B981;
            font-size: 11px;
            font-weight: 600;
            font-family: 'Segoe UI', system-ui, sans-serif;
        """)
        header_layout.addWidget(self.status_dot)
        header_layout.addWidget(self.status_text)
        card_layout.addLayout(header_layout)

        # 2. Main Duration Counter
        self.time_label = QLabel("00:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.time_label.setStyleSheet("""
            color: #FFFFFF;
            font-size: 38px;
            font-weight: 700;
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            margin-top: -4px;
            margin-bottom: -4px;
        """)
        card_layout.addWidget(self.time_label)

        # 3. Progress bar (24 hours = 100%)
        self.progress_bar = ModernProgressBar(self.card)
        self.progress_bar.setRange(0, 86400)  # 86400 seconds in 24 hours
        self.progress_bar.setValue(0)
        card_layout.addWidget(self.progress_bar)

        # 4. Footer info: "Today" and fractional indicator
        footer_layout = QHBoxLayout()
        self.footer_today_label = QLabel("Today")
        self.footer_today_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.45);
            font-size: 11px;
            font-weight: 500;
            font-family: 'Segoe UI', system-ui, sans-serif;
        """)

        self.footer_ratio_label = QLabel("0h 00m / 24h")
        self.footer_ratio_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.45);
            font-size: 11px;
            font-weight: 500;
            font-family: 'Segoe UI', system-ui, sans-serif;
        """)

        footer_layout.addWidget(self.footer_today_label)
        footer_layout.addStretch()
        footer_layout.addWidget(self.footer_ratio_label)
        card_layout.addLayout(footer_layout)

        outer_layout.addWidget(self.card)

    # --- Signal Handlers from Tracker ---

    @Slot(int, bool, str, str)
    def _on_usage_updated(self, total_seconds: int, is_active: bool, formatted_time: str, date_str: str):
        # Update main counter
        self.time_label.setText(formatted_time)

        # Update progress bar (clamped to 24h)
        self.progress_bar.setValue(min(86400, total_seconds))

        # Update footer ratio
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        self.footer_ratio_label.setText(f"{hours}h {minutes:02d}m / 24h")

        # Update status
        self._update_status_ui(is_active)

    @Slot(bool)
    def _on_status_changed(self, is_active: bool):
        self._update_status_ui(is_active)

    def _update_status_ui(self, is_active: bool):
        if is_active:
            self.status_dot.setText("●")
            self.status_dot.setStyleSheet("color: #10B981; font-size: 10px;")
            self.status_text.setText("Active")
            self.status_text.setStyleSheet("color: #10B981; font-size: 11px; font-weight: 600;")
        else:
            self.status_dot.setText("○")
            self.status_dot.setStyleSheet("color: #94A3B8; font-size: 10px;")
            self.status_text.setText("Idle")
            self.status_text.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 500;")

    # --- Custom Context Menu Actions ---

    def add_custom_menu_actions(self, menu: QMenu):
        # Reset today's data action
        reset_action = menu.addAction("Reset Today's Data")
        reset_action.triggered.connect(self._confirm_reset_data)

    def _confirm_reset_data(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Reset Today's Data")
        msg.setText("Are you sure you want to reset today's active usage to 00:00?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #1E222B;
                color: #FFFFFF;
            }
            QLabel {
                color: #FFFFFF;
            }
            QPushButton {
                background-color: #3B82F6;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 6px 14px;
            }
        """)
        if msg.exec() == QMessageBox.StandardButton.Yes:
            if self.tracker:
                self.tracker.reset_today()

    def open_settings_dialog(self):
        """Opens the settings modal for this widget."""
        cfg = {}
        if self.widget_manager and self.widget_manager.settings:
            cfg = self.widget_manager.settings.get_widget_config(self.widget_id)

        dlg = LaptopUsageSettingsDialog(cfg, parent=self)
        dlg.settings_applied.connect(self._on_settings_applied)
        dlg.exec()

    def _on_settings_applied(self, new_settings: dict):
        # Update tracker idle threshold
        if self.tracker and "idle_threshold_seconds" in new_settings:
            self.tracker.set_idle_threshold(new_settings["idle_threshold_seconds"])

        # Update widget visual properties
        if "always_on_top" in new_settings:
            self.set_always_on_top(new_settings["always_on_top"])
        if "opacity" in new_settings:
            self.set_opacity(new_settings["opacity"])

        # Update settings manager
        if self.widget_manager and self.widget_manager.settings:
            self.widget_manager.settings.update_widget_config(self.widget_id, new_settings)
            self.widget_manager.settings.set_start_with_windows(new_settings.get("start_with_windows", False))
