import threading
import time
import json
import math
import socket
import subprocess
import re
from queue import Queue
from PyQt5.QtWidgets import QApplication
from sensor_reading import get_imu_data, get_gps_data, get_serial_data

# Configuration Flags
TEST_MODE = False
ENABLE_UI = True
ENABLE_NGROK = False

# Shared Data Structures
sensor_data = Queue()
data_lock = threading.Lock()

# Mock Functions (if TEST_MODE is enabled)
def mock_get_imu_data():
    # Simulate IMU data with oscillating values for testing
    current_time = time.time()
    return {
        "Linear Acceleration": f"{(math.sin(current_time) + 1) * 0.5:.2f} Gs",
        "Gyro X": f"{math.sin(current_time):.2f}",
        "Gyro Y": f"{math.cos(current_time):.2f}",
        "Gyro Z": f"{math.sin(current_time / 2):.2f}",
        "Compass Angle": f"{(math.sin(current_time) + 1) * 180:.2f}°",
        "Calibration Status": {"Sys": 3, "Gyro": 3, "Accel": 3, "Mag": 3}
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

# Data Acquisition Thread
def data_acquisition_thread():
    while True:
        if TEST_MODE:
            imu_data = mock_get_imu_data()
            gps_data = mock_get_gps_data()
            serial_data = mock_get_serial_data()
        else:
            imu_data = get_imu_data()
            gps_data = get_gps_data()
            serial_data = get_serial_data()

        with data_lock:
            sensor_data.put({
                "IMU Data": imu_data,
                "GPS Data": gps_data,
                "Serial Data": serial_data,
                "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            })
        time.sleep(1)

# UI Thread (Optional)
def ui_thread():
    app = QApplication([])
    window = SensorWindow()
    app.aboutToQuit.connect(stop_event.set)  # Ensure stop_event is set when the app quits
    window.showFullScreen()
    app.exec_()

# Networking Thread
def networking_thread():
    global latest_sensor_data, client_connected
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", 5000))
    server_socket.listen(5)
    print("Server listening on 0.0.0.0:5000")

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
                            if not sensor_data.empty():
                                latest_data = sensor_data.get()
                                client_socket.sendall(json.dumps(latest_data).encode('utf-8') + b'\n')
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

# Ngrok Integration (Optional)
def start_ngrok():
    if ENABLE_NGROK:
        print("Starting ngrok...")
        ngrok_process = subprocess.Popen(["ngrok", "tcp", str(5000)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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

        return ngrok_process
    return None

# Main Function
if __name__ == "__main__":
    # Start ngrok if enabled
    ngrok_process = start_ngrok()

    # Start Threads
    acquisition_thread = threading.Thread(target=data_acquisition_thread, daemon=True)
    acquisition_thread.start()

    if ENABLE_UI:
        ui_thread_instance = threading.Thread(target=ui_thread, daemon=True)
        ui_thread_instance.start()

    networking_thread_instance = threading.Thread(target=networking_thread, daemon=True)
    networking_thread_instance.start()

    try:
        acquisition_thread.join()
        if ENABLE_UI:
            ui_thread_instance.join()
        networking_thread_instance.join()
    finally:
        if ngrok_process:
            ngrok_process.terminate()
            print("ngrok connection terminated.")