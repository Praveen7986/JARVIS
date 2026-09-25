"""
Windows System Media Transport Controls (SMTC) Session Watcher.
Extracts live playing media info, cover art, timeline with smooth real-time interpolation,
and controls from internet apps (Spotify, YouTube / Chrome / Edge, Apple Music, VLC).
"""

import asyncio
import logging
import threading
import time
from typing import Optional, Dict, Any

from PySide6.QtCore import QObject, Signal, QTimer

logger = logging.getLogger(__name__)

WINRT_AVAILABLE = False
try:
    import winrt.windows.media.control as wmc
    import winrt.windows.storage.streams as streams
    import winrt.windows.foundation.collections
    WINRT_AVAILABLE = True
except Exception as e:
    logger.warning(f"WinRT media control not available: {e}")


class WindowsMediaWatcher(QObject):
    """Monitors live Windows media playback sessions with smooth timeline tracking."""

    media_updated = Signal(dict)
    state_changed = Signal(bool)
    timeline_updated = Signal(int, int)  # (position_ms, duration_ms)
    session_status_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_connected = WINRT_AVAILABLE
        self.has_active_session = False

        self._last_title = ""
        self._last_artist = ""
        self._last_is_playing = False
        self._last_pos_ms = 0
        self._last_dur_ms = 0
        self._last_pos_timestamp = time.time()

        self._loop = None
        self._thread = None
        self._manager = None
        self._current_session = None

        if WINRT_AVAILABLE:
            self._start_async_worker()

        # Check SMTC sessions every 1000ms
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(1000)
        self.poll_timer.timeout.connect(self._trigger_check)
        self.poll_timer.start()

        # Smooth timeline tick timer (every 500ms) for real-time progress bar movement
        self.timeline_timer = QTimer(self)
        self.timeline_timer.setInterval(500)
        self.timeline_timer.timeout.connect(self._tick_timeline)
        self.timeline_timer.start()

    def _start_async_worker(self):
        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._init_session_manager())
            self._loop.run_forever()

        self._thread = threading.Thread(target=run_loop, daemon=True)
        self._thread.start()

    async def _init_session_manager(self):
        try:
            self._manager = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
            logger.info("SMTC Session Manager initialized.")
        except Exception as e:
            logger.warning(f"Could not request SMTC Session Manager: {e}")

    def _trigger_check(self):
        if not WINRT_AVAILABLE or not self._loop or not self._manager:
            return
        asyncio.run_coroutine_threadsafe(self._check_active_session(), self._loop)

    def _tick_timeline(self):
        """Interpolates current playback position between SMTC updates."""
        if self.has_active_session and self._last_is_playing and self._last_dur_ms > 0:
            elapsed = int((time.time() - self._last_pos_timestamp) * 1000)
            current_pos = min(self._last_dur_ms, self._last_pos_ms + elapsed)
            self.timeline_updated.emit(current_pos, self._last_dur_ms)

    async def _check_active_session(self):
        try:
            if not self._manager:
                return

            session = self._manager.get_current_session()
            if not session:
                sessions = self._manager.get_sessions()
                for s in sessions:
                    info = s.get_playback_info()
                    if info and info.playback_status == wmc.GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING:
                        session = s
                        break
                if not session and len(sessions) > 0:
                    session = sessions[0]

            if not session:
                if self.has_active_session:
                    self.has_active_session = False
                    self.session_status_changed.emit(False)
                return

            self._current_session = session
            app_id = session.source_app_user_model_id or "Internet Media"

            friendly_app = "Spotify" if "spotify" in app_id.lower() else (
                "Google Chrome" if "chrome" in app_id.lower() else (
                    "Microsoft Edge" if "edge" in app_id.lower() else (
                        "Apple Music" if "apple" in app_id.lower() else "Web / App Music"
                    )
                )
            )

            # Media properties
            props = await session.try_get_media_properties_async()
            if not props or not props.title:
                return

            title = props.title
            artist = props.artist or "Unknown Artist"
            album = props.album_title or ""

            # Playback status
            info = session.get_playback_info()
            is_playing = False
            if info:
                is_playing = (info.playback_status == wmc.GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING)

            # Timeline
            timeline = session.get_timeline_properties()
            pos_ms = 0
            dur_ms = 0
            if timeline:
                pos_ms = int(timeline.position.duration / 10000) if hasattr(timeline.position, "duration") else 0
                dur_ms = int(timeline.end_time.duration / 10000) if hasattr(timeline.end_time, "duration") else 0

            # Update timeline base
            self._last_pos_ms = pos_ms
            self._last_dur_ms = dur_ms
            self._last_pos_timestamp = time.time()
            self._last_is_playing = is_playing

            # Thumbnail bytes
            cover_bytes = b""
            if props.thumbnail:
                try:
                    stream = await props.thumbnail.open_read_async()
                    if stream and stream.size > 0:
                        reader = streams.DataReader(stream.get_input_stream_at(0))
                        await reader.load_async(stream.size)
                        buf = bytearray(stream.size)
                        reader.read_bytes(buf)
                        cover_bytes = bytes(buf)
                except Exception as thumb_err:
                    logger.debug(f"Thumbnail read error: {thumb_err}")

            track_info = {
                "title": title,
                "artist": artist,
                "album": album,
                "app_name": friendly_app,
                "is_playing": is_playing,
                "position_ms": pos_ms,
                "duration_ms": dur_ms,
                "cover_bytes": cover_bytes,
                "source": "smtc",
            }

            self.has_active_session = True
            self.session_status_changed.emit(True)
            self.media_updated.emit(track_info)

            if is_playing != self._last_is_playing:
                self.state_changed.emit(is_playing)

            if dur_ms > 0:
                self.timeline_updated.emit(pos_ms, dur_ms)

        except Exception as e:
            logger.debug(f"Error in SMTC session check: {e}")

    # --- Media Remote Control Actions ---

    def toggle_play_pause(self):
        if not self._loop or not self._current_session:
            return
        asyncio.run_coroutine_threadsafe(self._do_toggle_play_pause(), self._loop)

    async def _do_toggle_play_pause(self):
        try:
            if self._current_session:
                await self._current_session.try_toggle_play_pause_async()
        except Exception as e:
            logger.warning(f"Failed to toggle play/pause via SMTC: {e}")

    def next_track(self):
        if not self._loop or not self._current_session:
            return
        asyncio.run_coroutine_threadsafe(self._do_next_track(), self._loop)

    async def _do_next_track(self):
        try:
            if self._current_session:
                await self._current_session.try_skip_next_async()
        except Exception as e:
            logger.warning(f"Failed to skip next via SMTC: {e}")

    def prev_track(self):
        if not self._loop or not self._current_session:
            return
        asyncio.run_coroutine_threadsafe(self._do_prev_track(), self._loop)

    async def _do_prev_track(self):
        try:
            if self._current_session:
                await self._current_session.try_skip_previous_async()
        except Exception as e:
            logger.warning(f"Failed to skip prev via SMTC: {e}")

    def set_position(self, pos_ms: int):
        self._last_pos_ms = pos_ms
        self._last_pos_timestamp = time.time()
        if not self._loop or not self._current_session:
            return
        asyncio.run_coroutine_threadsafe(self._do_set_position(pos_ms), self._loop)

    async def _do_set_position(self, pos_ms: int):
        try:
            if self._current_session:
                ticks = int(pos_ms * 10000)
                await self._current_session.try_change_playback_position_async(ticks)
        except Exception as e:
            logger.debug(f"Failed to change position via SMTC: {e}")
