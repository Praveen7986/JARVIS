"""
Windows Startup Registry helper for My Widgets.
Configures autostart via HKEY_CURRENT_USER without needing admin privileges.
"""

import logging
import os
import sys
import winreg

logger = logging.getLogger(__name__)

REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "MyWidgets"


def get_launch_command() -> str:
    """Returns the command line to launch MyWidgets."""
    python_exe = sys.executable
    # Point to main.py
    main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "main.py"))
    # If running with pythonw.exe or python.exe
    if python_exe.lower().endswith("python.exe"):
        pythonw_exe = python_exe[:-10] + "pythonw.exe"
        if os.path.exists(pythonw_exe):
            python_exe = pythonw_exe
    return f'"{python_exe}" "{main_py}"'


def is_autostart_enabled() -> bool:
    """Checks if MyWidgets is registered in HKCU Run."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(val)
    except FileNotFoundError:
        return False
    except Exception as e:
        logger.error(f"Error checking autostart registry: {e}")
        return False


def set_autostart(enable: bool) -> bool:
    """Enables or disables autostart in HKCU Run."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_ALL_ACCESS) as key:
            if enable:
                cmd = get_launch_command()
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
                logger.info(f"Registered autostart command: {cmd}")
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                    logger.info("Removed autostart registry entry.")
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        logger.error(f"Error updating autostart registry: {e}")
        return False
