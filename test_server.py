import socket
import subprocess
import re
import time
import json
import threading
from queue import Queue
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QGridLayout, QWidget, QProgressBar
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap
# import sensor_reading

# Enable testing mode
TEST_MODE = True

HOST = "0.0.0.0"
PORT = 5000

# Shared data structure for sensor data
sensor_data = Queue()
data_lock = threading.Lock()

# Mock functions for testing mode
def mock_get_imu_data():
    return {
        "Linear Acceleration": "1.23 Gs",
        "Gyro X": "0.12",
        "Gyro Y": "0.34",
        "Gyro Z": "0.56",
        "Compass Angle": "45.67°",
        "Calibration Status": {"Sys": 3, "Gyro": 3, "Accel": 3, "Mag": 3},
        "RPM": "1500",
        "Speed": "60",
        "Gear Position": "2",
        "Connection": "Active"
    }

def mock_get_gps_data():
    return {"Latitude": 51.5074, "Longitude": -0.1278}  # Example: London coordinates

def mock_get_serial_data():
    return {"Sensor Value": "12345"}

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

                # Update Speed bar and label
                speed = int(latest_data["IMU Data"].get("Speed", 0))
                self.speed_bar.setValue(speed)
                self.speed_label.setText(f"{speed} km/h")

                # Update Gear Position
                gear = latest_data["IMU Data"].get("Gear Position", "N")
                self.gear_label.setText(gear)

                # Update Connection Status
                connection = latest_data["IMU Data"].get("Connection", "Disconnected")
                self.connection_label.setText(connection)

# Function for data acquisition
def data_acquisition_thread():
    while True:
        if TEST_MODE:
            imu_data = mock_get_imu_data()
            gps_data = mock_get_gps_data()
            serial_data = mock_get_serial_data()
        else:
            imu_data = sensor_reading.get_imu_data()
            gps_data = sensor_reading.get_gps_data()
            serial_data = sensor_reading.get_serial_data()

        with data_lock:
            sensor_data.put({
                "IMU Data": imu_data,
                "GPS Data": gps_data,
                "Serial Data": serial_data
            })
        time.sleep(1)

# Function for UI
def ui_thread():
    app = QApplication([])
    window = SensorWindow()
    window.showFullScreen()
    app.exec_()

# Start threads
if __name__ == "__main__":
    acquisition_thread = threading.Thread(target=data_acquisition_thread, daemon=True)
    ui_thread_instance = threading.Thread(target=ui_thread, daemon=True)

    acquisition_thread.start()
    ui_thread_instance.start()

    acquisition_thread.join()
    ui_thread_instance.join()