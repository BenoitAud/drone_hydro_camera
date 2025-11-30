import depthai as dai
import time
import datetime
import os
import sys
import glob
import serial
from gpiozero import Button
from signal import pause

# --- Configuration ---
# Hardware Settings
BUTTON_PIN = 9          # GPIO Pin for the button
GPS_BAUD = 9600
FPS = 2                 # 2 Frames Per Second (2 Hz)

# Storage Settings
# Tries to save to SSD first, falls back to local user folder if SSD missing
PRIMARY_ROOT = "/mnt/ssd/camera_logs"
FALLBACK_ROOT = os.path.expanduser("~/camera_logs_backup")

# --- Helper Functions ---

def get_storage_path():
    """
    Determines storage path by actually TRYING to write a file.
    This is the only way to detect a 'Ghost' or 'Unplugged' drive on Linux.
    """
    try:
        # 1. Try to create the folder (if it doesn't exist)
        if not os.path.exists(PRIMARY_ROOT):
            os.makedirs(PRIMARY_ROOT, exist_ok=True)
            
        # 2. The Critical Test: Try to write a dummy file
        # This will trigger the [Errno 5] Input/output error immediately if the drive is bad
        test_file = os.path.join(PRIMARY_ROOT, ".write_test")
        with open(test_file, 'w') as f:
            f.write("test")
            
        # 3. If we got here, the SSD is healthy. Clean up and return.
        os.remove(test_file)
        print(f"STORAGE: SSD verified at {PRIMARY_ROOT}")
        return PRIMARY_ROOT

    except (OSError, IOError) as e:
        # 4. If ANY error happens (Permissions, Unplugged, I/O Error), switch to fallback
        print(f"WARNING: SSD failed write test ({e}).")
        print(f"STORAGE: Switching to FALLBACK at {FALLBACK_ROOT}")
        
        # Ensure fallback exists
        if not os.path.exists(FALLBACK_ROOT):
            os.makedirs(FALLBACK_ROOT, exist_ok=True)
            
        return FALLBACK_ROOT

def get_gps_port():
    """Auto-detects USB GPS."""
    ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
    if ports:
        return ports[0]
    return None

def restart_program():
    """Restarts the current script to reset all buffers and states."""
    print("Restarting program for new acquisition cycle...")
    python = sys.executable
    os.execl(python, python, *sys.argv)

def create_session_folders(base_path):
    """Creates a timestamped folder structure for the current session."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session_path = os.path.join(base_path, f"session_{timestamp}")
    
    img_path = os.path.join(session_path, "images")
    os.makedirs(img_path, exist_ok=True)
    
    return session_path, img_path

# --- Main Execution ---

def run_mission():
    # 1. Initialize Button
    print("--- SYSTEM INIT ---")
    try:
        btn = Button(BUTTON_PIN, pull_up=True, bounce_time=0.1, hold_time=1.0)
        print("Button: READY")
    except Exception as e:
        print(f"CRITICAL: Button init failed: {e}")
        sys.exit(1)

    # 2. Initialize GPS
    gps_port = get_gps_port()
    ser = None
    if gps_port:
        try:
            ser = serial.Serial(gps_port, GPS_BAUD, timeout=0.5)
            print(f"GPS: DETECTED at {gps_port}")
        except Exception as e:
            print(f"GPS: Error opening port ({e}). Proceeding without GPS.")
    else:
        print("GPS: NOT FOUND. Proceeding without GPS.")

    # 3. Initialize OAK-D Pipeline
    print("Camera: CONFIGURING...")
    pipeline = dai.Pipeline()

    # RGB Camera Setup
    camRgb = pipeline.create(dai.node.ColorCamera)
    camRgb.setBoardSocket(dai.CameraBoardSocket.CAM_A)
    camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_4_K)
    camRgb.setImageOrientation(dai.CameraImageOrientation.ROTATE_180_DEG)
    camRgb.setFps(FPS)
    
    # Critical for moving platform: Fast shutter speed
    camRgb.initialControl.setSceneMode(dai.CameraControl.SceneMode.SPORTS)

    # Encoder Setup (MJPEG for speed)
    videoEnc = pipeline.create(dai.node.VideoEncoder)
    videoEnc.setDefaultProfilePreset(FPS, dai.VideoEncoderProperties.Profile.MJPEG)
    videoEnc.setQuality(95)

    # Link nodes
    xoutJpeg = pipeline.create(dai.node.XLinkOut)
    xoutJpeg.setStreamName("jpeg")
    camRgb.video.link(videoEnc.input)
    videoEnc.bitstream.link(xoutJpeg.input)

    # --- IDLE STATE ---
    print("\n--------------------------------")
    print(" SYSTEM READY. WAITING FOR TRIGGER.")
    print(f" Press Button on GPIO {BUTTON_PIN} to start.")
    print("--------------------------------")

    btn.wait_for_press()
    print("TRIGGER RECEIVED. STARTING RECORDING...")
    
    # --- RECORDING SETUP ---
    root_path = get_storage_path()
    session_dir, img_dir = create_session_folders(root_path)
    
    # Create GPS Log file
    gps_file = None
    if ser:
        gps_log_path = os.path.join(session_dir, "gps_log.txt")
        gps_file = open(gps_log_path, "a")
        # Write CSV Header
        gps_file.write("SystemTime,RawNMEA\n")
        print(f"GPS Log: {gps_log_path}")

    print(f"Images: {img_dir}")

    # --- RECORDING LOOP ---
    with dai.Device(pipeline) as device:
        qJpeg = device.getOutputQueue(name="jpeg", maxSize=4, blocking=True)
        
        recording = True
        frame_count = 0
        
        try:
            while recording:
                # A. Check Button for Stop (Requires Hold)
                if btn.is_pressed:
                    pass 

                # B. Get Frame (This blocks and governs the 2Hz timing)
                if qJpeg.has():
                    inJpeg = qJpeg.get()
                    jpegData = inJpeg.getData()
                    
                    # Timestamp for filename
                    now = datetime.datetime.now()
                    ts_str = now.strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3] # ms precision
                    
                    # Save Image
                    filename = f"{img_dir}/img_{ts_str}.jpg"
                    with open(filename, "wb") as f:
                        f.write(jpegData)
                    
                    # C. Read GPS (Non-blocking attempt)
                    if ser and ser.is_open:
                        try:
                            # Read all lines in buffer to get latest
                            while ser.in_waiting > 0:
                                line = ser.readline().decode('utf-8', errors='replace').strip()
                                if line.startswith("$"): # Valid NMEA
                                    gps_file.write(f"{ts_str},{line}\n")
                        except Exception as e:
                            print(f"GPS Read Error: {e}")

                    if frame_count % 2 == 0: # Print status every second (approx)
                        print(f"Recording... {ts_str} | GPS: {'YES' if ser else 'NO'}")
                    
                    frame_count += 1

                if btn.value == 1:
                   if btn.is_pressed:
                       print("\nButton Pressed - STOPPING.")
                       recording = False
                       time.sleep(1)

        except KeyboardInterrupt:
            print("\nStopped by User (Keyboard).")

        finally:
            # --- CLEANUP ---
            if gps_file:
                gps_file.close()
            if ser:
                ser.close()
            print("Session Saved.")
            time.sleep(2)
            
            # Restart script to wait for next trigger
            restart_program()

if __name__ == "__main__":
    run_mission()