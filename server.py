import socket
import subprocess
import re
import time

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

while True:
    data = "Telemetry Data\n"
    time.sleep(1)
    conn.sendall(data.encode())
