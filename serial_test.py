
import serial
import time

# Serial communication settings
PORT = "/dev/ttyACM0"
BAUD_RATE = 115200

def main():
    print("Connecting to Arduino...")

    with serial.Serial(PORT, BAUD_RATE, timeout=2) as arduino:

        # Give Arduino time to reset after connection
        time.sleep(2)

        commands = ["PING", "STATUS", "PING"]

        for command in commands:

            # Send command
            print(f"Raspberry Pi -> Arduino: {command}")
            arduino.write((command + "\n").encode("utf-8"))
            arduino.flush()

            # Read Arduino response
            response = arduino.readline().decode(
                "utf-8", errors="replace"
            ).strip()

            if response:
                print(f"Arduino -> Raspberry Pi: {response}")
            else:
                print("No response from Arduino!")

            time.sleep(1)

    print("Serial communication test complete!")

if __name__ == "__main__":
    main()
