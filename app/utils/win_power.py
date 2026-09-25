"""
Windows sleep, wake, lock, and unlock event listener.
"""

import ctypes
import logging
from typing import Callable, List

logger = logging.getLogger(__name__)

# Windows session notification constants
NOTIFY_FOR_THIS_SESSION = 0
WM_WTSSESSION_CHANGE = 0x02B1
WTS_SESSION_LOCK = 0x7
WTS_SESSION_UNLOCK = 0x8

# Windows power broadcast constants
WM_POWERBROADCAST = 0x0218
PBT_APMSUSPEND = 0x0004
PBT_APMRESUMEAUTOMATIC = 0x0012
PBT_APMRESUMESUSPEND = 0x0007


class PowerSessionWatcher:
    """Monitors Windows power events (sleep/wake) and session lock/unlock events."""

    def __init__(self):
        self._lock_callbacks: List[Callable[[], None]] = []
        self._unlock_callbacks: List[Callable[[], None]] = []
        self._sleep_callbacks: List[Callable[[], None]] = []
        self._wake_callbacks: List[Callable[[], None]] = []
        self._is_locked = False
        self._is_sleeping = False
        self._wtsapi32 = getattr(ctypes.windll, "wtsapi32", None)

    @property
    def is_locked(self) -> bool:
        return self._is_locked

    @property
    def is_sleeping(self) -> bool:
        return self._is_sleeping

    def on_lock(self, callback: Callable[[], None]):
        self._lock_callbacks.append(callback)

    def on_unlock(self, callback: Callable[[], None]):
        self._unlock_callbacks.append(callback)

    def on_sleep(self, callback: Callable[[], None]):
        self._sleep_callbacks.append(callback)

    def on_wake(self, callback: Callable[[], None]):
        self._wake_callbacks.append(callback)

    def register_window_handle(self, hwnd: int):
        """Registers a Qt window handle (HWND) for WTSRegisterSessionNotification."""
        if self._wtsapi32 and hwnd:
            try:
                self._wtsapi32.WTSRegisterSessionNotification(hwnd, NOTIFY_FOR_THIS_SESSION)
                logger.info("Registered WTSRegisterSessionNotification successfully.")
            except Exception as e:
                logger.warning(f"Could not register session notification: {e}")

    def unregister_window_handle(self, hwnd: int):
        if self._wtsapi32 and hwnd:
            try:
                self._wtsapi32.WTSUnRegisterSessionNotification(hwnd)
            except Exception:
                pass

    def handle_native_event(self, msg_type: int, w_param: int, l_param: int) -> bool:
        """Process native Windows messages from Qt nativeEventFilter."""
        if msg_type == WM_WTSSESSION_CHANGE:
            if w_param == WTS_SESSION_LOCK:
                logger.info("Windows Session Locked.")
                self._is_locked = True
                for cb in self._lock_callbacks:
                    try:
                        cb()
                    except Exception as e:
                        logger.error(f"Error in lock callback: {e}")
            elif w_param == WTS_SESSION_UNLOCK:
                logger.info("Windows Session Unlocked.")
                self._is_locked = False
                for cb in self._unlock_callbacks:
                    try:
                        cb()
                    except Exception as e:
                        logger.error(f"Error in unlock callback: {e}")
            return True

        elif msg_type == WM_POWERBROADCAST:
            if w_param == PBT_APMSUSPEND:
                logger.info("Windows System Suspend (Sleep).")
                self._is_sleeping = True
                for cb in self._sleep_callbacks:
                    try:
                        cb()
                    except Exception as e:
                        logger.error(f"Error in sleep callback: {e}")
            elif w_param in (PBT_APMRESUMEAUTOMATIC, PBT_APMRESUMESUSPEND):
                logger.info("Windows System Resumed (Wake).")
                self._is_sleeping = False
                for cb in self._wake_callbacks:
                    try:
                        cb()
                    except Exception as e:
                        logger.error(f"Error in wake callback: {e}")
            return True

        return False
