
import platform
import time

print("Granular Jamming Hexapod Robot")
print("-----------------------------")
print(f"Computer: {platform.node()}")
print(f"Python: {platform.python_version()}")

for i in range(5):
    print(f"System running... {i + 1}/5")
    time.sleep(1)

print("Raspberry Pi setup successful!")
