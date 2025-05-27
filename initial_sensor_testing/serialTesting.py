import serial

ser = serial.Serial('/dev/ttyAMA2', 9600)
while True:
    print(ser.readline().decode().strip())