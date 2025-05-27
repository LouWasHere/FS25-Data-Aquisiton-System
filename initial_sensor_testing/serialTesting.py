import serial
import time

# Open ttyAMA2
ser = serial.Serial("/dev/ttyAMA2", 9600, timeout=1)

# Flush buffers
ser.reset_input_buffer()
ser.reset_output_buffer()

# Send test string
ser.write(b"Hello UART2\n")
time.sleep(0.1)  # Wait for loopback

# Read response
if ser.in_waiting:
    print("Received:", ser.readline().decode(errors="ignore").strip())
else:
    print("No data received — check wiring or config.")
