
import csv
import time
import serial
from pathlib import Path
from datetime import datetime

# Serial connection
PORT = "/dev/ttyACM0"
BAUD_RATE = 115200

# Expected Arduino CSV columns
HEADERS = [
    "ms",
    "accel_roll_deg",
    "kalman_roll_deg",
    "accel_pitch_deg",
    "kalman_pitch_deg",
    "tof_raw_mm",
    "tof_filtered_mm",
    "tof_valid"
]

# Create a folder for experimental data
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

# Unique file for each recording session
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = data_dir / f"sensor_log_{timestamp}.csv"

print("Connecting to Arduino...")

try:
    with serial.Serial(PORT, BAUD_RATE, timeout=2) as arduino:
        # Uno may restart when serial is opened
        time.sleep(2)

        print("Connected!")
        print(f"Recording data to: {filename}")
        print("Press Ctrl+C to stop recording.\n")

        with open(filename, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(HEADERS)

            sample_count = 0

            while True:
                raw = arduino.readline().decode(
                    "utf-8", errors="replace"
                ).strip()

                # Ignore blank, diagnostic and header lines
                if not raw or raw.startswith("#"):
                    continue

                if raw.startswith("ms,"):
                    continue

                values = raw.split(",")

                if len(values) != len(HEADERS):
                    continue

                # Validate numeric measurements
                try:
                    int(values[0])
                    for value in values[1:7]:
                        float(value)
                    valid = int(values[7])
                    if valid not in (0, 1):
                        continue
                except ValueError:
                    continue

                # Save the measurement
                writer.writerow(values)
                file.flush()
                sample_count += 1

                # Display one sample per ~20 readings
                if sample_count % 20 == 0:
                    print(
                        f"Roll: {values[2]} deg | "
                        f"Pitch: {values[4]} deg | "
                        f"ToF: {values[6]} mm | "
                        f"Valid: {values[7]}"
                    )

except KeyboardInterrupt:
    print("\nRecording stopped by user.")

except serial.SerialException as error:
    print(f"Serial connection error: {error}")

print(f"Data file: {filename}")
