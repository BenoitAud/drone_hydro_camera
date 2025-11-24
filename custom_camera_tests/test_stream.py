import depthai as dai
import cv2
import time

# Create pipeline
pipeline = dai.Pipeline()

# --- 1. Setup RGB Camera (Low Power Mode) ---
camRgb = pipeline.create(dai.node.ColorCamera)
camRgb.setBoardSocket(dai.CameraBoardSocket.CAM_A)

# Set the sensor resolution
camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)

# --- FIX ORIENTATION HERE ---
# ROTATE_180_DEG fixes an upside-down camera (flips both Vertical and Horizontal)
camRgb.setImageOrientation(dai.CameraImageOrientation.ROTATE_180_DEG)

# Downscale ON DEVICE to save bandwidth (1920x1080 -> ~320x180)
camRgb.setIspScale(1, 4)

# Limit FPS to save power
camRgb.setFps(10)

camRgb.setInterleaved(False)
camRgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)

# --- 2. Setup Output ---
xoutRgb = pipeline.create(dai.node.XLinkOut)
xoutRgb.setStreamName("rgb")
camRgb.isp.link(xoutRgb.input)

# --- 3. Main Loop ---
print("Connecting (Inverted Mode)...")

with dai.Device(pipeline, maxUsbSpeed=dai.UsbSpeed.HIGH) as device:
    print("Connected.")
    print("Image Rotated 180 degrees.")
    print("Opening X11 Window... (Press 'q' to quit)")
    
    qRgb = device.getOutputQueue(name="rgb", maxSize=2, blocking=False)

    while True:
        inRgb = qRgb.tryGet()

        if inRgb is not None:
            # Get the frame
            frame = inRgb.getCvFrame()
            
            # Display it
            cv2.imshow("Inverted Stream", frame)

        if cv2.waitKey(1) == ord('q'):
            break

    cv2.destroyAllWindows()