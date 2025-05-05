import socket
import subprocess
import re
import time
import json
import threading
from queue import Queue
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QGridLayout, QWidget
from PyQt5.QtCore import Qt, QTimer
import sensor_reading

HOST = "0.0.0.0"
PORT = 5000

# Shared data structure for sensor data
sensor_data = Queue()
data_lock = threading.Lock()

# UI Definition
class SensorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IMU Sensor Data")
        self.setGeometry(0, 0, 480, 320)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: black;")

        self.layout = QGridLayout()

        # Values and annotations
        self.accel_value = QLabel("")
        self.accel_annotation = QLabel("Lin.Accel")
        self.gyro_x_value = QLabel("")
        self.gyro_x_annotation = QLabel("Gyro X")
        self.gyro_y_value = QLabel("")
        self.gyro_y_annotation = QLabel("Gyro Y")
        self.gyro_z_value = QLabel("")
        self.gyro_z_annotation = QLabel("Gyro Z")
        self.compass_value = QLabel("")
        self.compass_annotation = QLabel("Deg")

        # Style the values
        value_style = "font-size: 24pt; color: green; qproperty-alignment: AlignCenter;"
        self.accel_value.setStyleSheet(value_style)
        self.gyro_x_value.setStyleSheet(value_style)
        self.gyro_y_value.setStyleSheet(value_style)
        self.gyro_z_value.setStyleSheet(value_style)
        self.compass_value.setStyleSheet(value_style)

        # Style the annotations
        annotation_style = "font-size: 12pt; color: white; qproperty-alignment: AlignCenter;"
        self.accel_annotation.setStyleSheet(annotation_style)
        self.gyro_x_annotation.setStyleSheet(annotation_style)
        self.gyro_y_annotation.setStyleSheet(annotation_style)
        self.gyro_z_annotation.setStyleSheet(annotation_style)
        self.compass_annotation.setStyleSheet(annotation_style)

        # Add widgets to the layout
        self.layout.addWidget(self.accel_value, 0, 0)
        self.layout.addWidget(self.accel_annotation, 1, 0)
        self.layout.addWidget(self.gyro_x_value, 0, 1)
        self.layout.addWidget(self.gyro_x_annotation, 1, 1)
        self.layout.addWidget(self.gyro_y_value, 0, 2)
        self.layout.addWidget(self.gyro_y_annotation, 1, 2)
        self.layout.addWidget(self.gyro_z_value, 2, 0)
        self.layout.addWidget(self.gyro_z_annotation, 3, 0)
        self.layout.addWidget(self.compass_value, 2, 1)
        self.layout.addWidget(self.compass_annotation, 3, 1)

        # Set the layout
        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        # Timer to update sensor data
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_sensor_data)
        self.timer.start(1000)  # Update every second

    def update_sensor_data(self):
        pass  # Placeholder for UI updates from the main thread

# Function for data acquisition
def data_acquisition_thread():
    while True:
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

    def update_ui():
        with data_lock:
            if not sensor_data.empty():
                latest_data = sensor_data.get()
                # Update the UI with the latest data
                window.accel_value.setText(latest_data["IMU Data"].get("Linear Acceleration", "N/A"))
                window.gyro_x_value.setText(latest_data["IMU Data"].get("Gyro X", "N/A"))
                window.gyro_y_value.setText(latest_data["IMU Data"].get("Gyro Y", "N/A"))
                window.gyro_z_value.setText(latest_data["IMU Data"].get("Gyro Z", "N/A"))
                window.compass_value.setText(latest_data["IMU Data"].get("Compass Angle", "N/A"))

    window.timer.timeout.connect(update_ui)
    window.showFullScreen()
    app.exec_()

# Function for networking
def networking_thread():
    print("Starting ngrok...")
    ngrok_process = subprocess.Popen(["ngrok", "tcp", str(PORT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)

    try:
        ngrok_tunnel_process = subprocess.run(["curl", "-s", "http://localhost:4040/api/tunnels"], capture_output=True, text=True)
        match = re.search(r'"public_url":"tcp://(.*?)"', ngrok_tunnel_process.stdout)
        if match:
            ngrok_url = match.group(1)
            print(f"Connect to the server using: {ngrok_url}")
        else:
            print("Error retrieving ngrok URL. Ensure ngrok is running and try again.")
    except Exception as e:
        print(f"Error fetching ngrok URL: {e}")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(1)

    print(f"Server listening on {HOST}:{PORT}")

    conn, addr = server.accept()
    print(f"Connected by {addr}")

    sensor_reading.power_on(sensor_reading.power_key)

    try:
        while True:
            with data_lock:
                if not sensor_data.empty():
                    latest_data = sensor_data.get()
                    conn.sendall(json.dumps(latest_data).encode())
                    print("Data sent.")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Server shutting down...")
    finally:
        sensor_reading.power_down(sensor_reading.power_key)
        conn.close()
        server.close()
        ngrok_process.terminate()
        print("ngrok connection terminated.")

# Start threads
if __name__ == "__main__":
    acquisition_thread = threading.Thread(target=data_acquisition_thread, daemon=True)
    ui_thread_instance = threading.Thread(target=ui_thread, daemon=True)
    networking_thread_instance = threading.Thread(target=networking_thread, daemon=True)

    acquisition_thread.start()
    ui_thread_instance.start()
    networking_thread_instance.start()

    acquisition_thread.join()
    networking_thread_instance.join()