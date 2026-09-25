"""
Windows input activity detector using native GetLastInputInfo API.
Accurately detects keyboard, mouse move, and mouse click events system-wide.
Zero-overhead, non-intrusive, no admin rights required.
"""

import ctypes
import logging
from ctypes import Structure, c_uint, sizeof, byref

logger = logging.getLogger(__name__)


class LASTINPUTINFO(Structure):
    _fields_ = [
        ("cbSize", c_uint),
        ("dwTime", c_uint)
    ]


class ActivityDetector:
    """Detects system-wide user interaction on Windows."""

    def __init__(self):
        self._last_input_info = LASTINPUTINFO()
        self._last_input_info.cbSize = sizeof(LASTINPUTINFO)
        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32

    def get_idle_seconds(self) -> float:
        """Returns the number of seconds since the last system-wide user input."""
        try:
            if not self._user32.GetLastInputInfo(byref(self._last_input_info)):
                return 0.0

            # Get current tick count (in milliseconds)
            current_ticks = self._kernel32.GetTickCount64()
            # dwTime is 32-bit unsigned, so we mask or handle tick diff
            last_input_time = self._last_input_info.dwTime
            
            # Since GetTickCount64() is 64-bit and dwTime is 32-bit (wrapping every ~49.7 days),
            # compute the diff modulo 2^32
            current_ticks_32 = current_ticks & 0xFFFFFFFF
            if current_ticks_32 >= last_input_time:
                elapsed_ms = current_ticks_32 - last_input_time
            else:
                elapsed_ms = (0xFFFFFFFF - last_input_time) + current_ticks_32 + 1

            return max(0.0, elapsed_ms / 1000.0)
        except Exception as e:
            logger.error(f"Error querying last input info: {e}")
            return 0.0

    def is_user_active(self, idle_threshold_seconds: float) -> bool:
        """Returns True if the user interacted within the given threshold."""
        return self.get_idle_seconds() < idle_threshold_seconds
