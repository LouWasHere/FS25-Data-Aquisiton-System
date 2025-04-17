import socket
import subprocess
import re
import time
import json
import math
import threading
from queue import Queue
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QGridLayout, QWidget, QProgressBar
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap

# Shared stop event for thread termination
stop_event = threading.Event()

# Enable testing mode
TEST_MODE = True

HOST = "0.0.0.0"
PORT = 5000

# Shared data structure for sensor data
sensor_data = Queue()
data_lock = threading.Lock()

# Shared variable for the latest sensor data
latest_sensor_data = None

# Mock functions for testing mode with dynamic values
def mock_get_imu_data():
    # Use time to create oscillating values for testing
    current_time = time.time()
    rpm = int((math.sin(current_time) + 1) * 7500)  # Oscillates between 0 and 15000
    speed = int((math.sin(current_time / 2) + 1) * 45)  # Oscillates between 0 and 90
    gear_position = str(int((math.sin(current_time / 3) + 1) * 3))  # Oscillates between 0 and 6
    connection = "Active" if int(current_time) % 2 == 0 else "Disconnected"  # Toggles every second

    return {
        "Linear Acceleration": f"{(math.sin(current_time) + 1) * 0.5:.2f} Gs",
        "Gyro X": f"{math.sin(current_time):.2f}",
        "Gyro Y": f"{math.cos(current_time):.2f}",
        "Gyro Z": f"{math.sin(current_time / 2):.2f}",
        "Compass Angle": f"{(math.sin(current_time) + 1) * 180:.2f}°",
        "Calibration Status": {"Sys": 3, "Gyro": 3, "Accel": 3, "Mag": 3},
        "RPM": rpm,
        "Speed": speed,
        "Gear Position": gear_position,
        "Connection": connection
    }

def mock_get_gps_data():
    # Simulate GPS coordinates moving in a small circle
    current_time = time.time()
    latitude = 51.5074 + 0.001 * math.sin(current_time / 10)
    longitude = -0.1278 + 0.001 * math.cos(current_time / 10)
    return {"Latitude": latitude, "Longitude": longitude}

def mock_get_serial_data():
    # Simulate a sensor value oscillating
    current_time = time.time()
    sensor_value = int((math.sin(current_time) + 1) * 5000)  # Oscillates between 0 and 10000
    return {"Sensor Value": sensor_value}

class SensorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Car Dashboard")
        self.setGeometry(0, 0, 480, 320)  # Adjusted for 480x320 resolution
        self.setStyleSheet("background-color: black;")

        self.layout = QGridLayout()

        # RPM Bar and Label
        self.rpm_bar = QProgressBar()
        self.rpm_bar.setRange(0, 15000)  # RPM range: 0 to 15000
        self.rpm_bar.setTextVisible(False)
        self.rpm_bar.setStyleSheet(
            "QProgressBar { background-color: #2F4F4F; } QProgressBar::chunk { background-color: #006400; }"
        )
        self.rpm_label = QLabel("0 RPM")
        self.rpm_label.setStyleSheet("font-size: 24pt; color: #00FF00; qproperty-alignment: AlignCenter;")

        # Speed Bar and Label
        self.speed_bar = QProgressBar()
        self.speed_bar.setRange(0, 90)  # Speed range: 0 to 90 km/h
        self.speed_bar.setTextVisible(False)
        self.speed_bar.setStyleSheet(
            "QProgressBar { background-color: #2F4F4F; } QProgressBar::chunk { background-color: #006400; }"
        )
        self.speed_label = QLabel("0 km/h")
        self.speed_label.setStyleSheet("font-size: 24pt; color: #00FF00; qproperty-alignment: AlignCenter;")

        # Gear Position
        self.gear_label = QLabel("N")
        self.gear_label.setStyleSheet("font-size: 48pt; color: #00FF00; qproperty-alignment: AlignCenter;")

        # Logo
        self.logo_label = QLabel()
        self.logo_label.setPixmap(QPixmap("logo.png").scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.logo_label.setAlignment(Qt.AlignCenter)

        # Connection Status
        self.connection_label = QLabel("Disconnected")
        self.connection_label.setStyleSheet("font-size: 18pt; color: #00FF00; qproperty-alignment: AlignCenter;")

        # Add widgets to the layout
        self.layout.addWidget(self.rpm_bar, 0, 0, 1, 3)  # RPM bar spans 3 columns
        self.layout.addWidget(self.rpm_label, 1, 0, 1, 3)  # RPM label spans 3 columns
        self.layout.addWidget(self.speed_bar, 2, 0, 1, 3)  # Speed bar spans 3 columns
        self.layout.addWidget(self.speed_label, 3, 0, 1, 3)  # Speed label spans 3 columns
        self.layout.addWidget(self.logo_label, 4, 0)  # Logo in bottom-left
        self.layout.addWidget(self.gear_label, 4, 1)  # Gear position in bottom-center
        self.layout.addWidget(self.connection_label, 4, 2)  # Connection status in bottom-right

        # Set the layout
        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        # Timer to update sensor data
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_sensor_data)
        self.timer.start(100)  # Update every 100ms for smooth bar updates

    def update_sensor_data(self):
        with data_lock:
            if not sensor_data.empty():
                latest_data = sensor_data.get()

                # Update RPM bar and label
                rpm = int(latest_data["IMU Data"].get("RPM", 0))
                self.rpm_bar.setValue(rpm)
                self.rpm_label.setText(f"{rpm} RPM")
                if rpm > 11250:  # Over 3/4 of 15000
                    self.rpm_bar.setStyleSheet(
                        "QProgressBar { background-color: #2F4F4F; } QProgressBar::chunk { background-color: red; }"
                    )
                elif rpm > 7500:  # Over half of 15000
                    self.rpm_bar.setStyleSheet(
                        "QProgressBar { background-color: #2F4F4F; } QProgressBar::chunk { background-color: orange; }"
                    )
                else:
                    self.rpm_bar.setStyleSheet(
                        "QProgressBar { background-color: #2F4F4F; } QProgressBar::chunk { background-color: #006400; }"
                    )

                # Update Speed bar and label
                speed = int(latest_data["IMU Data"].get("Speed", 0))
                self.speed_bar.setValue(speed)
                self.speed_label.setText(f"{speed} km/h")
                if speed > 67:  # Over 3/4 of 90
                    self.speed_bar.setStyleSheet(
                        "QProgressBar { background-color: #2F4F4F; } QProgressBar::chunk { background-color: red; }"
                    )
                elif speed > 45:  # Over half of 90
                    self.speed_bar.setStyleSheet(
                        "QProgressBar { background-color: #2F4F4F; } QProgressBar::chunk { background-color: orange; }"
                    )
                else:
                    self.speed_bar.setStyleSheet(
                        "QProgressBar { background-color: #2F4F4F; } QProgressBar::chunk { background-color: #006400; }"
                    )

                # Update Gear Position
                gear = latest_data["IMU Data"].get("Gear Position", "N")
                self.gear_label.setText(gear)

                # Update Connection Status
                connection = latest_data["IMU Data"].get("Connection", "Disconnected")
                self.connection_label.setText(connection)

    def closeEvent(self, event):
        """Handle the window close event."""
        stop_event.set()  # Signal all threads to stop
        event.accept()

# Function for data acquisition
def data_acquisition_thread():
    global latest_sensor_data
    while not stop_event.is_set():
        imu_data = mock_get_imu_data()
        gps_data = mock_get_gps_data()
        serial_data = mock_get_serial_data()

        with data_lock:
            # Update the latest sensor data
            latest_sensor_data = {
                "IMU Data": imu_data,
                "GPS Data": gps_data,
                "Serial Data": serial_data
            }
            # Add the data to the queue for UI updates
            sensor_data.put(latest_sensor_data)
        time.sleep(1)

# Function for UI
def ui_thread():
    app = QApplication([])
    window = SensorWindow()
    app.aboutToQuit.connect(stop_event.set)  # Ensure stop_event is set when the app quits
    window.showFullScreen()
    app.exec_()

# Function for networking
def networking_thread():
    global latest_sensor_data
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    print(f"Server listening on {HOST}:{PORT}")

    while not stop_event.is_set():
        try:
            server_socket.settimeout(1)  # Allow periodic checks for stop_event
            client_socket, client_address = server_socket.accept()
            print(f"Connection established with {client_address}")

            def handle_client(client_socket):
                try:
                    while not stop_event.is_set():
                        # Send the latest sensor data to the client
                        with data_lock:
                            if latest_sensor_data:
                                client_socket.sendall(json.dumps(latest_sensor_data).encode('utf-8') + b'\n')
                        time.sleep(1)  # Send data every second
                except (ConnectionResetError, BrokenPipeError):
                    print(f"Connection with {client_address} closed.")
                finally:
                    client_socket.close()

            # Start a new thread to handle the client
            client_handler = threading.Thread(target=handle_client, args=(client_socket,), daemon=True)
            client_handler.start()
        except socket.timeout:
            continue  # Check stop_event again

    server_socket.close()

# Start threads
if __name__ == "__main__":
    acquisition_thread = threading.Thread(target=data_acquisition_thread, daemon=True)
    ui_thread_instance = threading.Thread(target=ui_thread, daemon=True)
    networking_thread_instance = threading.Thread(target=networking_thread, daemon=True)

    acquisition_thread.start()
    ui_thread_instance.start()
    networking_thread_instance.start()

    acquisition_thread.join()
    ui_thread_instance.join()
    networking_thread_instance.join()