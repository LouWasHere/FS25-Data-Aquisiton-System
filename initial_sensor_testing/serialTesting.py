import serial
import time

ser = serial.Serial("/dev/ttyAMA5", 115200, timeout=1)

test_string = "Hello, loopback!\n"
ser.write(test_string.encode())
time.sleep(0.1)
response = ser.read(len(test_string))
print("Received: ",response.decode())

ser.close()
