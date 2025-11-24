import gpiozero
from signal import pause
import sys

BUTTON_PIN = 9  # GPIO 9

try:
    # pull_up=True: Enables internal resistor (Pin reads 1 normally)
    # bounce_time=0.1: Ignores signal noise for 100ms
    button = gpiozero.Button(BUTTON_PIN, pull_up=True, bounce_time=0.1)

except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    sys.exit(1)

def on_press():
    print("PRESSED")

def on_release():
    print("RELEASED")

# Assign logic
button.when_pressed = on_press
button.when_released = on_release

print("Ready. Waiting for press...")

# Keep script running
pause()