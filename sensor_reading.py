import sys
import serial
import RPi.GPIO as GPIO
import time
import math
import board
import adafruit_bno055

i2c = board.I2C()  # uses board.SCL and board.SDA

# Add a delay to ensure the sensor is ready
time.sleep(1)

sensor = adafruit_bno055.BNO055_I2C(i2c)

ser = serial.Serial('/dev/ttyS0', 115200)
ser.flushInput()

arduinoSerial = serial.Serial('/dev/ttyAMA2', 9600, timeout=1)
arduinoSerial.flush()

power_key = 6

def get_imu_data():
    try:
        sensor.mode = adafruit_bno055.NDOF_MODE
        print("Sensor mode set to:", sensor.mode)
    except OSError as e:
        print(f"Failed to set sensor mode: {e}")
        return {"Error": f"Failed to set sensor mode: {e}"}

    time.sleep(5)

    data = {}
    try:
        linear_accel = sensor.linear_acceleration
        gyro = sensor.gyro
        euler = sensor.euler
        calibration = sensor.calibration_status

        if linear_accel is not None and all(v is not None for v in linear_accel):
            magnitude = math.sqrt(linear_accel[0]**2 + linear_accel[1]**2 + linear_accel[2]**2) / 9.81
            data["Linear Acceleration"] = f"{magnitude:.2f} Gs"
            print(f"Linear Acceleration: {linear_accel}, Magnitude: {magnitude:.2f} Gs")
        else:
            data["Linear Acceleration"] = "N/A"
            print("Linear Acceleration: N/A")

        if gyro is not None and all(v is not None for v in gyro):
            data["Gyro X"] = f"{gyro[0]:.2f}"
            data["Gyro Y"] = f"{gyro[1]:.2f}"
            data["Gyro Z"] = f"{gyro[2]:.2f}"
            print(f"Gyroscope: {gyro}")
        else:
            data["Gyro X"] = "N/A"
            data["Gyro Y"] = "N/A"
            data["Gyro Z"] = "N/A"
            print("Gyroscope: N/A")

        if euler is not None and euler[0] is not None:
            data["Compass Angle"] = f"{euler[0]:.2f}°"
            print(f"Compass Angle: {euler[0]:.2f}°")
        else:
            data["Compass Angle"] = "N/A"
            print("Compass Angle: N/A")

        data["Calibration Status"] = {
            "Sys": calibration[0],
            "Gyro": calibration[1],
            "Accel": calibration[2],
            "Mag": calibration[3]
        }
        print(f"Calibration Status - Sys: {calibration[0]}, Gyro: {calibration[1]}, Accel: {calibration[2]}, Mag: {calibration[3]}")
    except OSError as e:
        print(f"Failed to read sensor data: {e}")
        return {"Error": f"Failed to read sensor data: {e}"}

    return data

def send_at(command, back, timeout):
    rec_buff = ''
    ser.write((command + '\r\n').encode())
    time.sleep(timeout)
    if ser.inWaiting():
        time.sleep(0.01)
        rec_buff = ser.read(ser.inWaiting())
    if rec_buff != '':
        if back not in rec_buff.decode():
            print(command + ' ERROR')
            print(command + ' back:\t' + rec_buff.decode())
            return None
        else:
            GPSDATA = str(rec_buff.decode()).replace('\n', '').replace('\r', '').replace('AT', '').replace('+CGPSINFO', '').replace(': ', '')
            if ",,,,,," in GPSDATA or len(GPSDATA) < 12:
                print('GPS is not ready')
                return None

            Lat = GPSDATA[:2]
            SmallLat = GPSDATA[2:11]
            NorthOrSouth = GPSDATA[12]
            Long = GPSDATA[14:17]
            SmallLong = GPSDATA[17:26]
            EastOrWest = GPSDATA[27]

            FinalLat = float(Lat) + (float(SmallLat) / 60)
            FinalLong = float(Long) + (float(SmallLong) / 60)

            if NorthOrSouth == 'S':
                FinalLat = -FinalLat
            if EastOrWest == 'W':
                FinalLong = -FinalLong

            return {"Latitude": FinalLat, "Longitude": FinalLong}
    else:
        print('GPS is not ready')
        return None

def get_gps_data():
    print('Start GPS session...')
    send_at('AT+CGPS=1,1', 'OK', 1)
    time.sleep(2)
    gps_data = None
    while gps_data is None:
        gps_data = send_at('AT+CGPSINFO', '+CGPSINFO: ', 1)
        if gps_data is None:
            time.sleep(1.5)
    send_at('AT+CGPS=0', 'OK', 1)
    if gps_data is None:
        return {"Error": "Failed to get GPS data"}
    return gps_data

def get_serial_data():
    try:
        if arduinoSerial.in_waiting > 0:
            data = arduinoSerial.readline().decode('utf-8').rstrip()
            return {"Sensor Value": data}
        return {"Error": "No data available"}
    except Exception as e:
        print(f"Failed to read serial data: {e}")
        return {"Error": f"Failed to read serial data: {e}"}

def power_on(power_key):
    try:
        print('SIM7600X is starting:')
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(power_key, GPIO.OUT)
        time.sleep(0.1)
        GPIO.output(power_key, GPIO.HIGH)
        time.sleep(2)
        GPIO.output(power_key, GPIO.LOW)
        time.sleep(20)
        ser.flushInput()
        print('SIM7600X is ready')
    except Exception as e:
        print(f"Failed to power on SIM7600X: {e}")

def power_down(power_key):
    try:
        print('SIM7600X is logging off:')
        GPIO.output(power_key, GPIO.HIGH)
        time.sleep(3)
        GPIO.output(power_key, GPIO.LOW)
        time.sleep(18)
        print('Goodbye')
    except Exception as e:
        print(f"Failed to power down SIM7600X: {e}")