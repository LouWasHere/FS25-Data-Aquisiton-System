import socket
import subprocess
import re
import time
import json

import sensor_reading

HOST = "0.0.0.0"
PORT = 5000

print("Starting ngrok...")
subprocess.Popen(["ngrok", "tcp", str(PORT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

time.sleep(5)

try:
    ngrok_process = subprocess.run(["curl", "-s", "http://localhost:4040/api/tunnels"], capture_output=True, text=True)
    match = re.search(r'"public_url":"tcp://(.*?)"', ngrok_process.stdout)
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

# Initialize the SIM7600X module
sensor_reading.power_on(sensor_reading.power_key)

try:
    while True:
        data = conn.recv(1024)
        if not data:
            break
        if data.decode() == "shutdown":
            print("Shutdown command received. Shutting down server...")
            break
        
        print("Attempting to gather sensor data...")

        imu_data = sensor_reading.get_imu_data()
        
        print("Got IMU data")
        
        gps_data = sensor_reading.get_gps_data()
        
        print("Got GPS data")
        
        serial_data = sensor_reading.get_serial_data()
        
        print("Got serial data")

        data = {
            "IMU Data": imu_data,
            "GPS Data": gps_data,
            "Serial Data": serial_data
        }

        print("Attempting to send data...")

        conn.sendall(json.dumps(data).encode())
        time.sleep(1)
except KeyboardInterrupt:
    print("Server shutting down...")
finally:
    # Clean up and power down the SIM7600X module
    sensor_reading.power_down(sensor_reading.power_key)
    conn.close()
    server.close()