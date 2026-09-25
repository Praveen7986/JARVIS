"""
Settings Dialog for GitHub Activity & PR Radar Widget.
Allows configuring username, optional Personal Access Token, refresh interval,
heatmap theme, always-on-top, and opacity.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QCheckBox, QSlider, QPushButton, QFrame, QGraphicsDropShadowEffect
)


class GitHubSettingsDialog(QDialog):
    """Modern Windows 11 styled modal dialog for configuring GitHub widget."""

    settings_applied = Signal(dict)

    def __init__(self, current_config: dict, parent=None):
        super().__init__(parent)
        self.current_config = dict(current_config)

        self.setWindowTitle("GitHub Radar Settings")
        self.setFixedSize(380, 520)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)

        container = QFrame(self)
        container.setObjectName("dialogContainer")
        container.setStyleSheet("""
            #dialogContainer {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(28, 32, 44, 0.98),
                    stop:1 rgba(16, 18, 26, 0.98));
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 16px;
            }
            QLabel {
                color: #E2E8F0;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 6px 10px;
                color: #FFFFFF;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #38BDF8;
                background-color: rgba(255, 255, 255, 0.10);
            }
            QComboBox {
                background-color: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 6px 12px;
                color: #FFFFFF;
                font-size: 13px;
                min-height: 20px;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background-color: #1E222B;
                border: 1px solid rgba(255, 255, 255, 0.15);
                selection-background-color: #3B82F6;
                color: #FFFFFF;
                border-radius: 6px;
                outline: none;
            }
            QCheckBox {
                color: #E2E8F0;
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 5px;
                border: 1px solid rgba(255, 255, 255, 0.25);
                background-color: rgba(255, 255, 255, 0.05);
            }
            QCheckBox::indicator:checked {
                background-color: #3B82F6;
                border-color: #60A5FA;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: rgba(255, 255, 255, 0.15);
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #3B82F6;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                border: 2px solid #3B82F6;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, 6)
        container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        # Header Title
        title_box = QHBoxLayout()
        icon_lbl = QLabel("🐙")
        icon_lbl.setFont(QFont("Segoe UI", 16))
        title_box.addWidget(icon_lbl)

        title_lbl = QLabel("GitHub Radar Settings")
        title_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #FFFFFF;")
        title_box.addWidget(title_lbl)
        title_box.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(24, 24)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #94A3B8;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #EF4444;
            }
        """)
        btn_close.clicked.connect(self.reject)
        title_box.addWidget(btn_close)
        layout.addLayout(title_box)

        # 1. GitHub Username
        lbl_user = QLabel("GitHub Username / Handle")
        lbl_user.setStyleSheet("font-weight: 600; font-size: 12px; color: #38BDF8;")
        layout.addWidget(lbl_user)

        self.input_username = QLineEdit()
        self.input_username.setPlaceholderText("e.g. Praveen7986 (or leave blank if using token)")
        layout.addWidget(self.input_username)

        # 2. Personal Access Token (Optional)
        lbl_token = QLabel("Personal Access Token / Secret Key (Optional)")
        lbl_token.setStyleSheet("font-weight: 600; font-size: 12px; color: #94A3B8;")
        layout.addWidget(lbl_token)

        self.input_token = QLineEdit()
        self.input_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_token.setPlaceholderText("ghp_... or github_pat_... (auto-detects user & private repos)")
        layout.addWidget(self.input_token)

        # 3. Refresh Interval & Heatmap Theme Row
        row_settings = QHBoxLayout()
        row_settings.setSpacing(10)

        col_refresh = QVBoxLayout()
        lbl_ref = QLabel("Sync Interval")
        lbl_ref.setStyleSheet("font-size: 12px; color: #94A3B8; font-weight: 600;")
        self.combo_interval = QComboBox()
        self.combo_interval.addItems(["5 Minutes", "15 Minutes", "30 Minutes", "60 Minutes"])
        col_refresh.addWidget(lbl_ref)
        col_refresh.addWidget(self.combo_interval)
        row_settings.addLayout(col_refresh)

        col_theme = QVBoxLayout()
        lbl_th = QLabel("Heatmap Theme")
        lbl_th.setStyleSheet("font-size: 12px; color: #94A3B8; font-weight: 600;")
        self.combo_theme = QComboBox()
        self.combo_theme.addItem("Classic Emerald", "emerald")
        self.combo_theme.addItem("Cyber Blue", "cyber_blue")
        self.combo_theme.addItem("Solar Amber", "solar_amber")
        col_theme.addWidget(lbl_th)
        col_theme.addWidget(self.combo_theme)
        row_settings.addLayout(col_theme)

        layout.addLayout(row_settings)

        # 4. Always on Top Checkbox
        self.chk_aot = QCheckBox("Keep widget Always on Top")
        layout.addWidget(self.chk_aot)

        # 5. Opacity Slider
        lbl_op = QLabel("Widget Opacity")
        lbl_op.setStyleSheet("font-size: 12px; color: #94A3B8; font-weight: 600;")
        layout.addWidget(lbl_op)

        slider_row = QHBoxLayout()
        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(40, 100)
        self.slider_opacity.setValue(95)

        self.lbl_opacity_val = QLabel("95%")
        self.lbl_opacity_val.setFixedWidth(36)
        self.lbl_opacity_val.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 600;")

        self.slider_opacity.valueChanged.connect(lambda v: self.lbl_opacity_val.setText(f"{v}%"))
        slider_row.addWidget(self.slider_opacity)
        slider_row.addWidget(self.lbl_opacity_val)
        layout.addLayout(slider_row)

        layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                color: #94A3B8;
                font-weight: 600;
                padding: 9px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.14);
                color: #FFFFFF;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("Save Changes")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3B82F6, stop:1 #6366F1);
                border: none;
                border-radius: 8px;
                color: #FFFFFF;
                font-weight: 600;
                padding: 9px 18px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2563EB, stop:1 #4F46E5);
            }
        """)
        btn_save.clicked.connect(self._on_save_clicked)
        btn_layout.addWidget(btn_save)

        layout.addLayout(btn_layout)
        root_layout.addWidget(container)

    def _load_values(self):
        self.input_username.setText(self.current_config.get("username", "torvalds"))
        self.input_token.setText(self.current_config.get("token", ""))

        # Interval
        minutes = self.current_config.get("refresh_interval", 15)
        interval_map = {5: 0, 15: 1, 30: 2, 60: 3}
        self.combo_interval.setCurrentIndex(interval_map.get(minutes, 1))

        # Theme
        theme_val = self.current_config.get("theme", "emerald")
        theme_idx = self.combo_theme.findData(theme_val)
        if theme_idx >= 0:
            self.combo_theme.setCurrentIndex(theme_idx)

        # AOT & Opacity
        self.chk_aot.setChecked(self.current_config.get("always_on_top", True))
        op_val = int(self.current_config.get("opacity", 0.95) * 100)
        self.slider_opacity.setValue(op_val)
        self.lbl_opacity_val.setText(f"{op_val}%")

    def _on_save_clicked(self):
        intervals = [5, 15, 30, 60]
        selected_interval = intervals[self.combo_interval.currentIndex()]
        selected_theme = self.combo_theme.currentData()

        new_config = {
            "username": self.input_username.text().strip(),
            "token": self.input_token.text().strip(),
            "refresh_interval": selected_interval,
            "theme": selected_theme,
            "always_on_top": self.chk_aot.isChecked(),
            "opacity": self.slider_opacity.value() / 100.0,
        }
        self.settings_applied.emit(new_config)
        self.accept()
