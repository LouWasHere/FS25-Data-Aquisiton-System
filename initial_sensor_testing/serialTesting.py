import serial

ser = serial.Serial("/dev/ttyAMA2", 9600, timeout=2)

print("Waiting for input...")
while True:
    if ser.in_waiting:
        line = ser.readline().decode(errors="ignore").strip()
        print("Received:", line)
