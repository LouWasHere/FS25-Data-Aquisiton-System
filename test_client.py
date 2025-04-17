import socket
import sys
import json
import threading
import csv
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QStackedWidget, QGridLayout
)
from PyQt5.QtCore import Qt, QTimer
from pyqtgraph import PlotWidget
import pyqtgraph as pg

class TestClientApp(QWidget):
    def __init__(self):
        super().__init__()
        self.client = None
        self.running = False
        self.recording = False
        self.csv_file = None
        self.csv_writer = None
        self.data = {}
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Local Telemetry Test Client')
        self.setFixedSize(1280, 720)  # Increased window size for better spacing

        # Create a stacked widget to switch between "logon" and "connected" screens
        self.stacked_widget = QStackedWidget(self)

        # Logon screen
        self.logon_screen = QWidget()
        self.initLogonScreen()
        self.stacked_widget.addWidget(self.logon_screen)

        # Connected screen
        self.connected_screen = QWidget()
        self.initConnectedScreen()
        self.stacked_widget.addWidget(self.connected_screen)

        # Set the initial screen to the logon screen
        layout = QVBoxLayout()
        layout.addWidget(self.stacked_widget)
        self.setLayout(layout)
        self.stacked_widget.setCurrentWidget(self.logon_screen)

    def initLogonScreen(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        self.address_label = QLabel('Server Address:')
        self.address_label.setStyleSheet("font-size: 16px;")
        self.address_input = QLineEdit(self)
        self.address_input.setText('127.0.0.1')  # Default to localhost

        self.port_label = QLabel('Server Port:')
        self.port_label.setStyleSheet("font-size: 16px;")
        self.port_input = QLineEdit(self)
        self.port_input.setText('5000')  # Default to match test_server.py

        self.connect_button = QPushButton('Connect', self)
        self.connect_button.setStyleSheet("font-size: 16px;")
        self.connect_button.clicked.connect(self.connect_to_server)

        layout.addWidget(self.address_label)
        layout.addWidget(self.address_input)
        layout.addWidget(self.port_label)
        layout.addWidget(self.port_input)
        layout.addWidget(self.connect_button)

        self.logon_screen.setLayout(layout)

    def initConnectedScreen(self):
        layout = QGridLayout()  # Use a grid layout for modular design
        layout.setSpacing(20)  # Increased spacing between widgets

        # Create labels for IMU Data
        self.data_labels = {}
        keys = ["RPM", "Speed", "Gear Position", "Linear Acceleration", "Gyro X", "Gyro Y", "Gyro Z", "Compass Angle"]
        for i, key in enumerate(keys):
            label_key = QLabel(f"{key}:")
            label_key.setStyleSheet("font-size: 14px; font-weight: bold;")
            label_value = QLabel("N/A")
            label_value.setStyleSheet("font-size: 14px;")
            self.data_labels[key] = label_value

            # Place each label in the grid
            row = i // 2
            col = (i % 2) * 2
            layout.addWidget(label_key, row, col)
            layout.addWidget(label_value, row, col + 1)

        # Add RPM graph
        self.rpm_graph_widget = PlotWidget()
        self.rpm_graph_widget.setBackground("w")
        self.rpm_graph_widget.setTitle("RPM Over Time", color="b", size="14pt")
        self.rpm_graph_widget.setLabel("left", "RPM")
        self.rpm_graph_widget.setLabel("bottom", "Time (s)")
        self.rpm_graph_widget.showGrid(x=True, y=True)
        self.rpm_graph_widget.setYRange(0, 15000)  # Set Y-axis range for RPM
        self.rpm_curve = self.rpm_graph_widget.plot(
            pen=pg.mkPen(color="r", width=2), name="RPM"
        )
        layout.addWidget(self.rpm_graph_widget, 3, 0, 2, 2)  # Spans 2 rows and 2 columns

        # Add Speed graph
        self.speed_graph_widget = PlotWidget()
        self.speed_graph_widget.setBackground("w")
        self.speed_graph_widget.setTitle("Speed Over Time", color="b", size="14pt")
        self.speed_graph_widget.setLabel("left", "Speed (km/h)")
        self.speed_graph_widget.setLabel("bottom", "Time (s)")
        self.speed_graph_widget.showGrid(x=True, y=True)
        self.speed_graph_widget.setYRange(0, 120)  # Set Y-axis range for Speed
        self.speed_curve = self.speed_graph_widget.plot(
            pen=pg.mkPen(color="g", width=2), name="Speed"
        )
        layout.addWidget(self.speed_graph_widget, 3, 2, 2, 2)  # Spans 2 rows and 2 columns

        # Add recording buttons
        self.start_recording_button = QPushButton('Start Recording', self)
        self.start_recording_button.setStyleSheet("font-size: 16px;")
        self.start_recording_button.clicked.connect(self.start_recording)
        layout.addWidget(self.start_recording_button, 5, 0)

        self.stop_recording_button = QPushButton('Stop Recording', self)
        self.stop_recording_button.setStyleSheet("font-size: 16px;")
        self.stop_recording_button.clicked.connect(self.stop_recording)
        self.stop_recording_button.setEnabled(False)  # Initially disabled
        layout.addWidget(self.stop_recording_button, 5, 1)

        # Add the shutdown button
        self.shutdown_button = QPushButton('Shutdown Server', self)
        self.shutdown_button.setStyleSheet("font-size: 16px;")
        self.shutdown_button.clicked.connect(self.shutdown_server)
        layout.addWidget(self.shutdown_button, 5, 3)  # Bottom-right corner

        self.connected_screen.setLayout(layout)

        # Timer for updating the graph
        self.graph_timer = QTimer()
        self.graph_timer.timeout.connect(self.update_graph)
        self.graph_timer.start(1000)  # Update every second

        # Initialize data storage for graphs
        self.rpm_data = []
        self.speed_data = []
        self.max_time_window = 20  # Display the last 20 seconds of data

    def connect_to_server(self):
        server_host = self.address_input.text()
        server_port = int(self.port_input.text())

        try:
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.connect((server_host, server_port))
            self.running = True
            self.stacked_widget.setCurrentWidget(self.connected_screen)
            threading.Thread(target=self.receive_data, daemon=True).start()
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", f"Failed to connect to server: {e}")

    def receive_data(self):
        try:
            while self.running:
                data = self.client.recv(1024)
                if not data:
                    break
                self.data = json.loads(data.decode())
                self.update_data_display()
                self.record_data_to_csv()
        except Exception as e:
            QMessageBox.critical(self, "Data Error", f"Error receiving data: {e}")
        finally:
            self.client.close()
            self.running = False

    def update_data_display(self):
        # Update the labels with the latest data
        imu_data = self.data.get("IMU Data", {})
        for key, label in self.data_labels.items():
            value = imu_data.get(key, "N/A")
            label.setText(str(value))

        # Update graph data
        self.rpm_data.append(imu_data.get("RPM", 0))
        self.speed_data.append(imu_data.get("Speed", 0))

        # Keep only the last 20 seconds of data
        if len(self.rpm_data) > self.max_time_window:
            self.rpm_data = self.rpm_data[-self.max_time_window:]
        if len(self.speed_data) > self.max_time_window:
            self.speed_data = self.speed_data[-self.max_time_window:]

    def update_graph(self):
        # Generate "T-" time values for the x-axis
        time_values = list(range(-len(self.rpm_data), 0))

        # Update the graphs
        self.rpm_curve.setData(time_values, self.rpm_data)
        self.speed_curve.setData(time_values, self.speed_data)

    def start_recording(self):
        self.csv_file = open('recorded_data.csv', 'w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(['Speed (km/h)', 'RPM', 'Gear Position', 'Linear Acceleration'])
        self.recording = True
        self.start_recording_button.setEnabled(False)
        self.stop_recording_button.setEnabled(True)

    def stop_recording(self):
        if self.csv_file:
            self.csv_file.close()
        self.recording = False
        self.start_recording_button.setEnabled(True)
        self.stop_recording_button.setEnabled(False)

    def record_data_to_csv(self):
        if self.recording and self.csv_writer:
            imu_data = self.data.get("IMU Data", {})
            speed = imu_data.get("Speed", "N/A")
            rpm = imu_data.get("RPM", "N/A")
            gear = imu_data.get("Gear Position", "N/A")
            linear_acceleration = imu_data.get("Linear Acceleration", "N/A")
            self.csv_writer.writerow([speed, rpm, gear, linear_acceleration])

    def shutdown_server(self):
        try:
            self.running = False
            self.client.sendall("shutdown".encode())
            self.client.close()
            QMessageBox.information(self, "Shutdown", "Server has been shut down.")
            self.stacked_widget.setCurrentWidget(self.logon_screen)
        except Exception as e:
            QMessageBox.critical(self, "Shutdown Error", f"Failed to shutdown server: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    test_client_app = TestClientApp()
    test_client_app.show()
    sys.exit(app.exec_())