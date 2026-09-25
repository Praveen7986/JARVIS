"""
Widget Manager for My Widgets platform.
Responsible for registering widget types, instantiating active widgets,
restoring/saving widget geometry, and reacting to display configuration changes.
"""

import logging
from typing import Dict, Type, Optional, List
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QGuiApplication
from .base_widget import BaseWidget
from .settings import SettingsManager
from .storage import StorageManager

logger = logging.getLogger(__name__)


class WidgetManager(QObject):
    """Central registry and lifecycle manager for all desktop widgets."""

    widget_visibility_changed = Signal(str, bool)

    def __init__(self, settings: SettingsManager, storage: StorageManager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.storage = storage
        self._registry: Dict[str, Type[BaseWidget]] = {}
        self._instances: Dict[str, BaseWidget] = {}

        # Listen to screen topology changes
        app = QGuiApplication.instance()
        if app:
            app.screenAdded.connect(self._handle_screens_changed)
            app.screenRemoved.connect(self._handle_screens_changed)

    def register_widget_type(self, widget_id: str, widget_cls: Type[BaseWidget]):
        """Register a widget class into the platform."""
        self._registry[widget_id] = widget_cls
        logger.info(f"Registered widget type: {widget_id}")

    def get_registered_types(self) -> List[str]:
        return list(self._registry.keys())

    def get_or_create_widget(self, widget_id: str) -> Optional[BaseWidget]:
        """Gets existing widget instance or creates a new one."""
        if widget_id in self._instances:
            return self._instances[widget_id]

        if widget_id not in self._registry:
            logger.warning(f"Widget type '{widget_id}' is not registered.")
            return None

        cls = self._registry[widget_id]
        instance = cls(widget_id=widget_id, widget_manager=self)
        self._instances[widget_id] = instance
        return instance

    def show_widget(self, widget_id: str) -> Optional[BaseWidget]:
        """Instantiates and shows the given widget."""
        instance = self.get_or_create_widget(widget_id)
        if instance:
            instance.show_widget()
            self.set_widget_enabled(widget_id, True)
            self.widget_visibility_changed.emit(widget_id, True)
        return instance

    def hide_widget(self, widget_id: str):
        """Hides the given widget."""
        if widget_id in self._instances:
            self._instances[widget_id].hide_widget()
            self.set_widget_enabled(widget_id, False)
            self.widget_visibility_changed.emit(widget_id, False)

    def is_widget_visible(self, widget_id: str) -> bool:
        if widget_id in self._instances:
            return self._instances[widget_id].isVisible()
        return False

    def set_widget_enabled(self, widget_id: str, enabled: bool):
        self.settings.set_widget_active(widget_id, enabled)

    def show_all_active(self):
        """Show all widgets that are flagged as active in settings."""
        active_ids = self.settings.get_active_widgets()
        for wid in active_ids:
            if wid in self._registry:
                self.show_widget(wid)

    def hide_all(self):
        """Hide all active widget windows without clearing active config."""
        for instance in self._instances.values():
            instance.hide()

    def show_all(self):
        """Show all initialized widgets."""
        for instance in self._instances.values():
            instance.show()
            instance.ensure_on_screen()

    def _handle_screens_changed(self, _screen=None):
        """Handle monitor connect/disconnect: keep widgets on valid screens."""
        logger.info("Screen configuration changed. Clamping widgets...")
        for instance in self._instances.values():
            if instance.isVisible():
                instance.ensure_on_screen()
