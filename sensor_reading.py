import sys
import serial
import RPi.GPIO as GPIO
import time
import math
import board
import adafruit_mpu6050

# Initialize I2C for MPU6050 sensor
try:
    i2c = board.I2C()  # uses board.SCL and board.SDA
    # Add a delay to ensure the sensor is ready
    time.sleep(1)
    sensor = adafruit_mpu6050.MPU6050(i2c)
    print("MPU6050 initialized successfully.")
except Exception as e:
    print(f"Failed to initialize I2C connection: {e}")
    sensor = None

# Initialize serial connections (ttyS0 for SIM7600X, ttyAMA2 for Arduino, ttyAMA5 for RS232)
ser = serial.Serial('/dev/ttyS0', 115200)
ser.flushInput()

arduinoSerial = serial.Serial('/dev/ttyAMA2', 9600, timeout=1)
arduinoSerial.flush()

rs232 = serial.Serial('/dev/ttyAMA5', 19200, timeout=1)
rs232.flush() 

power_key = 6

def get_imu_data():
    # Check if the sensor is initialized
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

# Decode GPS data from SIM7600X module (code lifted from template)
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

# Get GPS data from SIM7600X module
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

# Read serial data from Arduino (analog sensor reading)
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
        print(f"Failed to read serial data: {e}.")
        return {"Error": f"Failed to read serial data: {e}"}

# Global buffer to accumulate RS232 data packets
rs232_buffer = bytearray()
rs232_synchronized = False

# Function to read and process RS232 data packets synchronously
def get_rs232_data():
    global rs232_buffer, rs232_synchronized
    
    try:
        # Always try to read new data first
        new_data_received = False
        while rs232.in_waiting > 0:
            # Read available bytes (could be partial packets)
            available_bytes = min(rs232.in_waiting, 64)  # Read up to 64 bytes at a time
            data_chunk = rs232.read(available_bytes)
            rs232_buffer.extend(data_chunk)
            new_data_received = True
            print(f"Read {len(data_chunk)} bytes, buffer size now: {len(rs232_buffer)}")
        
        # If we're not synchronized, try to find the start of a valid message
        if not rs232_synchronized:
            # Look for marker bytes pattern (0xFC, 0xFB, 0xFA) in the buffer
            for i in range(len(rs232_buffer) - 2):
                if (rs232_buffer[i] == 0xFC and 
                    rs232_buffer[i+1] == 0xFB and 
                    rs232_buffer[i+2] == 0xFA):
                    
                    # Check if this could be at position 140 of a 144-byte message
                    if i >= 140:
                        start_pos = i - 140
                        if start_pos + 144 <= len(rs232_buffer):
                            # We have enough data, check if this is a valid packet
                            test_data = rs232_buffer[start_pos:start_pos + 144]
                            checksum = sum(test_data[:143]) & 0xFF
                            if checksum == test_data[143]:
                                # Found valid message! Remove everything before it
                                rs232_buffer = rs232_buffer[start_pos:]
                                rs232_synchronized = True
                                print("RS232 synchronized successfully!")
                                break
            
            # If still not synchronized and buffer is getting large, clear old data
            if not rs232_synchronized and len(rs232_buffer) > 288:
                # Keep only the last 144 bytes to avoid losing a potential message
                rs232_buffer = rs232_buffer[-144:]
                print("RS232 clearing old unsynchronized data")
        
        # If synchronized, try to process complete messages
        while rs232_synchronized and len(rs232_buffer) >= 144:
            # Extract the first 144 bytes
            data = rs232_buffer[:144]
            
            # Confirm marker bytes at positions 140, 141, 142
            if data[140] == 0xFC and data[141] == 0xFB and data[142] == 0xFA:
                # Compute checksum to validate
                checksum = sum(data[:143]) & 0xFF
                if checksum == data[143]:
                    # Clear the processed data from buffer
                    rs232_buffer = rs232_buffer[144:]
                    print(f"Successfully processed message, buffer size now: {len(rs232_buffer)}")
                    
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
                else:
                    print("RS232 checksum validation failed, losing synchronization.")
                    rs232_synchronized = False
                    rs232_buffer = rs232_buffer[1:]  # Remove one byte and try to resync
                    break  # Exit the while loop to re-synchronize
            else:
                print("RS232 marker bytes not found, losing synchronization.")
                rs232_synchronized = False
                rs232_buffer = rs232_buffer[1:]  # Remove one byte and try to resync
                break  # Exit the while loop to re-synchronize
        
        # Clear buffer if it gets too large (prevent memory issues)
        if len(rs232_buffer) > 432:  # 3x expected packet size
            print("RS232 buffer overflow, clearing buffer and losing sync.")
            rs232_buffer.clear()
            rs232_synchronized = False
        
        # If not enough data or not synchronized, return all -1
        # But provide some debug info about the current state
        if not new_data_received and len(rs232_buffer) == 0:
            print("No new RS232 data available")
        elif not rs232_synchronized:
            print(f"RS232 not synchronized, buffer size: {len(rs232_buffer)}")
        else:
            print(f"RS232 synchronized but incomplete message, buffer size: {len(rs232_buffer)}")
            
        return {
            'RPM': -1,
            'Throttle Position': -1,
            'Engine Temperature': -1,
            'Drive Speed': -1,
            'Ground Speed': -1,
            'Gear': -1
        }
    except Exception as e:
        print(f"Failed to read RS232 data: {e}")
        # Clear buffer on error to prevent corruption
        rs232_buffer.clear()
        rs232_synchronized = False
        return {
            'RPM': -1,
            'Throttle Position': -1,
            'Engine Temperature': -1,
            'Drive Speed': -1,
            'Ground Speed': -1,
            'Gear': -1
        }

# Power on and power down functions for SIM7600X module
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

