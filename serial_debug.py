
import serial
import time

PORT = "/dev/ttyACM0"
BAUD_RATE = 115200

print("Connecting to Arduino...")

with serial.Serial(PORT, BAUD_RATE, timeout=1) as arduino:

    # Allow Arduino to reset
    time.sleep(2)

    print("Reading raw serial data for 12 seconds...\n")

    start = time.monotonic()
    lines_received = 0

    while time.monotonic() - start < 12:

        raw = arduino.readline()

        if raw:
            message = raw.decode(
                "utf-8", errors="replace"
            ).strip()

            print(f"Received: {message}")
            lines_received += 1

    print(f"\nTotal lines received: {lines_received}")

print("Debug test complete.")
