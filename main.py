"""
My Widgets - Modern Windows Desktop Widget Platform.
Entry point for application lifecycle.
"""

import sys
import logging
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from app.application import MyWidgetsApp

# Configure logging
log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=log_format)
logger = logging.getLogger("MyWidgets")


def main():
    # Set app attributes
    QApplication.setApplicationName("MyWidgets")
    QApplication.setOrganizationName("MyWidgetsApp")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Single-instance enforcement using QLocalServer
    server_name = "MyWidgets_SingleInstance_Lock"
    socket = QLocalSocket()
    socket.connectToServer(server_name)

    if socket.waitForConnected(500):
        # Already running; notify primary instance and exit
        logger.warning("Another instance of My Widgets is already running.")
        socket.write(b"SHOW")
        socket.waitForBytesWritten(1000)
        sys.exit(0)

    # Primary instance: create server
    server = QLocalServer()
    server.removeServer(server_name)
    server.listen(server_name)

    my_widgets_app = MyWidgetsApp(app)

    def handle_new_connection():
        client_sock = server.nextPendingConnection()
        if client_sock:
            client_sock.readyRead.connect(lambda: _on_client_message(client_sock, my_widgets_app))

    def _on_client_message(sock, app_instance):
        msg = bytes(sock.readAll()).decode("utf-8")
        if msg == "SHOW":
            app_instance.show_main_window()
            app_instance.widget_manager.show_all()

    server.newConnection.connect(handle_new_connection)

    # Launch application
    my_widgets_app.run()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
