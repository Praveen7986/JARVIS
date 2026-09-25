# My Widgets 🪟

A sleek, modular Windows 11 desktop widget platform built with **Python**, **PySide6**, and modern glassmorphism aesthetics.

Designed from the ground up for minimal CPU/RAM footprint, robust persistence, and seamless extensibility.

---

## 🚀 Features

* **Laptop Usage Monitor (MVP Widget)**:
  * ⏱️ **Accurate Timestamp-based Active Usage**: Measures actual user interaction (keyboard keystrokes, mouse moves, mouse clicks) using native Windows `GetLastInputInfo` API with zero system overhead.
  * 💤 **Idle Detection**: Pauses timer when user is idle for longer than the configurable threshold (default: 5 minutes) and excludes the idle duration from active time.
  * 🌙 **Automatic Midnight Rollover**: Seamlessly transitions daily usage at `00:00:00` without losing historical records.
  * 🔒 **Sleep & Lock Handling**: Automatically pauses tracking when the laptop goes to sleep or the Windows session is locked, and resumes only when user interaction recommences.
  * 📊 **Daily Progress Bar**: Displays today's usage ratio against the 24-hour day.
  * 🟢 **Real-time Status Badge**: Instant visual indicator showing `● Active` (green) or `○ Idle` (muted).
* **Modern Windows 11 Glass UI**:
  * Frameless, dark acrylic translucent appearance with rounded corners and drop shadows.
  * Smooth click-and-drag movement across monitors with boundary safety / screen clamping.
  * Right-click context menu (Always on Top, Opacity 40%–100%, Settings dialog, Reset Today's Data, Close Widget).
* **System Tray & App Lifecycle**:
  * Minimizes to Windows system tray with quick-toggle options.
  * Auto-start with Windows configuration (via `HKCU` registry, no admin privileges needed).
  * Single-instance lock to prevent duplicate background instances.
  * First-launch welcome onboarding experience.

---

## 🛠️ Project Structure

```text
MyWidgets/
│
├── main.py                     # Application entry point with single-instance lock
│
├── app/
│   ├── __init__.py
│   ├── application.py          # Central controller, lifecycle & native event filters
│   ├── base_widget.py          # Abstract BaseWidget with dragging, glass UI, context menus
│   ├── widget_manager.py       # Central widget registry and multi-monitor manager
│   ├── storage.py              # Resilient atomic JSON storage & corruption recovery
│   ├── settings.py             # App & widget preferences manager
│   ├── tray.py                 # Windows system tray integration
│   └── utils/
│       ├── __init__.py
│       ├── win_activity.py     # Native Windows GetLastInputInfo input activity detector
│       ├── win_power.py        # Windows session lock/unlock & sleep/wake listeners
│       └── autostart.py        # Windows HKCU Run registry autostart manager
│
├── widgets/
│   ├── __init__.py
│   └── laptop_usage/
│       ├── __init__.py
│       ├── widget.py           # Frameless dark glass UI with active/idle display
│       ├── tracker.py          # Accurate timestamp tracking engine & date rollover
│       └── settings_dialog.py  # Modal settings dialog for threshold, opacity, autostart
│
├── data/
│   ├── usage_data.json         # Historical usage database
│   └── app_settings.json       # Persisted widget positions and configurations
│
├── tests/
│   ├── test_storage.py         # Unit tests for storage and settings resilience
│   └── test_tracker.py         # Unit tests for duration formatting & midnight rollover
│
├── requirements.txt            # Python dependencies
└── README.md                   # Complete documentation
```

---

## 📦 Installation

### Prerequisites
* **Windows 10 / 11**
* **Python 3.10+** (Python 3.13 recommended)

### Setup

1. **Clone or navigate to the project directory**:
   ```bash
   cd "c:\Users\USER\Desktop\WIDGETS X"
   ```

2. **(Optional) Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🏃 Running the Application

Launch the desktop widget app:

```bash
python main.py
```

* On first run, a modern welcome card will appear. Click **Add Laptop Usage Widget** to place the widget on your desktop.
* The widget will save its position automatically as you drag it around.
* Right-click the widget to access **Always on Top**, **Opacity**, **Settings...**, or **Reset Today's Data**.
* Right-click the tray icon in the Windows taskbar to show/hide widgets or exit.

---

## ⚙️ How Usage Tracking Works

1. **Active Input Detection**:
   The tracker queries Windows `GetLastInputInfo` every second. This checks keyboard and mouse events across the entire OS at essentially 0% CPU consumption.
2. **Idle Threshold**:
   If no input is detected for longer than the idle threshold (default: 5 minutes, configurable to 1m, 5m, 10m, 15m, 30m), the widget switches from `● Active` to `○ Idle` and stops accumulating active usage. The idle period itself is excluded from the active tally.
3. **Session Lock & Sleep Detection**:
   When the screen is locked (`Win + L`) or the machine goes into sleep mode, tracking immediately suspends until the user unlocks and interacts with the machine again.
4. **Midnight Rollover**:
   When the system clock crosses midnight (`00:00:00`), the previous day's tally is permanently recorded in `data/usage_data.json`, and today's counter resets to `0h 00m`.

---

## 🧩 Adding Future Widgets

The platform is designed around a modular `BaseWidget` architecture:

1. Create a new folder inside `widgets/` (e.g. `widgets/system_monitor/`).
2. Subclass `BaseWidget` from `app.base_widget`:
   ```python
   from app.base_widget import BaseWidget
   from PySide6.QtWidgets import QLabel, QVBoxLayout

   class SystemMonitorWidget(BaseWidget):
       def __init__(self, widget_id="sys_mon", widget_manager=None, parent=None):
           super().__init__(widget_id=widget_id, widget_manager=widget_manager, parent=parent)
           layout = QVBoxLayout(self)
           layout.addWidget(QLabel("CPU: 12%"))

       def get_display_title(self) -> str:
           return "System Monitor"
   ```
3. Register the widget in `app/application.py` using `widget_manager.register_widget_type("sys_mon", SystemMonitorWidget)`.

---

## 🧪 Running Unit Tests

Run the test suite:

```bash
python -m unittest discover tests
```
