import socket
host = "2.tcp.eu.ngrok.io"
port = 11566
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((host, port))
print("Connected!")
s.close()