import serial

ser = serial.Serial("/dev/ttyAMA2", 9600, timeout=1)
while True:
    line = ser.readline().decode(errors="ignore").strip()
    if line:
        print("Received:", line)
