import sys
import serial
import RPi.GPIO as GPIO
import time
import math
import board
import adafruit_mpu6050

try:
    i2c = board.I2C()  # uses board.SCL and board.SDA
    # Add a delay to ensure the sensor is ready
    time.sleep(1)
    sensor = adafruit_mpu6050.MPU6050(i2c)
    print("MPU6050 initialized successfully.")
except Exception as e:
    print(f"Failed to initialize I2C connection: {e}")
    sensor = None

ser = serial.Serial('/dev/ttyS0', 115200)
ser.flushInput()

arduinoSerial = serial.Serial('/dev/ttyAMA2', 9600, timeout=1)
arduinoSerial.flush()

power_key = 6

def get_imu_data():
    if sensor is None:
        return {"Error": "I2C connection failed, using dummy data"}

    data = {}
    try:
        # Read acceleration data
        accel = sensor.acceleration
        if accel is not None:
            magnitude = math.sqrt(accel[0]**2 + accel[1]**2 + accel[2]**2) / 9.81
            data["Linear Acceleration"] = f"{magnitude:.2f} Gs"
            print(f"Linear Acceleration: {accel}, Magnitude: {magnitude:.2f} Gs")
        else:
            data["Linear Acceleration"] = "N/A"
            print("Linear Acceleration: N/A")

        # Read gyroscope data
        gyro = sensor.gyro
        if gyro is not None:
            data["Gyro X"] = f"{gyro[0]:.2f}"
            data["Gyro Y"] = f"{gyro[1]:.2f}"
            data["Gyro Z"] = f"{gyro[2]:.2f}"
            print(f"Gyroscope: {gyro}")
        else:
            data["Gyro X"] = "N/A"
            data["Gyro Y"] = "N/A"
            data["Gyro Z"] = "N/A"
            print("Gyroscope: N/A")

        # Read temperature data
        temperature = sensor.temperature
        if temperature is not None:
            data["Temperature"] = f"{temperature:.2f}°C"
            print(f"Temperature: {temperature:.2f}°C")
        else:
            data["Temperature"] = "N/A"
            print("Temperature: N/A")
    except Exception as e:
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
            if ",,,,,," in GPSDATA or len(GPSDATA) < 28:  # Ensure GPSDATA has the required length
                print('GPS is not ready or data is incomplete')
                return None

            try:
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
            except (IndexError, ValueError) as e:
                print(f"Error parsing GPS data: {e}")
                return None
    else:
        print('GPS is not ready')
        return None

def get_gps_data():
    print('Start GPS session...')
    send_at('AT+CGPS=1,1', 'OK', 1)
    time.sleep(2)
    gps_data = send_at('AT+CGPSINFO', '+CGPSINFO: ', 1)
    send_at('AT+CGPS=0', 'OK', 1)
    if gps_data is None:
        # Return dummy GPS data if the GPS is not ready
        print("GPS is not ready. Sending dummy data.")
        return {"Latitude": 53.8067, "Longitude": 1.5550}  # Replace with your desired dummy coordinates
    return gps_data

def get_serial_data():
    print("Reading serial data from Arduino...")
    try:
        if arduinoSerial.in_waiting > 0:
            data = arduinoSerial.readline().decode('utf-8').rstrip()
            # Assuming the data is in the format: "Name:VAL,Name2:VAL2"
            parsed_data = {}
            for item in data.split(','):
                key, value = item.split(':')
                parsed_data[key.strip()] = value.strip()
                print(f"Parsed Serial Data: {key.strip()} = {value.strip()}")
            return parsed_data
        return {"Error": "No data available"}
    except Exception as e:
        print(f"Failed to read serial data: {e}. Data: {data}")
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

rs232 = serial.Serial('/dev/ttyAMA1', 9600, timeout=1)
rs232.flush() 

def get_rs232_data():
    if rs232.in_waiting > 143:
        data = rs232.read(144)  # Full packet size

        # Confirm marker bytes at positions 140, 141, 142
        if data[140] == 0xFC and data[141] == 0xFB and data[142] == 0xFA:
            # Compute checksum to validate (optional but recommended)
            checksum = sum(data[:143]) & 0xFF
            if checksum == data[143]:
                rpm = int.from_bytes(data[0:2], byteorder='big')
                throttle_pos = int.from_bytes(data[2:4], byteorder='big') * 0.1
                engine_temp = int.from_bytes(data[8:10], byteorder='big') * 0.1
                drive_speed = int.from_bytes(data[56:58], byteorder='big') * 0.1
                ground_speed = int.from_bytes(data[58:60], byteorder='big') * 0.1
                gear = int.from_bytes(data[104:106], byteorder='big') // 10

                return {
                    'RPM': rpm,
                    'Throttle Position': throttle_pos,
                    'Engine Temperature': engine_temp,
                    'Drive Speed': drive_speed,
                    'Ground Speed': ground_speed,
                    'Gear': str(gear)  # Ensure gear is a string for display
                }
    return None