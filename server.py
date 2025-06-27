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

try:
    import sensor_reading # Will only work on a Pi, so it is optional for testing mode.
except ImportError:
    pass

# Shared stop event for thread termination
stop_event = threading.Event()

# Enable testing mode
TEST_MODE = True

# Temporary host and port for testing
HOST = "0.0.0.0"
PORT = 5000

# Shared data structure for sensor data
sensor_data = Queue()
data_lock = threading.Lock()

# Shared variable for the latest sensor data
latest_sensor_data = None

# Flag to track client connection status
client_connected = False

# Mock functions for testing mode with dynamic values
def mock_get_imu_data():
    # Use time to create oscillating values for testing
    current_time = time.time()
    rpm = int((math.sin(current_time) + 1) * 7500)  # Oscillates between 0 and 15000
    speed = int((math.sin(current_time / 2) + 1) * 45)  # Oscillates between 0 and 90
    gear_position = str(int((math.sin(current_time / 3) + 1) * 3))  # Oscillates between 0 and 6

    # Use the client_connected flag to set the connection status
    connection = "Active" if client_connected else "Disconnected"

    return {
        "Linear Acceleration": f"{(math.sin(current_time) + 1) * 0.5:.2f} Gs",
        "Gyro X": f"{math.sin(current_time):.2f}",
        "Gyro Y": f"{math.cos(current_time):.2f}",
        "Gyro Z": f"{math.sin(current_time / 2):.2f}",
        "Temperature": f"{(math.sin(current_time / 3) + 1) * 20:.2f} °C"
    }

def mock_get_gps_data():
    # Simulate GPS coordinates moving in a small circle
    current_time = time.time()
    latitude = 51.5074 + 0.001 * math.sin(current_time / 10)
    longitude = -0.1278 + 0.001 * math.cos(current_time / 10)
    return {"Latitude": latitude, "Longitude": longitude}

def mock_get_serial_data():
    # Simulate sensor values oscillating
    current_time = time.time()
    wheel_speed = int((math.sin(current_time / 5) + 1) * 45)  # Oscillates between 0 and 90
    neutral_flag = int((math.sin(current_time / 2) + 1))  # Oscillates between 0 and 1

    return {
        "Wheel Speed": wheel_speed,
        "Neutral Flag": neutral_flag,
    }

def mock_get_rs232_data():
    # Simulate RS232 data
    current_time = time.time()
    rpm = int((math.sin(current_time) + 1) * 7500)  # Oscillates between 0 and 15000
    throttle_position = int((math.sin(current_time / 2) + 1) * 100)  # Oscillates between 0 and 100
    engine_temperature = int((math.sin(current_time / 3) + 1) * 100)  # Oscillates between 0 and 100
    drive_speed = int((math.sin(current_time / 4) + 1) * 90)  # Oscillates between 0 and 90
    ground_speed = int((math.sin(current_time / 5) + 1) * 90)  # Oscillates between 0 and 90
    gear = str(int((math.sin(current_time / 6) + 1) * 3))  # Oscillates between 0 and 6
    return {
        "RPM": rpm,
        "Throttle Position": throttle_position,
        "Engine Temperature": engine_temperature,
        "Drive Speed": drive_speed,
        "Ground Speed": ground_speed,
        "Gear": gear
    }

class SensorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Car Dashboard")
        self.setFixedSize(480, 320)  # Fixed size to prevent stretching
        self.setGeometry(0, 0, 480, 320)  # Adjusted for 480x320 resolution
        self.setStyleSheet("background-color: black;")

        self.layout = QGridLayout()
        self.layout.setSpacing(5)  # Add consistent spacing
        self.layout.setContentsMargins(10, 10, 10, 10)  # Add margins

        # RPM Bar and Label
        self.rpm_bar = QProgressBar()
        self.rpm_bar.setRange(0, 15000)  # RPM range: 0 to 15000
        self.rpm_bar.setTextVisible(False)
        self.rpm_bar.setStyleSheet(
            "QProgressBar { background-color: #2F4F4F; } QProgressBar::chunk { background-color: #006400; }"
        )
        self.rpm_label = QLabel("0 RPM")
        self.rpm_label.setStyleSheet("font-size: 18pt; color: #00FF00; qproperty-alignment: AlignCenter;")

        # Speed Label (no bar)
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
        self.connection_label.setStyleSheet("font-size: 14pt; color: #00FF00; qproperty-alignment: AlignCenter;")
        self.ngrok_url_displayed = False  # Track if we've set the ngrok URL

        # Engine Temperature Label
        self.engine_temp_label = QLabel("Engine Temp: -- °C")
        self.engine_temp_label.setStyleSheet("font-size: 14pt; color: #FFFFFF; qproperty-alignment: AlignCenter;")

        # Add widgets to the layout
        self.layout.addWidget(self.rpm_bar, 0, 0, 1, 3)  # RPM bar spans 3 columns
        self.layout.addWidget(self.rpm_label, 1, 0, 1, 3)  # RPM label spans 3 columns
        self.layout.addWidget(self.gear_label, 2, 1)  # Gear position in center
        self.layout.addWidget(self.speed_label, 3, 1)  # Speed label below gear in center
        self.layout.addWidget(self.engine_temp_label, 4, 1)  # Engine temp label below speed in center
        self.layout.addWidget(self.logo_label, 5, 0)  # Logo in bottom-left
        self.layout.addWidget(self.connection_label, 5, 1)  # Connection status in bottom-center

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
                # Get RS232 and Serial data safely
                rs232_data = latest_data.get("RS232 Data", {"RPM": 0, "Gear": "N", "Engine Temperature": 0, "Drive Speed": 0, "Ground Speed": 0, "Throttle Position": 0})
                serial_data = latest_data.get("Serial Data", {"Wheel Speed": 0})

                # RPM from RS232
                rpm = int(rs232_data.get("RPM", 0))
                self.rpm_bar.setValue(rpm)
                self.rpm_label.setText(f"{rpm} RPM")
                if rpm > 11250:
                    self.rpm_bar.setStyleSheet(
                        "QProgressBar { background-color: #2F4F4F; } QProgressBar::chunk { background-color: red; }"
                    )
                elif rpm > 7500:
                    self.rpm_bar.setStyleSheet(
                        "QProgressBar { background-color: #2F4F4F; } QProgressBar::chunk { background-color: orange; }"
                    )
                else:
                    self.rpm_bar.setStyleSheet(
                        "QProgressBar { background-color: #2F4F4F; } QProgressBar::chunk { background-color: #006400; }"
                    )

                # Speed from Serial (Wheel Speed)
                speed = int(rs232_data.get("Ground Speed", 0))
                self.speed_label.setText(f"{speed} km/h")

                # Engine Temperature from RS232
                engine_temp = rs232_data.get("Engine Temperature", 0)
                try:
                    temp_val = float(engine_temp)
                except (ValueError, TypeError):
                    temp_val = 0
                self.engine_temp_label.setText(f"Engine Temp: {temp_val:.1f} °C")
                if temp_val > 60:
                    self.engine_temp_label.setStyleSheet("font-size: 14pt; color: #FF0000; qproperty-alignment: AlignCenter;")
                else:
                    self.engine_temp_label.setStyleSheet("font-size: 14pt; color: #FFFFFF; qproperty-alignment: AlignCenter;")

                # Gear from RS232
                gear = rs232_data.get("Gear", "N")
                self.gear_label.setText(str(gear))

                # Update Connection Status
                if TEST_MODE:
                    if client_connected:
                        self.connection_label.setText("Active")
                    else:
                        self.connection_label.setText("Disconnected")
                else:
                    if not self.ngrok_url_displayed:
                        ngrok_url = latest_data.get("Ngrok URL")
                        if ngrok_url and ngrok_url != "Disconnected":
                            self.connection_label.setText(ngrok_url)
                            self.ngrok_url_displayed = True

    def closeEvent(self, event):
        """Handle the window close event."""
        stop_event.set()  # Signal all threads to stop
        event.accept()

# Function for data acquisition
def data_acquisition_thread():
    global latest_sensor_data
    while not stop_event.is_set():
        if TEST_MODE:
            imu_data = mock_get_imu_data()
            gps_data = mock_get_gps_data()
            serial_data = mock_get_serial_data()
            rs232_data = mock_get_rs232_data()
        else:
            imu_data = sensor_reading.get_imu_data()
            gps_data = sensor_reading.get_gps_data()
            serial_data = sensor_reading.get_serial_data()
            rs232_data = sensor_reading.get_rs232_data()

        with data_lock:
            # Add a timestamp to the sensor data
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            # Update the latest sensor data
            latest_sensor_data = {
                "Timestamp": timestamp,  # Add the timestamp here
                "IMU Data": imu_data,
                "GPS Data": gps_data,
                "Serial Data": serial_data,
                "RS232 Data": rs232_data
            }
            # Add the data to the queue for UI updates
            sensor_data.put(latest_sensor_data)
        time.sleep(1)

# Function for UI
def ui_thread():
    app = QApplication([])
    window = SensorWindow()
    app.aboutToQuit.connect(stop_event.set)  # Ensure stop_event is set when the app quits
    window.show()  # Use show() instead of showFullScreen() to respect window size
    app.exec_()

# Function for networking
def networking_thread():
    global latest_sensor_data, client_connected

    def kill_orphaned_ngrok_processes():
        """Kill any orphaned ngrok processes."""
        try:
            result = subprocess.run(["pgrep", "ngrok"], capture_output=True, text=True)
            if result.stdout:
                pids = result.stdout.strip().split("\n")
                for pid in pids:
                    print(f"Killing orphaned ngrok process with PID: {pid}")
                    subprocess.run(["kill", "-9", pid])
        except Exception as e:
            print(f"Error killing orphaned ngrok processes: {e}")

    if TEST_MODE:
        # Existing functionality for TEST_MODE
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
                client_connected = True  # Set the connection status to active

                def handle_client(client_socket):
                    global client_connected
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
                        client_connected = False  # Set the connection status to inactive
                        client_socket.close()

                # Start a new thread to handle the client
                client_handler = threading.Thread(target=handle_client, args=(client_socket,), daemon=True)
                client_handler.start()
            except socket.timeout:
                continue  # Check stop_event again

        server_socket.close()

    else:
        # Ngrok networking for production mode
        kill_orphaned_ngrok_processes()  # Kill any orphaned ngrok processes

        print("Starting ngrok...")
        ngrok_process = subprocess.Popen(["ngrok", "tcp", str(PORT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Poll the ngrok API until the tunnel is available
        ngrok_url = None
        start_time = time.time()
        timeout = 30  # Timeout after 30 seconds
        while time.time() - start_time < timeout:
            try:
                ngrok_tunnel_process = subprocess.run(["curl", "-s", "http://localhost:4040/api/tunnels"], capture_output=True, text=True)
                match = re.search(r'"public_url":"tcp://(.*?)"', ngrok_tunnel_process.stdout)
                if match:
                    ngrok_url = match.group(1)
                    print(f"Connect to the server using: {ngrok_url}")
                    break
            except Exception as e:
                print(f"Error fetching ngrok URL: {e}")
            time.sleep(1)  # Retry every second

        if not ngrok_url:
            print("Failed to retrieve ngrok URL within the timeout period. Shutting down.")
            ngrok_process.terminate()
            return

        with data_lock:
            # Always put a full data structure in the queue for the UI
            if latest_sensor_data and isinstance(latest_sensor_data, dict):
                data = latest_sensor_data.copy()
            else:
                data = {
                    "Timestamp": "",
                    "IMU Data": {},
                    "GPS Data": {},
                    "Serial Data": {"RPM": 0, "Speed": 0, "Gear": "N"},
                    "RS232 Data": {"RPM": 0, "Throttle Position": 0, "Engine Temperature": 0, "Drive Speed": 0, "Ground Speed": 0, "Gear": "N"}
                }
            data["Ngrok URL"] = ngrok_url
            latest_sensor_data = data
            sensor_data.put(latest_sensor_data)
            print(f"Debug: Added Ngrok URL to sensor_data queue: {ngrok_url}")

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((HOST, PORT))
        server_socket.listen(1)

        print(f"Server listening on {HOST}:{PORT}")

        try:
            while not stop_event.is_set():
                conn, addr = server_socket.accept()
                print(f"Connected by {addr}")
                client_connected = True

                try:
                    while not stop_event.is_set():
                        # Send the latest sensor data to the client
                        with data_lock:
                            if latest_sensor_data:
                                conn.sendall(json.dumps(latest_sensor_data).encode('utf-8') + b'\n')
                        time.sleep(1)  # Send data every second
                except (ConnectionResetError, BrokenPipeError):
                    print(f"Connection with {addr} closed.")
                finally:
                    client_connected = False
                    conn.close()
        except KeyboardInterrupt:
            print("Server shutting down...")
        finally:
            server_socket.close()
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
    ui_thread_instance.join()
    networking_thread_instance.join()