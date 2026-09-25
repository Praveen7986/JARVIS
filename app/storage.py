"""
Persistent data storage manager for My Widgets.
Handles atomic reads/writes, corruption recovery, and structured schema.
"""

import copy
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages reading and writing JSON data files with resilience against corruption."""

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            # Default to project data directory
            self.data_dir = Path(__file__).resolve().parent.parent / "data"
        else:
            self.data_dir = Path(data_dir)

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.usage_file = self.data_dir / "usage_data.json"
        self.settings_file = self.data_dir / "app_settings.json"

    def load_json(self, file_path: Path, default_factory: Any) -> Dict[str, Any]:
        """Loads a JSON file safely. If corrupt or missing, creates backup and returns default."""
        if not file_path.exists():
            default_val = default_factory() if callable(default_factory) else default_factory
            self.save_json(file_path, default_val)
            return default_val

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}. Creating backup and resetting.")
            try:
                backup_path = file_path.with_suffix(f".bak_{int(datetime.now().timestamp())}")
                shutil.copyfile(file_path, backup_path)
            except Exception as backup_err:
                logger.warning(f"Could not create backup of corrupt file: {backup_err}")

            default_val = default_factory() if callable(default_factory) else default_factory
            self.save_json(file_path, default_val)
            return default_val

    def save_json(self, file_path: Path, data: Dict[str, Any]) -> bool:
        """Atomically saves data to a JSON file via a temporary file."""
        temp_file = file_path.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            # Atomic replace
            os.replace(temp_file, file_path)
            return True
        except Exception as e:
            logger.error(f"Failed to save JSON to {file_path}: {e}")
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            return False

    # --- Usage Data Specific Methods ---

    def load_usage_data(self) -> Dict[str, Any]:
        """Loads usage history data."""
        return self.load_json(self.usage_file, dict)

    def save_usage_data(self, data: Dict[str, Any]) -> bool:
        """Saves usage history data."""
        return self.save_json(self.usage_file, data)

    def get_day_usage(self, date_str: str) -> int:
        """Retrieves usage seconds for a specific date (YYYY-MM-DD)."""
        data = self.load_usage_data()
        day_entry = data.get(date_str, {})
        return day_entry.get("usage_seconds", 0)

    def set_day_usage(self, date_str: str, seconds: int) -> bool:
        """Sets usage seconds for a specific date (YYYY-MM-DD)."""
        data = self.load_usage_data()
        if date_str not in data:
            data[date_str] = {}
        data[date_str]["usage_seconds"] = int(seconds)
        data[date_str]["last_updated"] = datetime.now().isoformat()
        return self.save_usage_data(data)

    def reset_day_usage(self, date_str: str) -> bool:
        """Resets a day's usage to 0."""
        return self.set_day_usage(date_str, 0)

    # --- Settings Specific Methods ---

    def load_settings(self, default_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Loads application and widget settings with defaults merged."""
        saved = self.load_json(self.settings_file, default_settings)
        # Deep copy defaults so original constant is never mutated
        result = copy.deepcopy(default_settings)
        for key, val in saved.items():
            if isinstance(val, dict) and isinstance(result.get(key), dict):
                result[key].update(val)
            else:
                result[key] = copy.deepcopy(val)
        return result

    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """Saves application and widget settings."""
        return self.save_json(self.settings_file, settings)
