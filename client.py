import socket
import sys
import json
import threading
import csv
import folium  # For map rendering
import os  # Import os to handle file paths
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QStackedWidget, QGridLayout
)
from PyQt5.QtCore import Qt, QTimer, QUrl, QMetaObject, Q_ARG, pyqtSlot
from PyQt5.QtWebEngineWidgets import QWebEngineView  # For displaying the map
from pyqtgraph import PlotWidget
import pyqtgraph as pg
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MapWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("GPS Map")
        self.setFixedSize(800, 600)

        layout = QVBoxLayout()

        # Web view to display the map
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)

        self.setLayout(layout)

        # Load the static HTML file
        map_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "map.html")
        self.web_view.setUrl(QUrl.fromLocalFile(map_file_path))

    def update_marker(self, latitude, longitude):
        # Validate latitude and longitude
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            logging.error(f"Invalid latitude or longitude: {latitude}, {longitude}")
            return

        # Log the latitude and longitude
        # logging.debug(f"Updating marker to latitude: {latitude}, longitude: {longitude}")

        # Ensure this runs in the main thread
        QMetaObject.invokeMethod(self, "execute_js", Qt.QueuedConnection, 
                                 Q_ARG(float, latitude), Q_ARG(float, longitude))

    @pyqtSlot(float, float)
    def execute_js(self, latitude, longitude):
        js_code = f"updateMarker({latitude}, {longitude});"
        self.web_view.page().runJavaScript(js_code, self.handle_js_result)

    def handle_js_result(self, result):
        if result is None:
            return
            #logging.debug("JavaScript executed successfully.")
        else:
            logging.error(f"JavaScript error: {result}")


class TestClientApp(QWidget):
    def __init__(self):
        super().__init__()
        self.client = None
        self.running = False
        self.recording = False
        self.csv_file = None
        self.csv_writer = None
        self.data = {}
        self.map_window = None  # Reference to the Map window
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

        # Add a dedicated row for the timestamp
        timestamp_layout = QHBoxLayout()
        self.timestamp_label = QLabel("Timestamp: N/A")
        self.timestamp_label.setStyleSheet("font-size: 16px; font-weight: bold; color: blue;")
        timestamp_layout.addWidget(self.timestamp_label)
        layout.addLayout(timestamp_layout, 0, 0, 1, 4)  # Spans the entire top row

        # Create labels for IMU Data and Engine Temperature
        self.data_labels = {}
        keys = ["RPM", "Speed", "Gear Position", "Linear Acceleration", "Engine Temperature"]
        for i, key in enumerate(keys):
            label_key = QLabel(f"{key}:")
            label_key.setStyleSheet("font-size: 14px; font-weight: bold;")
            label_value = QLabel("N/A")
            label_value.setStyleSheet("font-size: 14px;")
            self.data_labels[key] = label_value

            # Place each label in the grid
            row = (i // 2) + 1  # Start from row 1 (row 0 is for the timestamp)
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
        layout.addWidget(self.rpm_graph_widget, 4, 0, 2, 2)  # Spans 2 rows and 2 columns

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
        layout.addWidget(self.speed_graph_widget, 4, 2, 2, 2)  # Spans 2 rows and 2 columns

        # Add the Map button
        self.map_button = QPushButton('Show Map', self)
        self.map_button.setStyleSheet("font-size: 16px;")
        self.map_button.clicked.connect(self.show_map_window)
        layout.addWidget(self.map_button, 6, 2)

        # Add recording buttons
        self.start_recording_button = QPushButton('Start Recording', self)
        self.start_recording_button.setStyleSheet("font-size: 16px;")
        self.start_recording_button.clicked.connect(self.start_recording)
        layout.addWidget(self.start_recording_button, 6, 0)

        self.stop_recording_button = QPushButton('Stop Recording', self)
        self.stop_recording_button.setStyleSheet("font-size: 16px;")
        self.stop_recording_button.clicked.connect(self.stop_recording)
        self.stop_recording_button.setEnabled(False)  # Initially disabled
        layout.addWidget(self.stop_recording_button, 6, 1)

        # Add the shutdown button
        self.shutdown_button = QPushButton('Close Connection', self)
        self.shutdown_button.setStyleSheet("font-size: 16px;")
        self.shutdown_button.clicked.connect(self.shutdown_server)
        layout.addWidget(self.shutdown_button, 6, 3)  # Bottom-right corner

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
        print(f"Trying to connect to {server_host}:{server_port}")
        try:
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.connect((server_host, server_port))
            print("Connected!")
            self.running = True
            self.stacked_widget.setCurrentWidget(self.connected_screen)
            threading.Thread(target=self.receive_data, daemon=True).start()
        except Exception as e:
            print(f"Failed to connect: {e}")
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
        # Match the data sent in server.py
        imu_data = self.data.get("IMU Data", {})
        serial_data = self.data.get("Serial Data", {})
        rs232_data = self.data.get("RS232 Data", {})
        gps_data = self.data.get("GPS Data", {})
        timestamp = self.data.get("Timestamp", "N/A")

        self.timestamp_label.setText(f"Timestamp: {timestamp}")

        # Map UI keys to their data sources as per server.py
        for key, label in self.data_labels.items():
            if key == "RPM":
                value = rs232_data.get("RPM", "N/A")
            elif key == "Speed":
                value = serial_data.get("Wheel Speed", "N/A")
            elif key == "Gear Position":
                value = rs232_data.get("Gear", "N/A")
            elif key == "Engine Temperature":
                temp = rs232_data.get("Engine Temperature", "N/A")
                try:
                    temp_val = float(temp)
                except (ValueError, TypeError):
                    temp_val = 0
                value = f"{temp_val:.1f} °C"
                if temp_val > 60:
                    label.setStyleSheet("font-size: 14px; color: #FF0000;")
                else:
                    label.setStyleSheet("font-size: 14px; color: #FFFFFF;")
            else:
                value = imu_data.get(key, "N/A")
            label.setText(str(value))

        # Update graph data (RPM and Speed from correct sources)
        rpm_val = rs232_data.get("RPM", 0)
        speed_val = serial_data.get("Wheel Speed", 0)
        try:
            rpm_val = float(rpm_val)
        except (ValueError, TypeError):
            rpm_val = 0
        try:
            speed_val = float(speed_val)
        except (ValueError, TypeError):
            speed_val = 0
        self.rpm_data.append(rpm_val)
        self.speed_data.append(speed_val)

        # Keep only the last 20 seconds of data
        if len(self.rpm_data) > self.max_time_window:
            self.rpm_data = self.rpm_data[-self.max_time_window:]
        if len(self.speed_data) > self.max_time_window:
            self.speed_data = self.speed_data[-self.max_time_window:]

        # Update the map window if open
        if self.map_window:
            latitude = gps_data.get("Latitude", 0)
            longitude = gps_data.get("Longitude", 0)
            self.map_window.update_marker(latitude, longitude)

    def update_graph(self):
        # Generate "T-" time values for the x-axis
        time_values = list(range(-len(self.rpm_data), 0))

        # Update the graphs
        self.rpm_curve.setData(time_values, self.rpm_data)
        self.speed_curve.setData(time_values, self.speed_data)

    def start_recording(self):
        # Flatten the current data structure to get all keys for the header
        flat_data = self.flatten_dict(self.data)
        self.csv_header = list(flat_data.keys())
        self.csv_file = open('recorded_data.csv', 'w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(self.csv_header)
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
            flat_data = self.flatten_dict(self.data)
            # Ensure all columns are present in the same order as the header
            row = [flat_data.get(col, "N/A") for col in self.csv_header]
            self.csv_writer.writerow(row)

    def flatten_dict(self, d, parent_key='', sep='.'):
        """Recursively flattens a nested dictionary."""
        items = {}
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.update(self.flatten_dict(v, new_key, sep=sep))
            else:
                items[new_key] = v
        return items

    def show_map_window(self):
        if not self.map_window:
            self.map_window = MapWindow()
        self.map_window.show()

    def shutdown_server(self):
        try:
            self.running = False
            self.client.sendall("shutdown".encode())
            self.client.close()
            QMessageBox.information(self, "Shutdown", "Connection Closed.")
            self.stacked_widget.setCurrentWidget(self.logon_screen)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to close connection: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    test_client_app = TestClientApp()
    test_client_app.show()
    sys.exit(app.exec_())