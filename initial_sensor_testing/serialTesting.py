import serial
import time
import sys

# Configure serial port
ser = serial.Serial("/dev/ttyAMA5", 19200, timeout=0.1)

print("=== SERIAL DATA DUMP MODE ===")
print(f"Port: {ser.port}")
print(f"Baudrate: {ser.baudrate}")
print(f"Timeout: {ser.timeout}")
print("Dumping ALL data received (raw bytes, hex, and decoded)...")
print("Press Ctrl+C to stop")
print("-" * 50)

try:
    while True:
        # Check if any data is available
        if ser.in_waiting > 0:
            # Read all available bytes
            raw_data = ser.read(ser.in_waiting)
            
            if raw_data:
                timestamp = time.strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
                
                # Print raw bytes
                print(f"[{timestamp}] RAW BYTES ({len(raw_data)} bytes): {raw_data}")
                
                # Print hex representation
                hex_data = ' '.join([f'{b:02x}' for b in raw_data])
                print(f"[{timestamp}] HEX: {hex_data}")
                
                # Try to decode as text (with error handling)
                try:
                    decoded = raw_data.decode('utf-8', errors='replace')
                    print(f"[{timestamp}] TEXT: {repr(decoded)}")
                except:
                    print(f"[{timestamp}] TEXT: [Could not decode]")
                
                # Try to decode as ASCII (more permissive)
                try:
                    ascii_decoded = raw_data.decode('ascii', errors='replace')
                    if ascii_decoded != decoded:
                        print(f"[{timestamp}] ASCII: {repr(ascii_decoded)}")
                except:
                    pass
                
                print("-" * 30)
        
        # Small delay to prevent overwhelming output
        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nStopping serial dump...")
    ser.close()
    print("Serial port closed.")
    sys.exit(0)
except Exception as e:
    print(f"\nError: {e}")
    ser.close()
    sys.exit(1)
