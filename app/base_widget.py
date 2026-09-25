"""
BaseWidget class providing foundation for modular desktop widgets.
Features:
- Frameless transparent window
- Smooth mouse drag and drop
- Multi-monitor boundary safety / screen clamping
- Window flags (Always On Top, Taskbar visibility)
- Standardized context menu & state persistence
"""

import logging
from typing import Optional, TYPE_CHECKING
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QMouseEvent, QContextMenuEvent, QAction, QCursor, QGuiApplication
from PySide6.QtWidgets import QWidget, QMenu, QGraphicsDropShadowEffect
from PySide6.QtGui import QColor

if TYPE_CHECKING:
    from .widget_manager import WidgetManager
    from .settings import SettingsManager

logger = logging.getLogger(__name__)


class BaseWidget(QWidget):
    """Abstract base class for desktop widgets."""

    # Signal emitted when widget requests to be closed/hidden or settings opened
    closed = Signal(str)
    settings_requested = Signal(str)

    def __init__(self, widget_id: str, widget_manager: Optional['WidgetManager'] = None, parent=None):
        super().__init__(parent)
        self.widget_id = widget_id
        self.widget_manager = widget_manager
        self._drag_pos: Optional[QPoint] = None
        self._is_dragging = False

        self._always_on_top = True
        self._opacity = 0.95

        # Initialize base window flags & attributes
        self._init_window_flags()
        self._setup_shadow()

    def _init_window_flags(self):
        """Configure frameless, translucent, desktop-widget window flags."""
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        if self._always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint

        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

    def _setup_shadow(self):
        """Add subtle modern drop shadow around widget."""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    # --- Geometry & Multi-Monitor Clamping ---

    def ensure_on_screen(self):
        """Ensures the widget position is within the visible boundaries of an active screen."""
        screens = QGuiApplication.screens()
        if not screens:
            return

        current_geo = self.frameGeometry()
        widget_center = current_geo.center()

        # Check if center is within any screen
        on_valid_screen = any(screen.geometry().contains(widget_center) for screen in screens)

        if not on_valid_screen:
            # Re-position to primary screen center/top-right
            primary = QGuiApplication.primaryScreen()
            if primary:
                avail = primary.availableGeometry()
                new_x = avail.right() - self.width() - 40
                new_y = avail.top() + 60
                self.move(new_x, new_y)
                logger.info(f"Widget {self.widget_id} clamped back to primary screen at ({new_x}, {new_y})")

    # --- Mouse Drag Interaction ---

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_dragging and self._drag_pos is not None:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            self.move(new_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            self.unsetCursor()
            self.ensure_on_screen()
            self.save_state()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    # --- Context Menu ---

    def contextMenuEvent(self, event: QContextMenuEvent):
        menu = QMenu(self)
        self.build_context_menu(menu)
        menu.exec(event.globalPos())
        event.accept()

    def build_context_menu(self, menu: QMenu):
        """Populate the right-click context menu."""
        title_action = menu.addAction(self.get_display_title())
        title_action.setEnabled(False)
        menu.addSeparator()

        # Always on Top toggle
        aot_action = QAction("Always on Top", menu, checkable=True)
        aot_action.setChecked(self._always_on_top)
        aot_action.toggled.connect(self.set_always_on_top)
        menu.addAction(aot_action)

        # Opacity Submenu
        opacity_menu = menu.addMenu("Opacity")
        for pct in [100, 95, 90, 80, 70]:
            op_action = QAction(f"{pct}%", opacity_menu, checkable=True)
            op_action.setChecked(abs(self._opacity - (pct / 100.0)) < 0.02)
            op_action.triggered.connect(lambda checked=False, val=pct / 100.0: self.set_opacity(val))
            opacity_menu.addAction(op_action)

        menu.addSeparator()

        # Open Dashboard
        dashboard_action = menu.addAction("Open Dashboard")
        dashboard_action.triggered.connect(lambda: self.settings_requested.emit(self.widget_id))

        # Hook for custom actions in subclasses
        self.add_custom_menu_actions(menu)

        menu.addSeparator()

        # Close
        close_action = menu.addAction("Close Widget")
        close_action.triggered.connect(self.hide_widget)

    def add_custom_menu_actions(self, menu: QMenu):
        """Override in subclasses to insert widget-specific menu items."""
        pass

    def get_display_title(self) -> str:
        """Returns the widget title for menu headers."""
        return "Widget"

    # --- Window Controls & State Management ---

    def set_always_on_top(self, enable: bool):
        self._always_on_top = enable
        flags = self.windowFlags()
        if enable:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint

        # Re-apply flags
        self.setWindowFlags(flags)
        self.show()
        self.save_state()

    def set_opacity(self, opacity: float):
        self._opacity = max(0.2, min(1.0, opacity))
        self.setWindowOpacity(self._opacity)
        self.save_state()

    def show_widget(self):
        """Display the widget and ensure screen boundary safety."""
        self.load_state()
        self.show()
        self.ensure_on_screen()
        if self.widget_manager:
            self.widget_manager.set_widget_enabled(self.widget_id, True)

    def hide_widget(self):
        """Hide the widget."""
        self.hide()
        if self.widget_manager:
            self.widget_manager.set_widget_enabled(self.widget_id, False)
        self.closed.emit(self.widget_id)

    def save_state(self):
        """Persist widget geometry and visual preferences."""
        if not self.widget_manager or not self.widget_manager.settings:
            return

        geo = self.geometry()
        current_screen = QGuiApplication.screenAt(geo.center())
        screen_name = current_screen.name() if current_screen else ""

        self.widget_manager.settings.update_widget_config(self.widget_id, {
            "x": geo.x(),
            "y": geo.y(),
            "width": geo.width(),
            "height": geo.height(),
            "always_on_top": self._always_on_top,
            "opacity": self._opacity,
            "screen_name": screen_name,
        })

    def load_state(self):
        """Restore widget geometry and visual preferences."""
        if not self.widget_manager or not self.widget_manager.settings:
            return

        cfg = self.widget_manager.settings.get_widget_config(self.widget_id)
        x = cfg.get("x", 100)
        y = cfg.get("y", 100)
        w = cfg.get("width", 320)
        h = cfg.get("height", 180)
        self._always_on_top = cfg.get("always_on_top", True)
        self._opacity = cfg.get("opacity", 0.95)

        self.resize(w, h)
        self.move(x, y)
        self.setWindowOpacity(self._opacity)

        # Update flags
        flags = self.windowFlags()
        if self._always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
