"""
GitHub Contribution Calendar Desktop Widget UI.
Compact & sleek Windows 11 / GitHub dark styled monthly contribution heatmap,
showing the current month's contributions, streak stats, weekday headers, and hover tooltips.
"""

import logging
import webbrowser
from datetime import datetime
from typing import Optional, Dict, Any, List

from PySide6.QtCore import Qt, Signal, Slot, QTimer, QRectF, QPointF
from PySide6.QtGui import (
    QFont, QColor, QPainter, QBrush, QPen, QPixmap, QPainterPath, QCursor
)
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QWidget, QToolTip
)

from app.base_widget import BaseWidget
from .github_service import GitHubWorker, GitHubAvatarLoader, fetch_github_data
from .settings_dialog import GitHubSettingsDialog

logger = logging.getLogger(__name__)

# Palette options for contribution heatmap
HEATMAP_THEMES = {
    "emerald": [
        QColor(22, 27, 34),          # Level 0 (GitHub dark)
        QColor(14, 68, 41),          # Level 1
        QColor(0, 109, 50),          # Level 2
        QColor(38, 166, 65),         # Level 3
        QColor(57, 211, 83)          # Level 4
    ],
    "cyber_blue": [
        QColor(22, 27, 34),
        QColor(12, 74, 110),
        QColor(2, 132, 199),
        QColor(14, 165, 233),
        QColor(56, 189, 248)
    ],
    "solar_amber": [
        QColor(22, 27, 34),
        QColor(120, 53, 15),
        QColor(180, 83, 9),
        QColor(217, 119, 6),
        QColor(245, 158, 11)
    ]
}


class MonthContributionCalendarView(QWidget):
    """
    Renders compact monthly GitHub contribution graph (7 columns x 5-6 rows)
    with weekday headers, contribution level coloring, streak badge, and hover tooltips.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.days_data: List[Dict[str, Any]] = []
        self.month_positions: List[Dict[str, Any]] = []
        self.theme_name = "emerald"
        self.current_streak = 0
        self.setFixedHeight(150)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._hovered_idx: Optional[int] = None
        self._cell_rects: List[tuple[int, QRectF]] = []

    def set_data(self, days: List[Dict[str, Any]], month_positions: Optional[List[Dict[str, Any]]] = None, theme: str = "emerald", streak: int = 0):
        self.days_data = days or []
        self.month_positions = month_positions or []
        self.theme_name = theme if theme in HEATMAP_THEMES else "emerald"
        self.current_streak = streak
        self._hovered_idx = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        colors = HEATMAP_THEMES.get(self.theme_name, HEATMAP_THEMES["emerald"])
        self._cell_rects.clear()

        # Filter days for the month to display (current month or latest month present in data)
        display_days = self._get_display_month_days()
        if not display_days:
            painter.setPen(QPen(QColor(148, 163, 184)))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No contribution data")
            painter.end()
            return

        square_size = 22.0
        gap = 5.0
        grid_width = 7 * square_size + 6 * gap
        left_offset = max(10.0, (self.width() - grid_width) / 2.0)
        top_offset = 20.0

        font_header = QFont("Segoe UI", 8, QFont.Weight.DemiBold)
        painter.setFont(font_header)

        # 1. Paint Weekday Column Headers (M, T, W, T, F, S, S)
        weekday_labels = ["M", "T", "W", "T", "F", "S", "S"]
        painter.setPen(QPen(QColor(148, 163, 184, 200)))
        for i, lbl in enumerate(weekday_labels):
            wx = left_offset + i * (square_size + gap)
            rect = QRectF(wx, 2, square_size, 14)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, lbl)

        # 2. Paint Month Day Cells
        # Find the starting weekday of the month
        first_day_obj = display_days[0]
        try:
            first_dt = datetime.strptime(first_day_obj["date"], "%Y-%m-%d")
            first_weekday = first_dt.weekday()  # 0 = Monday, 6 = Sunday
        except Exception:
            first_weekday = 0

        for day in display_days:
            day_num = day.get("day", 1)
            # Row & Column calculation
            cell_index = (day_num - 1) + first_weekday
            col = cell_index % 7
            row = cell_index // 7

            x = left_offset + col * (square_size + gap)
            y = top_offset + row * (square_size + gap)
            rect = QRectF(x, y, square_size, square_size)
            self._cell_rects.append((day_num - 1, rect))

            lvl = min(4, max(0, day.get("level", 0)))
            fill_color = colors[lvl]

            painter.setBrush(QBrush(fill_color))

            # Hover & Border styling
            if self._hovered_idx == (day_num - 1):
                painter.setPen(QPen(QColor(255, 255, 255, 240), 1.5))
            elif lvl == 0:
                painter.setPen(QPen(QColor(255, 255, 255, 16), 0.8))
            else:
                border_color = QColor(fill_color.red(), fill_color.green(), fill_color.blue(), 220)
                painter.setPen(QPen(border_color, 0.8))

            painter.drawRoundedRect(rect, 3.5, 3.5)

        # 3. Footer: Streak badge & Legend
        max_rows = (len(display_days) + first_weekday + 6) // 7
        footer_y = top_offset + max_rows * (square_size + gap) + 12
        if footer_y + 14 > self.height():
            footer_y = self.height() - 14

        painter.setFont(QFont("Segoe UI", 7))

        # Left: Streak info
        painter.setPen(QPen(QColor(245, 158, 11) if self.current_streak > 0 else QColor(148, 163, 184, 160)))
        streak_text = f"🔥 {self.current_streak}d streak" if self.current_streak > 0 else "0d streak"
        painter.drawText(int(left_offset), int(footer_y), streak_text)

        # Right: Mini Legend "Less [ ■ ■ ■ ■ ■ ] More"
        legend_sq = 7.0
        legend_start_x = left_offset + grid_width - (5 * (legend_sq + 2) + 48)
        painter.setPen(QPen(QColor(148, 163, 184, 160)))
        painter.drawText(int(legend_start_x), int(footer_y), "Less")

        lx_base = legend_start_x + 22
        for l_idx, col_val in enumerate(colors):
            lx = lx_base + l_idx * (legend_sq + 2)
            ly = footer_y - 7
            painter.setBrush(QBrush(col_val))
            painter.setPen(QPen(QColor(255, 255, 255, 20), 0.5))
            painter.drawRoundedRect(QRectF(lx, ly, legend_sq, legend_sq), 1.5, 1.5)

        painter.setPen(QPen(QColor(148, 163, 184, 160)))
        painter.drawText(int(lx_base + 5 * (legend_sq + 2) + 3), int(footer_y), "More")

        painter.end()

    def _get_display_month_days(self) -> List[Dict[str, Any]]:
        """Returns days for the current month or latest available month."""
        if not self.days_data:
            return []

        now = datetime.now()
        cur_year = now.year
        cur_month_str = now.strftime("%b")

        matched = [d for d in self.days_data if d.get("year") == cur_year and d.get("month") == cur_month_str]
        if matched:
            return sorted(matched, key=lambda d: d.get("day", 0))

        # Fallback to the latest month present in data
        latest_date = max((d.get("date", "") for d in self.days_data if d.get("date")), default="")
        if latest_date and "-" in latest_date:
            parts = latest_date.split("-")
            yr = int(parts[0])
            mo_num = int(parts[1])
            fallback = [
                d for d in self.days_data
                if d.get("date", "").startswith(f"{yr:04d}-{mo_num:02d}")
            ]
            if fallback:
                return sorted(fallback, key=lambda d: d.get("day", 0))

        return self.days_data[:31]

    def mouseMoveEvent(self, event):
        pos = event.position()
        found_idx = None
        display_days = self._get_display_month_days()

        for idx, rect in self._cell_rects:
            if rect.contains(pos):
                found_idx = idx
                if idx < len(display_days):
                    day = display_days[idx]
                    count = day.get("count", 0)
                    date_str = day.get("date", "")
                    try:
                        dt = datetime.strptime(date_str, "%Y-%m-%d")
                        formatted_dt = dt.strftime("%B %d, %Y")
                    except Exception:
                        formatted_dt = date_str
                    c_word = "contribution" if count == 1 else "contributions"
                    tt = f"<b>{count} {c_word}</b> on {formatted_dt}"
                    QToolTip.showText(event.globalPosition().toPoint(), tt, self)
                break

        if found_idx != self._hovered_idx:
            self._hovered_idx = found_idx
            self.update()

        if found_idx is None:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            QToolTip.hideText()
        else:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def leaveEvent(self, event):
        self._hovered_idx = None
        self.update()
        QToolTip.hideText()
        super().leaveEvent(event)


# Backward compatibility alias
FullContributionCalendarView = MonthContributionCalendarView


class GitHubRadarWidget(BaseWidget):
    """
    Compact desktop widget presenting the monthly GitHub contribution graph
    and activity stats matching Windows 11 and GitHub dark glass aesthetics.
    """

    def __init__(
        self,
        widget_id: str = "github_radar",
        widget_manager=None,
        parent=None
    ):
        super().__init__(widget_id=widget_id, widget_manager=widget_manager, parent=parent)
        self.setFixedSize(320, 240)

        self._username = "Praveen7986"
        self._token = ""
        self._refresh_interval_minutes = 15
        self._theme = "emerald"
        self._html_url = "https://github.com/Praveen7986"
        self._avatar_pixmap: Optional[QPixmap] = None

        self._worker: Optional[GitHubWorker] = None
        self._avatar_loader: Optional[GitHubAvatarLoader] = None

        self._setup_ui()
        self._load_config()

        # Periodic Refresh Timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh_data)
        self._timer.start(self._refresh_interval_minutes * 60 * 1000)

        # Initial fetch
        QTimer.singleShot(200, self.refresh_data)

    def get_display_title(self) -> str:
        return "GitHub Contribution Calendar"

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(6, 6, 6, 6)

        self.card_frame = QFrame(self)
        self.card_frame.setObjectName("githubCard")
        self.card_frame.setStyleSheet("""
            #githubCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(18, 22, 30, 0.96),
                    stop:1 rgba(13, 17, 23, 0.98));
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 14px;
            }
            QLabel {
                font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            }
        """)

        card_layout = QVBoxLayout(self.card_frame)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(6)

        # --- Top Header: Avatar, User, Status & Actions ---
        header = QHBoxLayout()
        header.setSpacing(6)

        # User Avatar & Link
        self.lbl_avatar = QLabel()
        self.lbl_avatar.setFixedSize(20, 20)
        self.lbl_avatar.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.08);
            border-radius: 10px;
            font-size: 11px;
        """)
        self.lbl_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_avatar.setText("🐙")
        header.addWidget(self.lbl_avatar)

        self.lbl_user = QLabel(f"@{self._username}")
        self.lbl_user.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_user.setStyleSheet("color: #58A6FF; font-size: 12px; font-weight: 600;")
        self.lbl_user.mousePressEvent = lambda e: self._open_github_profile()
        header.addWidget(self.lbl_user)

        self.lbl_status = QLabel("●")
        self.lbl_status.setToolTip("Synced")
        self.lbl_status.setStyleSheet("color: #10B981; font-size: 10px; margin-left: 2px;")
        header.addWidget(self.lbl_status)

        header.addStretch()

        # Action Buttons (Refresh & Settings)
        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setFixedSize(22, 22)
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setToolTip("Refresh GitHub Data")
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 5px;
                color: #FFFFFF;
                font-size: 10px;
            }
            QPushButton:hover {
                background: rgba(56, 189, 248, 0.25);
                border-color: #38BDF8;
            }
        """)
        self.btn_refresh.clicked.connect(self.refresh_data)
        header.addWidget(self.btn_refresh)

        self.btn_settings = QPushButton("⚙️")
        self.btn_settings.setFixedSize(22, 22)
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.setToolTip("Widget Settings")
        self.btn_settings.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 5px;
                color: #FFFFFF;
                font-size: 10px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.18);
            }
        """)
        self.btn_settings.clicked.connect(self.open_settings_dialog)
        header.addWidget(self.btn_settings)

        card_layout.addLayout(header)

        # --- Month Summary Header: "21 contributions in September" ---
        now = datetime.now()
        self.lbl_total_header = QLabel(f"0 contributions in {now.strftime('%B')}")
        self.lbl_total_header.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 700; font-family: 'Segoe UI';")
        card_layout.addWidget(self.lbl_total_header)

        # --- Contribution Calendar Inner Box (Bordered sub-panel) ---
        self.calendar_panel = QFrame(self)
        self.calendar_panel.setObjectName("calendarPanel")
        self.calendar_panel.setStyleSheet("""
            #calendarPanel {
                background-color: rgba(13, 17, 23, 0.70);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }
        """)
        panel_layout = QVBoxLayout(self.calendar_panel)
        panel_layout.setContentsMargins(4, 4, 4, 4)

        self.calendar_view = MonthContributionCalendarView(self.calendar_panel)
        panel_layout.addWidget(self.calendar_view)

        card_layout.addWidget(self.calendar_panel)
        root_layout.addWidget(self.card_frame)

    def _load_config(self):
        """Loads configuration from SettingsManager."""
        if not self.widget_manager:
            return
        cfg = self.widget_manager.settings.get_widget_config(self.widget_id)
        self._username = cfg.get("username", "Praveen7986")
        self._token = cfg.get("token", "")
        self._refresh_interval_minutes = cfg.get("refresh_interval", 15)
        self._theme = cfg.get("theme", "emerald")

        self.lbl_user.setText(f"@{self._username}")
        self._html_url = f"https://github.com/{self._username}"

    def load_state(self):
        """Restore widget state while ensuring compact monthly layout size."""
        super().load_state()
        self.setFixedSize(320, 240)

    def save_widget_config(self):
        """Saves current widget config."""
        if not self.widget_manager:
            return
        self.widget_manager.settings.update_widget_config(self.widget_id, {
            "username": self._username,
            "token": self._token,
            "refresh_interval": self._refresh_interval_minutes,
            "theme": self._theme
        })

    @Slot()
    def refresh_data(self):
        """Triggers non-blocking background fetch."""
        if not self._username:
            self.lbl_status.setText("⚠️")
            self.lbl_status.setToolTip("Please set username in Settings")
            self.lbl_status.setStyleSheet("color: #F59E0B; font-size: 10px;")
            return

        self.lbl_status.setText("⏳")
        self.lbl_status.setToolTip("Syncing...")
        self.lbl_status.setStyleSheet("color: #F59E0B; font-size: 10px;")

        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait()

        self._worker = GitHubWorker(username=self._username, token=self._token, parent=self)
        self._worker.data_ready.connect(self._on_data_received)
        self._worker.start()

    @Slot(dict)
    def _on_data_received(self, data: dict):
        """Handles fetched GitHub calendar data."""
        if data.get("error"):
            err_msg = data["error"]
            logger.warning(f"GitHub fetch error: {err_msg}")
            self.lbl_status.setText("❌")
            self.lbl_status.setToolTip(f"Sync error: {err_msg}")
            self.lbl_status.setStyleSheet("color: #EF4444; font-size: 10px;")
            self.lbl_total_header.setText("⚠️ Sync Error")
            self.lbl_user.setText(f"@{self._username}" if self._username else "@github")
            self.calendar_view.set_data([], [], theme=self._theme)
            return

        # Auto-update username if resolved via token
        resolved_username = data.get("username", self._username)
        if resolved_username:
            self._username = resolved_username
            self.save_widget_config()

        self.lbl_user.setText(f"@{self._username}")
        self._html_url = data.get("html_url", f"https://github.com/{self._username}")

        # Update Header: Month contributions count
        now = datetime.now()
        month_total = data.get("month_total")
        if month_total is None:
            # Calculate from days
            month_days = data.get("month_days", [])
            month_total = sum(d.get("count", 0) for d in month_days)
        
        month_name = now.strftime("%B")
        self.lbl_total_header.setText(f"{month_total} contributions in {month_name}")

        # Update Compact Month Calendar View
        days = data.get("days", [])
        month_positions = data.get("month_positions", [])
        streak = data.get("current_streak", 0)
        self.calendar_view.set_data(days, month_positions, theme=self._theme, streak=streak)

        # Update Sync Badge
        sync_time = data.get("last_synced", "")
        self.lbl_status.setText("●")
        self.lbl_status.setToolTip(f"Synced at {sync_time}")
        self.lbl_status.setStyleSheet("color: #10B981; font-size: 10px; font-weight: 500;")

        # Load avatar
        avatar_url = data.get("avatar_url", "")
        if avatar_url:
            self._avatar_loader = GitHubAvatarLoader(avatar_url, parent=self)
            self._avatar_loader.avatar_loaded.connect(self._on_avatar_loaded)
            self._avatar_loader.start()
        else:
            self.lbl_avatar.setPixmap(QPixmap())
            self.lbl_avatar.setText("🐙")

    @Slot(QPixmap)
    def _on_avatar_loaded(self, pixmap: QPixmap):
        """Renders circular cropped avatar pixmap."""
        if pixmap.isNull():
            return

        size = 20
        rounded = QPixmap(size, size)
        rounded.fill(Qt.GlobalColor.transparent)

        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, size, size, pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        painter.end()

        self._avatar_pixmap = rounded
        self.lbl_avatar.setPixmap(rounded)

    def _open_github_profile(self):
        """Opens user's GitHub profile in default browser."""
        if self._html_url:
            webbrowser.open(self._html_url)

    def open_settings_dialog(self):
        """Opens settings modal dialog."""
        cfg = {
            "username": self._username,
            "token": self._token,
            "refresh_interval": self._refresh_interval_minutes,
            "theme": self._theme,
            "always_on_top": self._always_on_top,
            "opacity": self._opacity
        }
        dlg = GitHubSettingsDialog(current_config=cfg, parent=self)
        dlg.settings_applied.connect(self._on_settings_applied)
        dlg.exec()

    @Slot(dict)
    def _on_settings_applied(self, new_cfg: dict):
        """Applies updated settings from modal."""
        self._username = new_cfg.get("username", self._username).strip()
        self._token = new_cfg.get("token", "").strip()
        self._refresh_interval_minutes = int(new_cfg.get("refresh_interval", 15))
        self._theme = new_cfg.get("theme", "emerald")

        self.set_always_on_top(new_cfg.get("always_on_top", True))
        self.set_opacity(new_cfg.get("opacity", 0.95))

        self.lbl_user.setText(f"@{self._username}" if self._username else "@github")
        self.lbl_status.setText("⏳")
        self.lbl_status.setToolTip("Syncing...")
        self.lbl_status.setStyleSheet("color: #F59E0B; font-size: 10px;")
        self.lbl_total_header.setText("Contacting GitHub...")

        self.save_widget_config()

        self._timer.setInterval(self._refresh_interval_minutes * 60 * 1000)
        self.refresh_data()

    def build_context_menu(self, menu):
        """Extends BaseWidget right-click menu."""
        super().build_context_menu(menu)
        menu.addSeparator()

        act_refresh = menu.addAction("🔄 Refresh GitHub Calendar")
        act_refresh.triggered.connect(self.refresh_data)

        act_profile = menu.addAction("🌐 Open GitHub Profile")
        act_profile.triggered.connect(self._open_github_profile)

        act_cfg = menu.addAction("⚙️ GitHub Widget Settings")
        act_cfg.triggered.connect(self.open_settings_dialog)
