import socket
import sys

if len(sys.argv) != 3:
    print("Usage: python client.py <ngrok_address> <ngrok_port>")
    sys.exit(1)

NGROK_HOST = sys.argv[1]
NGROK_PORT = int(sys.argv[2])

print(f"Connecting to {NGROK_HOST}:{NGROK_PORT}...")

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((NGROK_HOST, NGROK_PORT))

while True:
    data = client.recv(1024)
    if not data:
        break
    print("Received:", data.decode())

