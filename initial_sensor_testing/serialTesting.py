import serial

ser = serial.Serial("/dev/ttyAMA5", 19200)

print("Waiting for input...")
while True:
    if ser.in_waiting:
        line = ser.readline().decode(errors="ignore").strip()
        print("Received:", line)
