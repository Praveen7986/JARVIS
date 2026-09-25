"""
Settings Dialog for Laptop Usage Monitor widget.
Provides controls for idle threshold, autostart, always-on-top, and opacity.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QSlider, QPushButton, QFrame, QGraphicsDropShadowEffect
)
from app.utils.autostart import is_autostart_enabled, set_autostart


class LaptopUsageSettingsDialog(QDialog):
    """Modern Windows 11 styled modal dialog for configuring widget settings."""

    settings_applied = Signal(dict)

    def __init__(self, current_config: dict, parent=None):
        super().__init__(parent)
        self.current_config = dict(current_config)

        self.setWindowTitle("Laptop Usage Settings")
        self.setFixedSize(360, 420)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        # Outer container for rounded border & glass background
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)

        container = QFrame(self)
        container.setObjectName("dialogContainer")
        container.setStyleSheet("""
            #dialogContainer {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(28, 30, 38, 0.96),
                    stop:1 rgba(18, 20, 26, 0.98));
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 16px;
            }
            QLabel {
                color: #E2E8F0;
                font-family: 'Segoe UI', system-ui, sans-serif;
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
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #3B82F6;
                border: none;
                border-radius: 8px;
                color: #FFFFFF;
                font-weight: 600;
                font-size: 13px;
                padding: 8px 18px;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
            QPushButton:pressed {
                background-color: #1D4ED8;
            }
            QPushButton#btnCancel {
                background-color: rgba(255, 255, 255, 0.08);
                color: #94A3B8;
            }
            QPushButton#btnCancel:hover {
                background-color: rgba(255, 255, 255, 0.15);
                color: #FFFFFF;
            }
        """)

        # Drop shadow for dialog
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, 8)
        container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Title
        title_label = QLabel("Laptop Usage Settings")
        title_font = QFont("Segoe UI", 14, QFont.Weight.Bold)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); max-height: 1px;")
        layout.addWidget(sep)

        # 1. Idle Threshold Section
        thresh_label = QLabel("Idle Threshold:")
        thresh_label.setStyleSheet("font-size: 12px; color: #94A3B8; font-weight: 600;")
        layout.addWidget(thresh_label)

        self.threshold_combo = QComboBox()
        self.threshold_combo.addItem("1 minute", 60)
        self.threshold_combo.addItem("5 minutes (Default)", 300)
        self.threshold_combo.addItem("10 minutes", 600)
        self.threshold_combo.addItem("15 minutes", 900)
        self.threshold_combo.addItem("30 minutes", 1800)
        layout.addWidget(self.threshold_combo)

        # 2. Checkboxes
        self.chk_autostart = QCheckBox("Start My Widgets with Windows")
        layout.addWidget(self.chk_autostart)

        self.chk_aot = QCheckBox("Always on top")
        layout.addWidget(self.chk_aot)

        # 3. Opacity Slider Section
        opacity_header = QHBoxLayout()
        opacity_label = QLabel("Widget Opacity:")
        opacity_label.setStyleSheet("font-size: 12px; color: #94A3B8; font-weight: 600;")
        self.opacity_val_label = QLabel("95%")
        self.opacity_val_label.setStyleSheet("color: #38BDF8; font-weight: 600; font-size: 12px;")
        opacity_header.addWidget(opacity_label)
        opacity_header.addStretch()
        opacity_header.addWidget(self.opacity_val_label)
        layout.addLayout(opacity_header)

        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(40, 100)
        self.slider_opacity.setValue(95)
        self.slider_opacity.valueChanged.connect(self._on_opacity_slider_changed)
        layout.addWidget(self.slider_opacity)

        layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("btnCancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save Changes")
        self.btn_save.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)
        root_layout.addWidget(container)

    def _on_opacity_slider_changed(self, value: int):
        self.opacity_val_label.setText(f"{value}%")

    def _load_values(self):
        # Idle threshold
        threshold = self.current_config.get("idle_threshold_seconds", 300)
        index = 1 # default 5m
        for i in range(self.threshold_combo.count()):
            if self.threshold_combo.itemData(i) == threshold:
                index = i
                break
        self.threshold_combo.setCurrentIndex(index)

        # Autostart
        self.chk_autostart.setChecked(is_autostart_enabled())

        # Always on top
        self.chk_aot.setChecked(self.current_config.get("always_on_top", True))

        # Opacity
        opacity = int(self.current_config.get("opacity", 0.95) * 100)
        self.slider_opacity.setValue(opacity)
        self.opacity_val_label.setText(f"{opacity}%")

    def _save_settings(self):
        selected_threshold = self.threshold_combo.currentData()
        autostart = self.chk_autostart.isChecked()
        always_on_top = self.chk_aot.isChecked()
        opacity = self.slider_opacity.value() / 100.0

        # Update registry autostart
        set_autostart(autostart)

        result = {
            "idle_threshold_seconds": selected_threshold,
            "always_on_top": always_on_top,
            "opacity": opacity,
            "start_with_windows": autostart,
        }
        self.settings_applied.emit(result)
        self.accept()
