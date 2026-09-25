"""
Music Player Desktop Widget UI with Dynamic Cover Art Background.
Clean Windows 11 aesthetics, vivid album art background, smooth timeline tracking,
and reference-styled media controls (circular glowing play button with minimal prev/next arrows).
"""

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot, QTimer, QRect, QPointF
from PySide6.QtGui import (
    QFont, QColor, QPainter, QBrush, QPen, QLinearGradient,
    QPixmap, QPainterPath, QPolygonF
)
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton, QFrame,
    QWidget
)

from app.base_widget import BaseWidget
from .player import AudioPlayerEngine
from .media_session_watcher import WindowsMediaWatcher
from .art_cache import ArtworkManager

logger = logging.getLogger(__name__)


def extract_dominant_color(pixmap: Optional[QPixmap]) -> QColor:
    """Extracts a vibrant accent color from the album artwork."""
    if not pixmap or pixmap.isNull():
        return QColor(245, 158, 11)  # Warm glowing amber/orange by default

    try:
        img = pixmap.toImage().scaled(24, 24, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
        r_sum, g_sum, b_sum, count = 0, 0, 0, 0
        for y in range(img.height()):
            for x in range(img.width()):
                c = img.pixelColor(x, y)
                brightness = c.red() + c.green() + c.blue()
                if 40 < brightness < 700:
                    r_sum += c.red()
                    g_sum += c.green()
                    b_sum += c.blue()
                    count += 1
        if count > 0:
            avg_r = r_sum // count
            avg_g = g_sum // count
            avg_b = b_sum // count
            # Boost vibrancy
            base = QColor(avg_r, avg_g, avg_b)
            h, s, v, a = base.getHsv()
            return QColor.fromHsv(h, max(140, min(255, int(s * 1.3))), max(180, min(255, int(v * 1.2))))
    except Exception:
        pass
    return QColor(245, 158, 11)


class CircularPlayButton(QPushButton):
    """Circular glowing play/pause button matching the user's reference image."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(46, 46)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.is_playing = False
        self.accent_color = QColor(245, 158, 11)  # Warm orange default

    def set_playing(self, playing: bool):
        self.is_playing = playing
        self.update()

    def set_accent_color(self, color: QColor):
        self.accent_color = color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        center_x = w / 2.0
        center_y = h / 2.0
        radius = (min(w, h) - 4) / 2.0

        # Outer soft glow ring
        glow_color = QColor(self.accent_color.red(), self.accent_color.green(), self.accent_color.blue(), 70)
        painter.setBrush(QBrush(glow_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(center_x, center_y), radius + 2, radius + 2)

        # Gradient Circle Fill
        grad = QLinearGradient(0, 0, 0, h)
        h_val, s_val, v_val, _ = self.accent_color.getHsv()
        top_color = QColor.fromHsv(h_val, max(0, s_val - 20), min(255, v_val + 25))
        bot_color = self.accent_color

        grad.setColorAt(0.0, top_color)
        grad.setColorAt(1.0, bot_color)
        painter.setBrush(QBrush(grad))
        painter.drawEllipse(QPointF(center_x, center_y), radius, radius)

        # Play / Pause symbol in crisp dark or white
        icon_color = QColor(20, 20, 20)  # Dark contrast icon on glowing circle

        if not self.is_playing:
            # Play triangle
            painter.setBrush(QBrush(icon_color))
            painter.setPen(Qt.PenStyle.NoPen)
            tri_size = 14
            poly = QPolygonF([
                QPointF(center_x - 4, center_y - tri_size / 2.0),
                QPointF(center_x + tri_size / 2.0 + 1, center_y),
                QPointF(center_x - 4, center_y + tri_size / 2.0)
            ])
            painter.drawPolygon(poly)
        else:
            # Pause bars
            painter.setBrush(QBrush(icon_color))
            painter.setPen(Qt.PenStyle.NoPen)
            bar_w = 4
            bar_h = 14
            gap = 4
            painter.drawRoundedRect(int(center_x - bar_w - gap / 2.0), int(center_y - bar_h / 2.0), bar_w, bar_h, 1.5, 1.5)
            painter.drawRoundedRect(int(center_x + gap / 2.0), int(center_y - bar_h / 2.0), bar_w, bar_h, 1.5, 1.5)

        painter.end()


class MinimalMediaArrowButton(QPushButton):
    """Crisp solid arrow button for Previous / Next (reference-styled)."""

    def __init__(self, direction: str = "next", parent=None):
        super().__init__(parent)
        self.direction = direction  # "prev" or "next"
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.is_hovered = False

    def enterEvent(self, event):
        self.is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = QColor(255, 255, 255, 240 if self.is_hovered else 190)
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0
        arrow_h = 13.0
        arrow_w = 7.0

        if self.direction == "next":
            # Two forward chevron triangles ▶▶
            poly1 = QPolygonF([
                QPointF(cx - arrow_w, cy - arrow_h / 2.0),
                QPointF(cx, cy),
                QPointF(cx - arrow_w, cy + arrow_h / 2.0)
            ])
            poly2 = QPolygonF([
                QPointF(cx, cy - arrow_h / 2.0),
                QPointF(cx + arrow_w, cy),
                QPointF(cx, cy + arrow_h / 2.0)
            ])
            painter.drawPolygon(poly1)
            painter.drawPolygon(poly2)
        else:
            # Two backward chevron triangles ◀◀
            poly1 = QPolygonF([
                QPointF(cx, cy - arrow_h / 2.0),
                QPointF(cx - arrow_w, cy),
                QPointF(cx, cy + arrow_h / 2.0)
            ])
            poly2 = QPolygonF([
                QPointF(cx + arrow_w, cy - arrow_h / 2.0),
                QPointF(cx, cy),
                QPointF(cx + arrow_w, cy + arrow_h / 2.0)
            ])
            painter.drawPolygon(poly1)
            painter.drawPolygon(poly2)

        painter.end()


class VisualizerWave(QWidget):
    """Album art tile with animated audio visualizer equalizer overlay."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(58, 58)
        self.is_playing = False
        self.cover_pixmap: Optional[QPixmap] = None
        self.accent_color = QColor(245, 158, 11)
        self.bar_heights = [10, 18, 14, 24, 12]

        self.timer = QTimer(self)
        self.timer.setInterval(120)
        self.timer.timeout.connect(self._animate)

    def set_playing(self, playing: bool):
        self.is_playing = playing
        if playing:
            self.timer.start()
        else:
            self.timer.stop()
            self.bar_heights = [6, 10, 8, 12, 6]
            self.update()

    def set_cover_art(self, pixmap: Optional[QPixmap], accent: QColor):
        self.cover_pixmap = pixmap
        self.accent_color = accent
        self.update()

    def _animate(self):
        import random
        self.bar_heights = [random.randint(8, 34) for _ in range(5)]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 14, 14)
        painter.setClipPath(path)

        if self.cover_pixmap and not self.cover_pixmap.isNull():
            scaled = self.cover_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            sx = (scaled.width() - self.width()) // 2
            sy = (scaled.height() - self.height()) // 2
            painter.drawPixmap(0, 0, scaled, sx, sy, self.width(), self.height())

            # Subtle shadow overlay for visualizer contrast
            painter.setBrush(QBrush(QColor(0, 0, 0, 100 if self.is_playing else 20)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(0, 0, self.width(), self.height())
        else:
            grad = QLinearGradient(0, 0, self.width(), self.height())
            grad.setColorAt(0, QColor(30, 41, 59))
            grad.setColorAt(1, QColor(15, 23, 42))
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(0, 0, self.width(), self.height())

        # Glowing border
        painter.setPen(QPen(QColor(self.accent_color.red(), self.accent_color.green(), self.accent_color.blue(), 140), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 14, 14)

        # Equalizer bars
        if self.is_playing:
            bar_w = 4
            gap = 3
            total_w = (5 * bar_w) + (4 * gap)
            start_x = (self.width() - total_w) // 2

            for i, h in enumerate(self.bar_heights):
                x = start_x + (i * (bar_w + gap))
                y = (self.height() - h) // 2
                b_grad = QLinearGradient(x, y, x, y + h)
                b_grad.setColorAt(0, QColor(255, 255, 255, 240))
                b_grad.setColorAt(1, self.accent_color)
                painter.setBrush(QBrush(b_grad))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(x, y, bar_w, h, 2, 2)

        painter.end()


class MusicPlayerWidget(BaseWidget):
    """
    Frameless desktop Music Player widget with full-bleed cover art background.
    """

    def __init__(
        self,
        widget_id: str = "music_player",
        widget_manager=None,
        engine: Optional[AudioPlayerEngine] = None,
        parent=None
    ):
        super().__init__(widget_id=widget_id, widget_manager=widget_manager, parent=parent)

        self.engine = engine or AudioPlayerEngine()
        self.media_watcher = WindowsMediaWatcher(self)
        self.artwork_manager = ArtworkManager(self)

        self.current_cover_pixmap: Optional[QPixmap] = None
        self.accent_color = QColor(245, 158, 11)
        self.is_internet_app_active = False
        self._is_seeking = False
        self._current_pos_ms = 0
        self._current_dur_ms = 180000

        self._setup_ui()
        self._wire_connections()
        self.load_state()

        # Start with default track info
        cur = self.engine.current_track()
        if cur:
            self._apply_track_info(
                cur.get("title", "Midnight City"),
                cur.get("artist", "Aether Beats"),
                "Local Audio",
                False,
                0,
                cur.get("duration_ms", 180000)
            )

    def get_display_title(self) -> str:
        return "Music Player"

    def _setup_ui(self):
        # Increased size for generous layout
        self.resize(390, 190)
        self.setMinimumSize(340, 170)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)

        # Card container
        self.card = QFrame(self)
        self.card.setObjectName("musicCard")

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(8)

        # 1. Top Bar: Visualizer Tile & Track Metadata
        top_layout = QHBoxLayout()
        top_layout.setSpacing(14)

        self.visualizer = VisualizerWave(self.card)
        top_layout.addWidget(self.visualizer)

        info_col = QVBoxLayout()
        info_col.setSpacing(3)

        self.lbl_now_playing = QLabel("NOW PLAYING")
        self.lbl_now_playing.setStyleSheet("color: rgba(255, 255, 255, 0.60); font-size: 10px; font-weight: 700; letter-spacing: 1.5px;")
        info_col.addWidget(self.lbl_now_playing)

        self.lbl_title = QLabel("Midnight City Lofi")
        self.lbl_title.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: 700; font-family: 'Segoe UI';")
        info_col.addWidget(self.lbl_title)

        self.lbl_artist = QLabel("Aether Beats")
        self.lbl_artist.setStyleSheet("color: #FBBF24; font-size: 13px; font-weight: 600;")
        info_col.addWidget(self.lbl_artist)

        top_layout.addLayout(info_col)
        top_layout.addStretch()
        card_layout.addLayout(top_layout)

        card_layout.addSpacing(4)

        # 2. Seek Bar Slider
        self.slider_seek = QSlider(Qt.Orientation.Horizontal)
        self.slider_seek.setRange(0, 1000)
        self.slider_seek.setValue(0)
        self.slider_seek.sliderPressed.connect(self._on_seek_started)
        self.slider_seek.sliderReleased.connect(self._on_seek_ended)
        self.slider_seek.valueChanged.connect(self._on_seek_val_changed)
        self._update_slider_style()
        card_layout.addWidget(self.slider_seek)

        # 3. Bottom Bar: Time labels & Reference-Styled Playback Controls
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        self.lbl_time = QLabel("00:00 / 03:34")
        self.lbl_time.setStyleSheet("color: rgba(255, 255, 255, 0.70); font-size: 11px; font-weight: 600;")
        bottom_layout.addWidget(self.lbl_time)
        bottom_layout.addStretch()

        # Previous (Minimal double chevron)
        self.btn_prev = MinimalMediaArrowButton(direction="prev", parent=self.card)
        self.btn_prev.clicked.connect(self._on_prev_clicked)
        bottom_layout.addWidget(self.btn_prev)

        # Center Circular Glowing Play Button
        self.btn_play = CircularPlayButton(parent=self.card)
        self.btn_play.clicked.connect(self._on_play_clicked)
        bottom_layout.addWidget(self.btn_play)

        # Next (Minimal double chevron)
        self.btn_next = MinimalMediaArrowButton(direction="next", parent=self.card)
        self.btn_next.clicked.connect(self._on_next_clicked)
        bottom_layout.addWidget(self.btn_next)

        card_layout.addLayout(bottom_layout)
        outer_layout.addWidget(self.card)

    def _update_slider_style(self):
        accent_hex = self.accent_color.name()
        self.slider_seek.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 5px;
                background: rgba(255, 255, 255, 0.25);
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: {accent_hex};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: #FFFFFF;
                border: 2px solid {accent_hex};
                width: 12px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 6px;
            }}
        """)

    def _wire_connections(self):
        # 1. SMTC Internet Media watcher
        self.media_watcher.media_updated.connect(self._on_smtc_media_updated)
        self.media_watcher.state_changed.connect(self._on_playback_state_changed)
        self.media_watcher.timeline_updated.connect(self._on_timeline_updated)
        self.media_watcher.session_status_changed.connect(self._on_session_status_changed)

        # 2. Local audio engine
        self.engine.track_changed.connect(self._on_local_track_changed)
        self.engine.state_changed.connect(self._on_playback_state_changed)
        self.engine.position_changed.connect(self._on_timeline_updated)

        # 3. Artwork manager
        self.artwork_manager.artwork_ready.connect(self._on_artwork_ready)

    # --- Full-Bleed Paint Event for Vivid Cover Art Background ---

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Full card bounding rectangle
        margins = 10
        card_rect = QRect(margins, margins, self.width() - (margins * 2), self.height() - (margins * 2))

        path = QPainterPath()
        path.addRoundedRect(card_rect, 20, 20)
        painter.setClipPath(path)

        # 1. Render Cover Art with Higher Opacity & Rich Vibrancy
        if self.current_cover_pixmap and not self.current_cover_pixmap.isNull():
            scaled = self.current_cover_pixmap.scaled(
                card_rect.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            # Center crop
            sx = (scaled.width() - card_rect.width()) // 2
            sy = (scaled.height() - card_rect.height()) // 2
            painter.drawPixmap(card_rect.x(), card_rect.y(), scaled, sx, sy, card_rect.width(), card_rect.height())

            # Translucent dark glass gradient overlay (higher image visibility)
            overlay_grad = QLinearGradient(card_rect.topLeft(), card_rect.bottomLeft())
            overlay_grad.setColorAt(0, QColor(10, 15, 26, 120))
            overlay_grad.setColorAt(0.5, QColor(8, 12, 22, 160))
            overlay_grad.setColorAt(1, QColor(5, 8, 15, 200))
            painter.setBrush(QBrush(overlay_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(card_rect)
        else:
            # Default dark glass acrylic
            base_grad = QLinearGradient(card_rect.topLeft(), card_rect.bottomLeft())
            base_grad.setColorAt(0, QColor(26, 32, 44, 240))
            base_grad.setColorAt(1, QColor(15, 18, 26, 250))
            painter.setBrush(QBrush(base_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(card_rect)

        # Clean glass border perfectly matching card boundaries
        painter.setPen(QPen(QColor(255, 255, 255, 45), 1.2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(card_rect, 20, 20)

        painter.end()
        super().paintEvent(event)

    # --- SMTC & Media Event Handlers ---

    @Slot(dict)
    def _on_smtc_media_updated(self, info: dict):
        self.is_internet_app_active = True
        title = info.get("title", "Unknown")
        artist = info.get("artist", "")
        app_name = info.get("app_name", "Internet App")
        is_playing = info.get("is_playing", False)
        pos_ms = info.get("position_ms", 0)
        dur_ms = info.get("duration_ms", 0)
        cover_bytes = info.get("cover_bytes", b"")

        self._apply_track_info(title, artist, app_name, is_playing, pos_ms, dur_ms)

        if cover_bytes:
            pixmap = self.artwork_manager.load_from_bytes(f"{title}_{artist}", cover_bytes)
            if pixmap:
                self._set_cover_pixmap(pixmap)
        else:
            cached = self.artwork_manager.fetch_online_artwork(title, artist)
            if cached:
                self._set_cover_pixmap(cached)

    @Slot(dict)
    def _on_local_track_changed(self, track: dict):
        if not self.is_internet_app_active:
            title = track.get("title", "Unknown")
            artist = track.get("artist", "Local Audio")
            dur_ms = track.get("duration_ms", 180000)
            self._apply_track_info(title, artist, "Local Audio", False, 0, dur_ms)

            cached = self.artwork_manager.fetch_online_artwork(title, artist)
            if cached:
                self._set_cover_pixmap(cached)

    @Slot(bool)
    def _on_session_status_changed(self, active: bool):
        self.is_internet_app_active = active

    @Slot(str, QPixmap)
    def _on_artwork_ready(self, key: str, pixmap: QPixmap):
        self._set_cover_pixmap(pixmap)

    def _set_cover_pixmap(self, pixmap: QPixmap):
        self.current_cover_pixmap = pixmap
        # Extract dominant vibrant color from cover art
        self.accent_color = extract_dominant_color(pixmap)

        self.visualizer.set_cover_art(pixmap, self.accent_color)
        self.btn_play.set_accent_color(self.accent_color)
        self.lbl_artist.setStyleSheet(f"color: {self.accent_color.name()}; font-size: 13px; font-weight: 600;")
        self._update_slider_style()
        self.update()

    def _apply_track_info(self, title: str, artist: str, app_name: str, is_playing: bool, pos_ms: int, dur_ms: int):
        self.lbl_title.setText(title)
        self.lbl_artist.setText(artist)

        self._on_playback_state_changed(is_playing)
        if dur_ms > 0:
            self._on_timeline_updated(pos_ms, dur_ms)

    @Slot(bool)
    def _on_playback_state_changed(self, is_playing: bool):
        self.btn_play.set_playing(is_playing)
        self.visualizer.set_playing(is_playing)

    @Slot(int, int)
    def _on_timeline_updated(self, pos_ms: int, dur_ms: int):
        self._current_pos_ms = pos_ms
        self._current_dur_ms = max(1000, dur_ms)

        if not self._is_seeking and dur_ms > 0:
            ratio = min(1.0, pos_ms / float(dur_ms))
            self.slider_seek.blockSignals(True)
            self.slider_seek.setValue(int(ratio * 1000))
            self.slider_seek.blockSignals(False)

        pos_str = AudioPlayerEngine.format_time(pos_ms)
        dur_str = AudioPlayerEngine.format_time(dur_ms)
        self.lbl_time.setText(f"{pos_str} / {dur_str}")

    # --- Controls ---

    def _on_play_clicked(self):
        if self.is_internet_app_active:
            self.media_watcher.toggle_play_pause()
        else:
            self.engine.toggle_play()

    def _on_next_clicked(self):
        if self.is_internet_app_active:
            self.media_watcher.next_track()
        else:
            self.engine.next_track()

    def _on_prev_clicked(self):
        if self.is_internet_app_active:
            self.media_watcher.prev_track()
        else:
            self.engine.previous_track()

    def _on_seek_started(self):
        self._is_seeking = True

    def _on_seek_ended(self):
        self._is_seeking = False
        val = self.slider_seek.value()
        target_ms = int((val / 1000.0) * self._current_dur_ms)
        if self.is_internet_app_active:
            self.media_watcher.set_position(target_ms)
        else:
            self.engine.set_position(target_ms)

    def _on_seek_val_changed(self, val: int):
        if self._is_seeking:
            target_ms = int((val / 1000.0) * self._current_dur_ms)
            pos_str = AudioPlayerEngine.format_time(target_ms)
            dur_str = AudioPlayerEngine.format_time(self._current_dur_ms)
            self.lbl_time.setText(f"{pos_str} / {dur_str}")
