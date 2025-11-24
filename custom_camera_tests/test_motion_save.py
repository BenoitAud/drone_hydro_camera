import depthai as dai
import time
import datetime
import os
import sys

# --- Configuration ---
OUTPUT_FOLDER = "pictures_out"
FPS = 1  # 1 Photo per second

# Create the output folder if it doesn't exist
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)
    print(f"Created folder: {OUTPUT_FOLDER}")

pipeline = dai.Pipeline()

# --- 1. Setup RGB Camera ---
camRgb = pipeline.create(dai.node.ColorCamera)
camRgb.setBoardSocket(dai.CameraBoardSocket.CAM_A)

# Use 4K. It is sharper than 1080p but has less "Jello effect" than 12MP
camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_4_K)

# Fix Orientation (Upside Down)
camRgb.setImageOrientation(dai.CameraImageOrientation.ROTATE_180_DEG)

# --- CRITICAL: Anti-Blur Settings ---
# Set Scene Mode to SPORTS. 
# This forces the Auto-Exposure algorithm to use the fastest shutter speed possible.
camRgb.initialControl.setSceneMode(dai.CameraControl.SceneMode.SPORTS)

# Set FPS to 1. The sensor will only capture 1 frame per second, saving huge power.
camRgb.setFps(FPS)

# --- 2. Setup JPEG Encoder ---
# We compress on the OAK-D to save the Raspberry Pi from doing work
videoEnc = pipeline.create(dai.node.VideoEncoder)
videoEnc.setDefaultProfilePreset(FPS, dai.VideoEncoderProperties.Profile.MJPEG)
# Quality 95 = Very high quality, low compression artifacts
videoEnc.setQuality(95)

# --- 3. Setup Output ---
xoutJpeg = pipeline.create(dai.node.XLinkOut)
xoutJpeg.setStreamName("jpeg")

# Link: Camera Video -> Encoder -> XLinkOut
camRgb.video.link(videoEnc.input)
videoEnc.bitstream.link(xoutJpeg.input)

# --- Main Loop ---
print(f"Starting 1 FPS Timelapse (4K Resolution). Saving to '{OUTPUT_FOLDER}/'...")
print("Press Ctrl+C to stop.")

# High speed USB is fine here because data is low (JPEG compressed)
with dai.Device(pipeline, maxUsbSpeed=dai.UsbSpeed.HIGH) as device:
    
    qJpeg = device.getOutputQueue(name="jpeg", maxSize=4, blocking=True)
    
    try:
        while True:
            # Wait for the next JPEG packet
            inJpeg = qJpeg.get()
            
            # Retrieve the actual JPEG byte data
            jpegData = inJpeg.getData()
            
            # Create filename with Timestamp
            # Format: YYYY-MM-DD_HH-MM-SS.jpg
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{OUTPUT_FOLDER}/img_{timestamp}.jpg"
            
            # Save to disk
            with open(filename, "wb") as f:
                f.write(jpegData)
            
            print(f"Saved: {filename} ({len(jpegData)/1024:.1f} KB)")

    except KeyboardInterrupt:
        print("\nStopped by user.")