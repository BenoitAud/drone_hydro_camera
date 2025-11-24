import serial
import time
import sys
import glob

# --- Auto-Detection Helper ---
def get_gps_port():
    # USB GPS devices usually show up as ttyACM* or ttyUSB*
    ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
    if len(ports) == 0:
        print("Error: No USB Serial devices found!")
        print("Check connection or run 'dmesg' to see if it was detected.")
        sys.exit(1)
    return ports[0] # Pick the first one found

# Configuration
SERIAL_PORT = get_gps_port() # Or set manually: "/dev/ttyACM0"
BAUD_RATE = 9600 # Most USB dongles use 9600 (sometimes 4800)

print(f"--- USB GPS Test (Port: {SERIAL_PORT}) ---")

try:
    # Open Serial connection
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print("Port opened. Reading data...")
    print("-----------------------------------")

    while True:
        try:
            # Read line
            line = ser.readline().decode('utf-8', errors='replace').strip()
            
            if line:
                print(f"Raw: {line}")
                
                # Simple Lock Check
                if "$GNGGA" in line or "$GPGGA" in line:
                    parts = line.split(',')
                    # Check if Latitude (index 2) is not empty
                    if len(parts) > 2 and parts[2]:
                        print(f"   >>> LOCK ACQUIRED! Lat: {parts[2]} Lon: {parts[4]}")
                    else:
                        print("   (Searching for satellites...)")
                        
        except UnicodeDecodeError:
            pass # Ignore binary garbage

except PermissionError:
    print(f"\nPERMISSION ERROR: Cannot access {SERIAL_PORT}")
    print("Try running: sudo chmod 666 {SERIAL_PORT}")
    print("Or run this script with sudo.")

except KeyboardInterrupt:
    print("\nExiting.")