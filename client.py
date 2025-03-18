import socket
import sys
import json
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox

class ClientApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Telemetry Data Receiver')
        self.layout = QVBoxLayout()

        self.address_label = QLabel('Ngrok Address:')
        self.address_input = QLineEdit(self)
        self.port_label = QLabel('Ngrok Port:')
        self.port_input = QLineEdit(self)
        self.connect_button = QPushButton('Connect', self)
        self.connect_button.clicked.connect(self.connect_to_server)

        self.name_label = QLabel('Name: ')
        self.value_label = QLabel('Value: ')

        self.shutdown_button = QPushButton('Shutdown Server', self)
        self.shutdown_button.clicked.connect(self.shutdown_server)
        self.shutdown_button.setEnabled(False)

        self.layout.addWidget(self.address_label)
        self.layout.addWidget(self.address_input)
        self.layout.addWidget(self.port_label)
        self.layout.addWidget(self.port_input)
        self.layout.addWidget(self.connect_button)
        self.layout.addWidget(self.name_label)
        self.layout.addWidget(self.value_label)
        self.layout.addWidget(self.shutdown_button)

        self.setLayout(self.layout)
        self.show()

    def connect_to_server(self):
        ngrok_host = self.address_input.text()
        ngrok_port = int(self.port_input.text())

        try:
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.connect((ngrok_host, ngrok_port))
            self.shutdown_button.setEnabled(True)
            self.receive_data()
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", f"Failed to connect to server: {e}")

    def receive_data(self):
        while True:
            data = self.client.recv(1024)
            if not data:
                break
            data_dict = json.loads(data.decode())
            self.name_label.setText(f"Name: {data_dict.get('name', 'N/A')}")
            self.value_label.setText(f"Value: {data_dict.get('value', 'N/A')}")

    def shutdown_server(self):
        try:
            self.client.sendall("shutdown".encode())
            self.client.close()
            self.shutdown_button.setEnabled(False)
            QMessageBox.information(self, "Shutdown", "Server has been shut down.")
        except Exception as e:
            QMessageBox.critical(self, "Shutdown Error", f"Failed to shutdown server: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    client_app = ClientApp()
    sys.exit(app.exec_())