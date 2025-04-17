import socket
import sys
import json
import threading
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox

class TestClientApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.client = None
        self.running = False

    def initUI(self):
        self.setWindowTitle('Local Telemetry Test Client')
        self.layout = QVBoxLayout()

        self.address_label = QLabel('Server Address:')
        self.address_input = QLineEdit(self)
        self.address_input.setText('127.0.0.1')  # Default to localhost
        self.port_label = QLabel('Server Port:')
        self.port_input = QLineEdit(self)
        self.port_input.setText('5000')  # Default to match test_server.py
        self.connect_button = QPushButton('Connect', self)
        self.connect_button.clicked.connect(self.connect_to_server)

        self.data_label = QLabel('Received Data:')
        self.data_display = QLabel('No data received yet.')

        self.shutdown_button = QPushButton('Shutdown Server', self)
        self.shutdown_button.clicked.connect(self.shutdown_server)
        self.shutdown_button.setEnabled(False)

        self.layout.addWidget(self.address_label)
        self.layout.addWidget(self.address_input)
        self.layout.addWidget(self.port_label)
        self.layout.addWidget(self.connect_button)
        self.layout.addWidget(self.data_label)
        self.layout.addWidget(self.data_display)
        self.layout.addWidget(self.shutdown_button)

        self.setLayout(self.layout)
        self.show()

    def connect_to_server(self):
        server_host = self.address_input.text()
        server_port = int(self.port_input.text())

        try:
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.connect((server_host, server_port))
            self.running = True
            self.shutdown_button.setEnabled(True)
            threading.Thread(target=self.receive_data, daemon=True).start()
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", f"Failed to connect to server: {e}")

    def receive_data(self):
        try:
            while self.running:
                data = self.client.recv(1024)
                if not data:
                    break
                data_dict = json.loads(data.decode())
                formatted_data = json.dumps(data_dict, indent=4)
                self.data_display.setText(f"Received Data:\n{formatted_data}")
        except Exception as e:
            QMessageBox.critical(self, "Data Error", f"Error receiving data: {e}")
        finally:
            self.client.close()
            self.running = False

    def shutdown_server(self):
        try:
            self.running = False
            self.client.sendall("shutdown".encode())
            self.client.close()
            self.shutdown_button.setEnabled(False)
            QMessageBox.information(self, "Shutdown", "Server has been shut down.")
        except Exception as e:
            QMessageBox.critical(self, "Shutdown Error", f"Failed to shutdown server: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    test_client_app = TestClientApp()
    sys.exit(app.exec_())