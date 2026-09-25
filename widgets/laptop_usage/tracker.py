"""
Accurate, timestamp-based Laptop Usage Tracker engine.
Distinguishes between active interaction and idle time, handles sleep/lock,
and performs date-based midnight rollover.
"""

import logging
import time
from datetime import datetime, date, timedelta
from typing import Optional
from PySide6.QtCore import QObject, QTimer, Signal
from app.storage import StorageManager
from app.utils.win_activity import ActivityDetector
from app.utils.win_power import PowerSessionWatcher

logger = logging.getLogger(__name__)


class LaptopUsageTracker(QObject):
    """
    Engine that tracks active laptop usage based on system timestamps and input activity.
    """

    # Signals: (total_usage_seconds, is_active, formatted_time, date_str)
    usage_updated = Signal(int, bool, str, str)
    status_changed = Signal(bool)
    date_changed = Signal(str)

    def __init__(
        self,
        storage: StorageManager,
        power_watcher: Optional[PowerSessionWatcher] = None,
        idle_threshold_seconds: int = 300,
        parent=None
    ):
        super().__init__(parent)
        self.storage = storage
        self.power_watcher = power_watcher
        self.idle_threshold_seconds = idle_threshold_seconds
        self.activity_detector = ActivityDetector()

        # Tracking state
        self.current_date_str = date.today().strftime("%Y-%m-%d")
        self.persisted_today_seconds = self.storage.get_day_usage(self.current_date_str)
        self.is_active = False
        self.active_start_time: Optional[float] = None
        self.last_input_time_cached: Optional[float] = None

        # Periodical save timer
        self._last_save_time = time.time()

        # Polling timer (1 second interval is lightweight & responsive)
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

        # Wire power session watcher if present
        if self.power_watcher:
            self.power_watcher.on_lock(self._handle_pause_event)
            self.power_watcher.on_sleep(self._handle_pause_event)
            self.power_watcher.on_unlock(self._handle_resume_event)
            self.power_watcher.on_wake(self._handle_resume_event)

    def start(self):
        """Starts the tracking timer."""
        self.current_date_str = date.today().strftime("%Y-%m-%d")
        self.persisted_today_seconds = self.storage.get_day_usage(self.current_date_str)
        self._timer.start()
        logger.info(f"LaptopUsageTracker started for {self.current_date_str} with base {self.persisted_today_seconds}s")
        self._emit_update()

    def stop(self):
        """Stops the tracking timer and flushes state."""
        self._timer.stop()
        self._finalize_active_session()
        self._flush_to_storage()
        logger.info("LaptopUsageTracker stopped.")

    def set_idle_threshold(self, seconds: int):
        """Updates the idle threshold in seconds."""
        self.idle_threshold_seconds = max(10, seconds)
        logger.info(f"Updated idle threshold to {self.idle_threshold_seconds}s")

    def reset_today(self):
        """Resets today's tracked usage to 0."""
        self.active_start_time = time.time() if self.is_active else None
        self.persisted_today_seconds = 0
        self.storage.reset_day_usage(self.current_date_str)
        self._emit_update()

    # --- Core Tracking Logic ---

    def _tick(self):
        """Main periodic loop executed every second."""
        now = time.time()
        today_str = date.today().strftime("%Y-%m-%d")

        # 1. Check for Midnight / Date Rollover
        if today_str != self.current_date_str:
            self._handle_midnight_rollover(today_str)
            return

        # 2. Check system power/lock status
        if self.power_watcher and (self.power_watcher.is_locked or self.power_watcher.is_sleeping):
            if self.is_active:
                self._transition_to_idle()
            self._emit_update()
            return

        # 3. Check Windows input activity
        idle_seconds = self.activity_detector.get_idle_seconds()
        is_user_input_recent = idle_seconds < self.idle_threshold_seconds

        if is_user_input_recent:
            if not self.is_active:
                # Transition: Idle -> Active
                self._transition_to_active(now, idle_seconds)
        else:
            if self.is_active:
                # Transition: Active -> Idle (Exceeded threshold)
                self._transition_to_idle(idle_seconds)

        # 4. Periodically save to storage (every 15 seconds)
        if self.is_active and (now - self._last_save_time >= 15):
            self._flush_to_storage()
            self._last_save_time = now

        # 5. Emit UI update
        self._emit_update()

    def _transition_to_active(self, now: float, idle_seconds: float):
        """User started interacting with the laptop."""
        self.is_active = True
        # Account for when the input occurred recently
        self.active_start_time = max(now - idle_seconds, now - 1.0)
        logger.debug("Tracker state: ACTIVE")
        self.status_changed.emit(True)

    def _transition_to_idle(self, idle_seconds: float = 0.0):
        """User became idle or locked screen. Do not count idle time as usage."""
        if self.is_active and self.active_start_time is not None:
            now = time.time()
            # The active session effectively ended when the last input occurred
            effective_end = max(self.active_start_time, now - idle_seconds)
            session_duration = max(0.0, effective_end - self.active_start_time)
            self.persisted_today_seconds += int(session_duration)
            self.active_start_time = None

        self.is_active = False
        logger.debug("Tracker state: IDLE")
        self.status_changed.emit(False)
        self._flush_to_storage()

    def _finalize_active_session(self):
        """Finalize any current running active session."""
        if self.is_active and self.active_start_time is not None:
            now = time.time()
            session_duration = max(0.0, now - self.active_start_time)
            self.persisted_today_seconds += int(session_duration)
            self.active_start_time = None
            self.is_active = False

    def _handle_midnight_rollover(self, new_date_str: str):
        """Gracefully handle the 00:00:00 midnight transition."""
        logger.info(f"Midnight transition detected: {self.current_date_str} -> {new_date_str}")
        now = time.time()

        # If user was active during midnight, credit time before midnight to yesterday
        if self.is_active and self.active_start_time is not None:
            # Midnight timestamp
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
            yesterday_portion = max(0.0, min(today_start, now) - self.active_start_time)
            self.persisted_today_seconds += int(yesterday_portion)
            self.storage.set_day_usage(self.current_date_str, self.persisted_today_seconds)

            # Start today portion from midnight
            self.active_start_time = today_start
        else:
            self.storage.set_day_usage(self.current_date_str, self.persisted_today_seconds)

        # Switch to new day
        self.current_date_str = new_date_str
        self.persisted_today_seconds = 0
        self.storage.set_day_usage(new_date_str, 0)
        self.date_changed.emit(new_date_str)
        self._emit_update()

    def _handle_pause_event(self):
        """Invoked when system sleeps or session locks."""
        logger.info("Handling sleep/lock: finalizing active session.")
        self._transition_to_idle(0.0)
        self._emit_update()

    def _handle_resume_event(self):
        """Invoked when system wakes or unlocks."""
        logger.info("Handling wake/unlock: waiting for user activity.")
        self.is_active = False
        self.active_start_time = None
        self._emit_update()

    def get_current_usage_seconds(self) -> int:
        """Returns the total active usage seconds for today so far."""
        current = self.persisted_today_seconds
        if self.is_active and self.active_start_time is not None:
            active_duration = max(0.0, time.time() - self.active_start_time)
            current += int(active_duration)
        return current

    def _flush_to_storage(self):
        """Saves current accumulated progress to storage."""
        total = self.get_current_usage_seconds()
        self.storage.set_day_usage(self.current_date_str, total)

    def _emit_update(self):
        """Formats and emits usage update signal."""
        total_sec = self.get_current_usage_seconds()
        formatted = self.format_duration(total_sec)
        self.usage_updated.emit(total_sec, self.is_active, formatted, self.current_date_str)

    @staticmethod
    def format_duration(seconds: int) -> str:
        """
        Formats seconds into clean human-readable duration:
        - If < 1 hour: "00:03:27" or "0h 05m" depending on context, or "0h 05m"
        - If >= 1 hour: "5h 42m"
        """
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours == 0 and minutes < 5:
            # Show MM:SS when under 5 minutes for crisp real-time feedback
            return f"{minutes:02d}:{secs:02d}"
        elif hours == 0:
            return f"0h {minutes:02d}m"
        else:
            return f"{hours}h {minutes:02d}m"
