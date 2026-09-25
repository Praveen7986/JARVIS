"""
Main Application Hub & Dashboard Interface for My Widgets.
Provides a modern Windows 11 fluent dark control panel for managing,
adding, removing, and configuring desktop widgets and inspecting usage analytics.
"""

import logging
from datetime import datetime, date, timedelta
from typing import TYPE_CHECKING, Optional, Dict, Any, List

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QColor, QPainter, QBrush, QPen, QLinearGradient, QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame, QScrollArea, QGridLayout, QSlider, QComboBox,
    QCheckBox, QFileDialog, QGraphicsDropShadowEffect, QMessageBox
)

from app.utils.autostart import is_autostart_enabled, set_autostart
from app.tray import create_app_icon

if TYPE_CHECKING:
    from app.widget_manager import WidgetManager
    from app.settings import SettingsManager
    from app.storage import StorageManager
    from widgets.laptop_usage.tracker import LaptopUsageTracker

logger = logging.getLogger(__name__)


class ModernNavButton(QPushButton):
    """Sidebar navigation item with active indicator and hover styling."""

    def __init__(self, text: str, icon_str: str = "", parent=None):
        super().__init__(f"{icon_str}  {text}".strip(), parent)
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 10px;
                color: #94A3B8;
                font-size: 14px;
                font-weight: 500;
                text-align: left;
                padding-left: 16px;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.06);
                color: #FFFFFF;
            }
            QPushButton:checked {
                background-color: rgba(59, 130, 246, 0.15);
                color: #38BDF8;
                font-weight: 600;
                border-left: 3px solid #38BDF8;
            }
        """)


class ToggleSwitch(QPushButton):
    """Modern iOS/Windows 11 style toggle switch."""
    toggled_state = Signal(bool)

    def __init__(self, active: bool = False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(active)
        self.setFixedSize(48, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._on_clicked)

    def _on_clicked(self):
        self.toggled_state.emit(self.isChecked())
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        is_on = self.isChecked()
        bg_color = QColor(59, 130, 246) if is_on else QColor(51, 65, 85)
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 13, 13)

        # Handle circle
        thumb_x = self.width() - 22 if is_on else 4
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(thumb_x, 3, 20, 20)
        painter.end()


class WidgetCard(QFrame):
    """Interactive card in Widget Gallery."""
    toggle_requested = Signal(str, bool)
    configure_requested = Signal(str)

    def __init__(
        self,
        widget_id: str,
        title: str,
        category: str,
        description: str,
        icon_str: str,
        is_installed: bool = True,
        is_active: bool = False,
        parent=None
    ):
        super().__init__(parent)
        self.widget_id = widget_id
        self.is_installed = is_installed
        self.is_active = is_active

        self.setObjectName("widgetCard")
        self.setStyleSheet("""
            #widgetCard {
                background-color: rgba(30, 41, 59, 0.70);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
            }
            #widgetCard:hover {
                border-color: rgba(56, 189, 248, 0.40);
                background-color: rgba(30, 41, 59, 0.90);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Top bar: Icon, title, category badge
        top_layout = QHBoxLayout()
        top_layout.setSpacing(12)

        # Icon box
        icon_lbl = QLabel(icon_str)
        icon_lbl.setStyleSheet("""
            background-color: rgba(59, 130, 246, 0.15);
            border-radius: 12px;
            font-size: 22px;
            padding: 8px;
        """)
        icon_lbl.setFixedSize(48, 48)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_layout.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #FFFFFF; font-size: 15px; font-weight: 700; font-family: 'Segoe UI';")
        
        cat_lbl = QLabel(category.upper())
        cat_lbl.setStyleSheet("color: #38BDF8; font-size: 10px; font-weight: 700; letter-spacing: 1px;")
        title_col.addWidget(title_lbl)
        title_col.addWidget(cat_lbl)
        top_layout.addLayout(title_col)
        top_layout.addStretch()

        if is_installed:
            self.toggle = ToggleSwitch(active=is_active)
            self.toggle.toggled_state.connect(self._on_toggle_changed)
            top_layout.addWidget(self.toggle)
        else:
            badge = QLabel("Coming Soon")
            badge.setStyleSheet("""
                background-color: rgba(148, 163, 184, 0.15);
                color: #94A3B8;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 10px;
                border-radius: 8px;
            """)
            top_layout.addWidget(badge)

        layout.addLayout(top_layout)

        # Description
        desc_lbl = QLabel(description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; line-height: 1.4;")
        layout.addWidget(desc_lbl)

        layout.addStretch()

        # Bottom actions: Add/Remove Button & Configure
        if is_installed:
            bottom_layout = QHBoxLayout()
            bottom_layout.setSpacing(8)

            # Direct Add / Remove Button
            self.btn_action = QPushButton()
            self.btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_action.clicked.connect(self._on_action_btn_clicked)
            self._update_action_button()
            bottom_layout.addWidget(self.btn_action)

            bottom_layout.addStretch()

            btn_cfg = QPushButton("⚙️ Settings")
            btn_cfg.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_cfg.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.07);
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 8px;
                    color: #E2E8F0;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 6px 12px;
                }
                QPushButton:hover {
                    background-color: rgba(59, 130, 246, 0.20);
                    color: #FFFFFF;
                    border-color: #3B82F6;
                }
            """)
            btn_cfg.clicked.connect(lambda: self.configure_requested.emit(self.widget_id))
            bottom_layout.addWidget(btn_cfg)

            layout.addLayout(bottom_layout)

    def _on_action_btn_clicked(self):
        new_state = not self.is_active
        self.set_active_state(new_state)
        self.toggle_requested.emit(self.widget_id, new_state)

    def _on_toggle_changed(self, active: bool):
        self.is_active = active
        self._update_action_button()
        self.toggle_requested.emit(self.widget_id, active)

    def set_active_state(self, is_active: bool):
        self.is_active = is_active
        if hasattr(self, "toggle"):
            self.toggle.blockSignals(True)
            self.toggle.setChecked(is_active)
            self.toggle.blockSignals(False)
            self.toggle.update()
        self._update_action_button()

    def _update_action_button(self):
        if not hasattr(self, "btn_action"):
            return
        if self.is_active:
            self.btn_action.setText("✕ Remove from Desktop")
            self.btn_action.setStyleSheet("""
                QPushButton {
                    background-color: rgba(239, 68, 68, 0.15);
                    border: 1px solid rgba(239, 68, 68, 0.35);
                    border-radius: 8px;
                    color: #F87171;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 6px 14px;
                }
                QPushButton:hover {
                    background-color: rgba(239, 68, 68, 0.28);
                    color: #FFFFFF;
                }
            """)
        else:
            self.btn_action.setText("+ Add to Desktop")
            self.btn_action.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #3B82F6, stop:1 #6366F1);
                    border: none;
                    border-radius: 8px;
                    color: #FFFFFF;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 6px 14px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #2563EB, stop:1 #4F46E5);
                }
            """)


class ManageWidgetRow(QFrame):
    """Detailed row item in the Active / Manage Widgets page."""
    toggle_requested = Signal(str, bool)
    configure_requested = Signal(str)
    custom_action_requested = Signal(str)

    def __init__(
        self,
        widget_id: str,
        title: str,
        icon_str: str,
        is_active: bool,
        config: Dict[str, Any],
        custom_action_label: str = "",
        parent=None
    ):
        super().__init__(parent)
        self.widget_id = widget_id
        self.is_active = is_active
        self.config = config
        self.custom_action_label = custom_action_label

        self.setObjectName("manageRow")
        self.setStyleSheet("""
            #manageRow {
                background-color: rgba(30, 41, 59, 0.70);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 16px;
                padding: 14px;
            }
            #manageRow:hover {
                border-color: rgba(56, 189, 248, 0.35);
            }
            QLabel {
                color: #FFFFFF;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QCheckBox {
                color: #CBD5E1;
                font-size: 13px;
                spacing: 6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)

        # Header: Icon, Title, Status pill, and Main Add/Remove Button
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_lbl = QLabel(icon_str)
        icon_lbl.setStyleSheet("font-size: 20px;")
        header_layout.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #FFFFFF;")
        header_layout.addWidget(title_lbl)

        # Status badge
        self.status_badge = QLabel()
        header_layout.addWidget(self.status_badge)
        header_layout.addStretch()

        # Add or Remove Action Button
        self.btn_toggle = QPushButton()
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.clicked.connect(self._on_btn_toggle_clicked)
        header_layout.addWidget(self.btn_toggle)

        layout.addLayout(header_layout)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.07); max-height: 1px;")
        layout.addWidget(sep)

        # Controls row
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(16)

        # Always on Top
        self.chk_aot = QCheckBox("Always on Top")
        self.chk_aot.setChecked(config.get("always_on_top", True))
        ctrl_layout.addWidget(self.chk_aot)

        # Position info
        x_pos = config.get("x", 100)
        y_pos = config.get("y", 100)
        self.lbl_pos = QLabel(f"Position: ({x_pos}, {y_pos})")
        self.lbl_pos.setStyleSheet("color: #94A3B8; font-size: 12px;")
        ctrl_layout.addWidget(self.lbl_pos)

        ctrl_layout.addStretch()

        # Custom Action (e.g. Reset Time or Open Files)
        if custom_action_label:
            btn_custom = QPushButton(custom_action_label)
            btn_custom.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_custom.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.08);
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 6px;
                    color: #E2E8F0;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 5px 12px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.15);
                    color: #FFFFFF;
                }
            """)
            btn_custom.clicked.connect(lambda: self.custom_action_requested.emit(self.widget_id))
            ctrl_layout.addWidget(btn_custom)

        layout.addLayout(ctrl_layout)

        self._update_state_ui()

    def _on_btn_toggle_clicked(self):
        new_state = not self.is_active
        self.set_active(new_state)
        self.toggle_requested.emit(self.widget_id, new_state)

    def set_active(self, is_active: bool):
        self.is_active = is_active
        self._update_state_ui()

    def _update_state_ui(self):
        if self.is_active:
            self.status_badge.setText("● Active on Desktop")
            self.status_badge.setStyleSheet("""
                background-color: rgba(16, 185, 129, 0.15);
                color: #34D399;
                font-size: 11px;
                font-weight: 700;
                padding: 4px 10px;
                border-radius: 8px;
            """)
            self.btn_toggle.setText("✕ Remove from Desktop")
            self.btn_toggle.setStyleSheet("""
                QPushButton {
                    background-color: rgba(239, 68, 68, 0.15);
                    border: 1px solid rgba(239, 68, 68, 0.35);
                    border-radius: 8px;
                    color: #F87171;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 6px 14px;
                }
                QPushButton:hover {
                    background-color: rgba(239, 68, 68, 0.28);
                    color: #FFFFFF;
                }
            """)
        else:
            self.status_badge.setText("○ Hidden / Inactive")
            self.status_badge.setStyleSheet("""
                background-color: rgba(148, 163, 184, 0.12);
                color: #94A3B8;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 10px;
                border-radius: 8px;
            """)
            self.btn_toggle.setText("+ Add to Desktop")
            self.btn_toggle.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #3B82F6, stop:1 #6366F1);
                    border: none;
                    border-radius: 8px;
                    color: #FFFFFF;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 6px 14px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #2563EB, stop:1 #4F46E5);
                }
            """)


class WeeklyUsageChart(QWidget):
    """Custom graphical 7-day usage bar chart."""

    def __init__(self, usage_data: Dict[str, int], parent=None):
        super().__init__(parent)
        self.usage_data = usage_data
        self.setFixedHeight(180)

    def set_data(self, usage_data: Dict[str, int]):
        self.usage_data = usage_data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background container
        painter.setBrush(QBrush(QColor(30, 41, 59, 180)))
        painter.setPen(QPen(QColor(255, 255, 255, 20), 1))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 14, 14)

        # Generate last 7 days
        today = date.today()
        days = [today - timedelta(days=i) for i in range(6, -1, -1)]

        max_hours = 8.0
        for d in days:
            sec = self.usage_data.get(d.strftime("%Y-%m-%d"), 0)
            max_hours = max(max_hours, sec / 3600.0)

        padding_x = 30
        padding_y = 25
        chart_w = self.width() - (padding_x * 2)
        chart_h = self.height() - (padding_y * 2) - 20
        col_w = chart_w / 7.0
        bar_w = min(36.0, col_w * 0.55)

        for i, d in enumerate(days):
            d_str = d.strftime("%Y-%m-%d")
            sec = self.usage_data.get(d_str, 0)
            hours = sec / 3600.0
            ratio = min(1.0, hours / max(1.0, max_hours))
            bar_h = chart_h * ratio

            center_x = padding_x + (i * col_w) + (col_w / 2.0)
            bar_x = center_x - (bar_w / 2.0)
            bar_y = padding_y + (chart_h - bar_h)

            # Bar gradient
            grad = QLinearGradient(bar_x, bar_y, bar_x, bar_y + bar_h)
            if d == today:
                grad.setColorAt(0, QColor(56, 189, 248))
                grad.setColorAt(1, QColor(59, 130, 246))
            else:
                grad.setColorAt(0, QColor(129, 140, 248))
                grad.setColorAt(1, QColor(99, 102, 241, 160))

            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(int(bar_x), int(bar_y), int(bar_w), max(4, int(bar_h)), 6, 6)

            # Hours text above bar
            painter.setPen(QColor(226, 232, 240))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            val_str = f"{hours:.1f}h" if hours > 0 else "0"
            painter.drawText(int(center_x - 20), int(bar_y - 6), 40, 14, Qt.AlignmentFlag.AlignCenter, val_str)

            # Day label below bar
            painter.setPen(QColor(148, 163, 184) if d != today else QColor(56, 189, 248))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold if d == today else QFont.Weight.Normal))
            day_label = "Today" if d == today else d.strftime("%a")
            painter.drawText(int(center_x - 25), int(padding_y + chart_h + 8), 50, 16, Qt.AlignmentFlag.AlignCenter, day_label)

        painter.end()


class MainWindow(QMainWindow):
    """Modern Windows 11 application interface for My Widgets."""

    def __init__(
        self,
        widget_manager: 'WidgetManager',
        settings: 'SettingsManager',
        storage: 'StorageManager',
        tracker: 'LaptopUsageTracker',
        parent=None
    ):
        super().__init__(parent)
        self.widget_manager = widget_manager
        self.settings = settings
        self.storage = storage
        self.tracker = tracker

        self.setWindowTitle("My Widgets")
        self.resize(1020, 700)
        self.setMinimumSize(880, 580)
        self.setWindowIcon(create_app_icon())

        self._setup_ui()
        self._wire_events()
        self.refresh_analytics()
        self._update_status_counts()

    def _setup_ui(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0F172A;
            }
            QLabel {
                color: #E2E8F0;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(255, 255, 255, 0.04);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.25);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Left Navigation Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #131C31;
                border-right: 1px solid rgba(255, 255, 255, 0.08);
            }
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 24, 18, 24)
        sidebar_layout.setSpacing(8)

        # Brand Header
        brand_layout = QHBoxLayout()
        brand_icon = QLabel("🪟")
        brand_icon.setStyleSheet("font-size: 24px;")
        brand_layout.addWidget(brand_icon)

        brand_text_col = QVBoxLayout()
        brand_title = QLabel("My Widgets")
        brand_title.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: 700; font-family: 'Segoe UI';")
        brand_sub = QLabel("Windows 11 Platform")
        brand_sub.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600;")
        brand_text_col.addWidget(brand_title)
        brand_text_col.addWidget(brand_sub)
        brand_layout.addLayout(brand_text_col)
        sidebar_layout.addLayout(brand_layout)

        sidebar_layout.addSpacing(24)

        # Nav Buttons
        self.nav_gallery = ModernNavButton("Widget Gallery", "🧩")
        self.nav_active = ModernNavButton("Manage Widgets", "🖥️")
        self.nav_analytics = ModernNavButton("Usage Analytics", "📊")
        self.nav_settings = ModernNavButton("Settings", "⚙️")

        self.nav_buttons = [self.nav_gallery, self.nav_active, self.nav_analytics, self.nav_settings]
        for idx, btn in enumerate(self.nav_buttons):
            btn.clicked.connect(lambda checked=False, i=idx: self._switch_page(i))
            sidebar_layout.addWidget(btn)

        self.nav_gallery.setChecked(True)

        sidebar_layout.addStretch()

        # Desktop Status Box
        status_card = QFrame()
        status_card.setStyleSheet("""
            background-color: rgba(30, 41, 59, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 8px;
        """)
        sc_layout = QVBoxLayout(status_card)
        sc_layout.setContentsMargins(12, 10, 12, 10)
        sc_layout.setSpacing(4)
        sc_title = QLabel("Desktop Status")
        sc_title.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        self.sc_active_lbl = QLabel("1 Widget Active")
        self.sc_active_lbl.setStyleSheet("color: #10B981; font-size: 13px; font-weight: 700;")
        sc_layout.addWidget(sc_title)
        sc_layout.addWidget(self.sc_active_lbl)
        sidebar_layout.addWidget(status_card)

        main_layout.addWidget(sidebar)

        # 2. Right Content Area
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(32, 28, 32, 28)
        content_layout.setSpacing(20)

        # Stacked Pages
        self.stack = QStackedWidget()
        self.page_gallery = self._build_gallery_page()
        self.page_active = self._build_active_page()
        self.page_analytics = self._build_analytics_page()
        self.page_settings = self._build_settings_page()

        self.stack.addWidget(self.page_gallery)
        self.stack.addWidget(self.page_active)
        self.stack.addWidget(self.page_analytics)
        self.stack.addWidget(self.page_settings)

        content_layout.addWidget(self.stack)
        main_layout.addWidget(content_area)

    def _switch_page(self, index: int):
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        self.stack.setCurrentIndex(index)
        if index == 1:
            self._refresh_manage_page()
        elif index == 2:
            self.refresh_analytics()

    # --- Page 1: Widget Gallery ---

    def _build_gallery_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        header_layout = QHBoxLayout()
        title_col = QVBoxLayout()
        h_title = QLabel("Widget Gallery")
        h_title.setStyleSheet("font-size: 24px; font-weight: 700; color: #FFFFFF;")
        h_sub = QLabel("Browse widgets and add them directly to your desktop.")
        h_sub.setStyleSheet("font-size: 13px; color: #94A3B8;")
        title_col.addWidget(h_title)
        title_col.addWidget(h_sub)
        header_layout.addLayout(title_col)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.cards_grid = QGridLayout(scroll_content)
        self.cards_grid.setContentsMargins(0, 10, 0, 10)
        self.cards_grid.setSpacing(16)

        # 1. Laptop Usage Monitor
        is_usage_active = self.widget_manager.is_widget_visible("laptop_usage")
        self.card_laptop = WidgetCard(
            widget_id="laptop_usage",
            title="Laptop Usage Monitor",
            category="Productivity",
            description="Real-time tracking of active laptop keyboard and mouse usage with idle detection, sleep/lock handling, and midnight rollover.",
            icon_str="⏱️",
            is_installed=True,
            is_active=is_usage_active
        )
        self.card_laptop.toggle_requested.connect(self._handle_widget_toggle)
        self.card_laptop.configure_requested.connect(self._handle_widget_configure)
        self.cards_grid.addWidget(self.card_laptop, 0, 0)

        # 2. Music Player Widget
        is_music_active = self.widget_manager.is_widget_visible("music_player")
        self.card_music = WidgetCard(
            widget_id="music_player",
            title="Music Player",
            category="Audio & Media",
            description="Sleek desktop audio player with playback controls, progress seeking, volume adjustment, and local file loading.",
            icon_str="🎵",
            is_installed=True,
            is_active=is_music_active
        )
        self.card_music.toggle_requested.connect(self._handle_widget_toggle)
        self.card_music.configure_requested.connect(self._handle_widget_configure)
        self.cards_grid.addWidget(self.card_music, 0, 1)

        # 3. GitHub Activity & PR Radar
        is_github_active = self.widget_manager.is_widget_visible("github_radar")
        self.card_github = WidgetCard(
            widget_id="github_radar",
            title="GitHub Activity & PR Radar",
            category="Developer Tool",
            description="Live commit streak counter, mini contribution heatmap grid, open PR tracker, and real-time repo activity stream.",
            icon_str="🐙",
            is_installed=True,
            is_active=is_github_active
        )
        self.card_github.toggle_requested.connect(self._handle_widget_toggle)
        self.card_github.configure_requested.connect(self._handle_widget_configure)
        self.cards_grid.addWidget(self.card_github, 1, 0)

        # 4. Digital Clock & Date
        card_clock = WidgetCard(
            widget_id="clock",
            title="Digital Clock & Date",
            category="Time & Glance",
            description="Clean modern typography displaying time, world clocks, and calendar date right on your desktop.",
            icon_str="🕒",
            is_installed=False
        )
        self.cards_grid.addWidget(card_clock, 1, 1)

        # 4. System Resource HUD
        card_sys = WidgetCard(
            widget_id="system_monitor",
            title="System Resource HUD",
            category="Hardware",
            description="Real-time CPU load, memory utilization, battery health, and network telemetry.",
            icon_str="⚡",
            is_installed=False
        )
        self.cards_grid.addWidget(card_sys, 1, 1)

        # 5. Minimal Weather
        card_weather = WidgetCard(
            widget_id="weather",
            title="Minimal Weather",
            category="Forecast",
            description="Localized live temperature, forecast glance, and dynamic atmospheric conditions.",
            icon_str="⛅",
            is_installed=False
        )
        self.cards_grid.addWidget(card_weather, 2, 0)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        return page

    # --- Page 2: Manage Widgets (Add / Remove Page) ---

    def _build_active_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        h_title = QLabel("Manage Widgets")
        h_title.setStyleSheet("font-size: 24px; font-weight: 700; color: #FFFFFF;")
        h_sub = QLabel("Add or remove widgets on your desktop and adjust their individual preferences.")
        h_sub.setStyleSheet("font-size: 13px; color: #94A3B8;")
        layout.addWidget(h_title)
        layout.addWidget(h_sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.manage_content = QWidget()
        self.manage_layout = QVBoxLayout(self.manage_content)
        self.manage_layout.setContentsMargins(0, 8, 0, 8)
        self.manage_layout.setSpacing(14)

        # Build rows for installed widgets
        self._rebuild_manage_rows()

        scroll.setWidget(self.manage_content)
        layout.addWidget(scroll)
        return page

    def _rebuild_manage_rows(self):
        # Clear existing
        while self.manage_layout.count():
            item = self.manage_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 1. Laptop Usage Row
        is_usage_active = self.widget_manager.is_widget_visible("laptop_usage")
        cfg_usage = self.settings.get_widget_config("laptop_usage")
        self.row_laptop = ManageWidgetRow(
            widget_id="laptop_usage",
            title="Laptop Usage Monitor",
            icon_str="⏱️",
            is_active=is_usage_active,
            config=cfg_usage,
            custom_action_label="Reset Time"
        )
        self.row_laptop.toggle_requested.connect(self._handle_widget_toggle)
        self.row_laptop.chk_aot.toggled.connect(lambda chk: self._on_widget_aot_toggled("laptop_usage", chk))
        self.row_laptop.custom_action_requested.connect(lambda _: self.tracker.reset_today())
        self.manage_layout.addWidget(self.row_laptop)

        # 2. Music Player Row
        is_music_active = self.widget_manager.is_widget_visible("music_player")
        cfg_music = self.settings.get_widget_config("music_player")
        self.row_music = ManageWidgetRow(
            widget_id="music_player",
            title="Music Player",
            icon_str="🎵",
            is_active=is_music_active,
            config=cfg_music,
            custom_action_label="📂 Load Songs"
        )
        self.row_music.toggle_requested.connect(self._handle_widget_toggle)
        self.row_music.chk_aot.toggled.connect(lambda chk: self._on_widget_aot_toggled("music_player", chk))
        self.row_music.custom_action_requested.connect(lambda _: self._open_music_files_dialog())
        self.manage_layout.addWidget(self.row_music)

        # 3. GitHub Radar Row
        is_github_active = self.widget_manager.is_widget_visible("github_radar")
        cfg_github = self.settings.get_widget_config("github_radar")
        self.row_github = ManageWidgetRow(
            widget_id="github_radar",
            title="GitHub Activity & PR Radar",
            icon_str="🐙",
            is_active=is_github_active,
            config=cfg_github,
            custom_action_label="🔄 Sync Now"
        )
        self.row_github.toggle_requested.connect(self._handle_widget_toggle)
        self.row_github.chk_aot.toggled.connect(lambda chk: self._on_widget_aot_toggled("github_radar", chk))
        self.row_github.custom_action_requested.connect(lambda _: self._refresh_github_widget())
        self.manage_layout.addWidget(self.row_github)

        self.manage_layout.addStretch()

    def _refresh_manage_page(self):
        if hasattr(self, "row_laptop"):
            is_u = self.widget_manager.is_widget_visible("laptop_usage")
            self.row_laptop.set_active(is_u)
        if hasattr(self, "row_music"):
            is_m = self.widget_manager.is_widget_visible("music_player")
            self.row_music.set_active(is_m)
        if hasattr(self, "row_github"):
            is_g = self.widget_manager.is_widget_visible("github_radar")
            self.row_github.set_active(is_g)

    def _refresh_github_widget(self):
        widget = self.widget_manager.get_or_create_widget("github_radar")
        if widget and hasattr(widget, "refresh_data"):
            widget.refresh_data()

    def _open_music_files_dialog(self):
        widget = self.widget_manager.get_or_create_widget("music_player")
        if widget and hasattr(widget, "_open_audio_files"):
            widget._open_audio_files()

    def _on_widget_aot_toggled(self, widget_id: str, checked: bool):
        widget = self.widget_manager.get_or_create_widget(widget_id)
        if widget:
            widget.set_always_on_top(checked)

    # --- Page 3: Usage Analytics ---

    def _build_analytics_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        h_title = QLabel("Usage Analytics")
        h_title.setStyleSheet("font-size: 24px; font-weight: 700; color: #FFFFFF;")
        h_sub = QLabel("Historical metrics and daily productivity stats.")
        h_sub.setStyleSheet("font-size: 13px; color: #94A3B8;")
        layout.addWidget(h_title)
        layout.addWidget(h_sub)

        # KPI Summary cards
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(14)

        self.kpi_today = self._create_kpi_card("Today's Active Usage", "0h 00m", "#38BDF8")
        self.kpi_avg = self._create_kpi_card("7-Day Daily Avg", "0h 00m", "#818CF8")
        self.kpi_total = self._create_kpi_card("Total Recorded", "0h 00m", "#10B981")

        kpi_layout.addWidget(self.kpi_today)
        kpi_layout.addWidget(self.kpi_avg)
        kpi_layout.addWidget(self.kpi_total)
        layout.addLayout(kpi_layout)

        # 7-Day Chart
        chart_title = QLabel("Past 7 Days Breakdown")
        chart_title.setStyleSheet("font-size: 15px; font-weight: 600; color: #FFFFFF; margin-top: 10px;")
        layout.addWidget(chart_title)

        self.chart = WeeklyUsageChart(usage_data={})
        layout.addWidget(self.chart)

        layout.addStretch()
        return page

    def _create_kpi_card(self, title: str, val: str, color_hex: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            background-color: rgba(30, 41, 59, 0.70);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 14px;
            padding: 14px;
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(4)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 600;")
        lbl_v = QLabel(val)
        lbl_v.setObjectName("valLabel")
        lbl_v.setStyleSheet(f"color: {color_hex}; font-size: 24px; font-weight: 700; font-family: 'Segoe UI';")
        c_layout.addWidget(lbl_t)
        c_layout.addWidget(lbl_v)
        return card

    # --- Page 4: Settings ---

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        h_title = QLabel("Application Settings")
        h_title.setStyleSheet("font-size: 24px; font-weight: 700; color: #FFFFFF;")
        h_sub = QLabel("Configure global platform options and startup behavior.")
        h_sub.setStyleSheet("font-size: 13px; color: #94A3B8;")
        layout.addWidget(h_title)
        layout.addWidget(h_sub)

        # Settings Box
        box = QFrame()
        box.setStyleSheet("""
            background-color: rgba(30, 41, 59, 0.70);
            border: 1px solid rgba(255, 255, 255, 0.10);
            border-radius: 16px;
            padding: 20px;
        """)
        b_layout = QVBoxLayout(box)
        b_layout.setSpacing(16)

        # Autostart checkbox
        self.chk_global_autostart = QCheckBox("Start My Widgets automatically when Windows boots")
        self.chk_global_autostart.setChecked(is_autostart_enabled())
        self.chk_global_autostart.toggled.connect(self._on_autostart_toggled)
        self.chk_global_autostart.setStyleSheet("color: #FFFFFF; font-size: 14px;")
        b_layout.addWidget(self.chk_global_autostart)

        # Idle Threshold dropdown
        row = QHBoxLayout()
        lbl = QLabel("Laptop Usage Idle Detection Threshold:")
        lbl.setStyleSheet("color: #E2E8F0; font-size: 13px;")
        self.combo_idle = QComboBox()
        self.combo_idle.addItem("1 minute", 60)
        self.combo_idle.addItem("5 minutes (Recommended)", 300)
        self.combo_idle.addItem("10 minutes", 600)
        self.combo_idle.addItem("15 minutes", 900)
        self.combo_idle.addItem("30 minutes", 1800)

        cfg = self.settings.get_widget_config("laptop_usage")
        current_t = cfg.get("idle_threshold_seconds", 300)
        for i in range(self.combo_idle.count()):
            if self.combo_idle.itemData(i) == current_t:
                self.combo_idle.setCurrentIndex(i)
                break
        self.combo_idle.currentIndexChanged.connect(self._on_idle_threshold_changed)
        self.combo_idle.setStyleSheet("""
            QComboBox {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 4px 10px;
                color: #FFFFFF;
                min-width: 180px;
            }
            QComboBox QAbstractItemView {
                background-color: #1E293B;
                selection-background-color: #3B82F6;
                color: #FFFFFF;
            }
        """)
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(self.combo_idle)
        b_layout.addLayout(row)

        layout.addWidget(box)
        layout.addStretch()
        return page

    # --- Event Handlers & Sync ---

    def _wire_events(self):
        self.widget_manager.widget_visibility_changed.connect(self._sync_widget_state)
        self.tracker.usage_updated.connect(self._on_tracker_usage_updated)

    def _handle_widget_toggle(self, widget_id: str, is_active: bool):
        if is_active:
            self.widget_manager.show_widget(widget_id)
        else:
            self.widget_manager.hide_widget(widget_id)
        self._update_status_counts()

    def _handle_widget_configure(self, widget_id: str):
        if widget_id == "laptop_usage":
            widget = self.widget_manager.get_or_create_widget("laptop_usage")
            if widget and hasattr(widget, "open_settings_dialog"):
                widget.open_settings_dialog()
        elif widget_id == "music_player":
            self._open_music_files_dialog()
        elif widget_id == "github_radar":
            widget = self.widget_manager.get_or_create_widget("github_radar")
            if widget and hasattr(widget, "open_settings_dialog"):
                widget.open_settings_dialog()

    def _sync_widget_state(self, widget_id: str, is_visible: bool):
        if widget_id == "laptop_usage":
            if hasattr(self, "card_laptop"):
                self.card_laptop.set_active_state(is_visible)
            if hasattr(self, "row_laptop"):
                self.row_laptop.set_active(is_visible)
        elif widget_id == "music_player":
            if hasattr(self, "card_music"):
                self.card_music.set_active_state(is_visible)
            if hasattr(self, "row_music"):
                self.row_music.set_active(is_visible)
        elif widget_id == "github_radar":
            if hasattr(self, "card_github"):
                self.card_github.set_active_state(is_visible)
            if hasattr(self, "row_github"):
                self.row_github.set_active(is_visible)

        self._update_status_counts()

    def _update_status_counts(self):
        count = 0
        if self.widget_manager.is_widget_visible("laptop_usage"):
            count += 1
        if self.widget_manager.is_widget_visible("music_player"):
            count += 1
        if self.widget_manager.is_widget_visible("github_radar"):
            count += 1
        self.sc_active_lbl.setText(f"{count} Active" if count == 1 else f"{count} Active")

    def _on_autostart_toggled(self, checked: bool):
        set_autostart(checked)
        self.settings.set_start_with_windows(checked)

    def _on_idle_threshold_changed(self, index: int):
        val = self.combo_idle.currentData()
        self.tracker.set_idle_threshold(val)
        self.settings.update_widget_config("laptop_usage", {"idle_threshold_seconds": val})

    def _on_tracker_usage_updated(self, total_sec: int, is_active: bool, formatted: str, date_str: str):
        today_lbl = self.kpi_today.findChild(QLabel, "valLabel")
        if today_lbl:
            today_lbl.setText(formatted)

    def refresh_analytics(self):
        """Re-reads usage records and redraws charts & metrics."""
        usage_data = self.storage.load_usage_data()
        data_map = {}
        total_all_time = 0

        for d_str, entry in usage_data.items():
            sec = entry.get("usage_seconds", 0)
            data_map[d_str] = sec
            total_all_time += sec

        today_str = date.today().strftime("%Y-%m-%d")
        live_today_sec = self.tracker.get_current_usage_seconds()
        data_map[today_str] = live_today_sec

        days_7 = [date.today() - timedelta(days=i) for i in range(7)]
        sec_7 = sum(data_map.get(d.strftime("%Y-%m-%d"), 0) for d in days_7)
        avg_7_sec = sec_7 // 7

        self.kpi_today.findChild(QLabel, "valLabel").setText(self.tracker.format_duration(live_today_sec))
        self.kpi_avg.findChild(QLabel, "valLabel").setText(self.tracker.format_duration(avg_7_sec))
        self.kpi_total.findChild(QLabel, "valLabel").setText(f"{total_all_time // 3600}h {(total_all_time % 3600) // 60}m")

        self.chart.set_data(data_map)

    def closeEvent(self, event):
        """Minimize to background/tray on close without stopping widgets."""
        event.ignore()
        self.hide()

    def show_and_raise(self):
        """Brings the dashboard window to the front."""
        self.show()
        self.raise_()
        self.activateWindow()
        self.refresh_analytics()
        self._refresh_manage_page()
