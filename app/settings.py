"""
Application settings manager for My Widgets.
"""

import copy
import logging
from typing import Any, Dict, List
from .storage import StorageManager

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS = {
    "app": {
        "start_with_windows": False,
        "first_launch": True,
        "theme": "dark_glass",
        "active_widgets": ["laptop_usage"],
    },
    "widgets": {
        "laptop_usage": {
            "enabled": True,
            "idle_threshold_seconds": 300,  # 5 minutes default
            "always_on_top": True,
            "opacity": 0.95,
            "x": 100,
            "y": 100,
            "width": 320,
            "height": 180,
            "screen_name": "",
        },
        "music_player": {
            "enabled": False,
            "always_on_top": True,
            "opacity": 0.95,
            "x": 100,
            "y": 300,
            "width": 390,
            "height": 190,
            "screen_name": "",
        },
        "github_radar": {
            "enabled": False,
            "username": "Praveen7986",
            "token": "",
            "refresh_interval": 15,
            "theme": "emerald",
            "always_on_top": True,
            "opacity": 0.95,
            "x": 100,
            "y": 500,
            "width": 760,
            "height": 205,
            "screen_name": "",
        }
    }
}


def get_default_settings() -> Dict[str, Any]:
    return copy.deepcopy(DEFAULT_SETTINGS)


class SettingsManager:
    """Provides high-level getters and setters for app configuration."""

    def __init__(self, storage: StorageManager):
        self.storage = storage
        self._data = self.storage.load_settings(get_default_settings())

    @property
    def data(self) -> Dict[str, Any]:
        return self._data

    def save(self) -> bool:
        return self.storage.save_settings(self._data)

    # --- App level settings ---

    def is_first_launch(self) -> bool:
        return self._data.get("app", {}).get("first_launch", True)

    def set_first_launch(self, val: bool):
        self._data.setdefault("app", {})["first_launch"] = val
        self.save()

    def get_start_with_windows(self) -> bool:
        return self._data.get("app", {}).get("start_with_windows", False)

    def set_start_with_windows(self, val: bool):
        self._data.setdefault("app", {})["start_with_windows"] = val
        self.save()

    def get_active_widgets(self) -> List[str]:
        return self._data.get("app", {}).get("active_widgets", ["laptop_usage"])

    def set_widget_active(self, widget_id: str, active: bool):
        active_list = list(self.get_active_widgets())
        if active and widget_id not in active_list:
            active_list.append(widget_id)
        elif not active and widget_id in active_list:
            active_list.remove(widget_id)
        self._data.setdefault("app", {})["active_widgets"] = active_list
        self.save()

    # --- Widget level settings ---

    def get_widget_config(self, widget_id: str) -> Dict[str, Any]:
        defaults = copy.deepcopy(DEFAULT_SETTINGS.get("widgets", {}).get(widget_id, {
            "enabled": True,
            "idle_threshold_seconds": 300,
            "always_on_top": True,
            "opacity": 0.95,
            "x": 100,
            "y": 100,
            "width": 320,
            "height": 180,
        }))
        current = self._data.setdefault("widgets", {}).setdefault(widget_id, dict(defaults))
        # Ensure default keys are present
        for k, v in defaults.items():
            if k not in current:
                current[k] = v
        return current

    def update_widget_config(self, widget_id: str, updates: Dict[str, Any]):
        cfg = self.get_widget_config(widget_id)
        cfg.update(updates)
        self.save()

    def set_widget_config(self, widget_id: str, updates: Dict[str, Any]):
        self.update_widget_config(widget_id, updates)

    def save_widget_geometry(self, widget_id: str, x: int, y: int, width: int, height: int, screen_name: str = ""):
        self.update_widget_config(widget_id, {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "screen_name": screen_name
        })
