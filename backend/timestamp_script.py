import time
import subprocess

# Get the current Unix timestamp
timestamp = time.time()

# Save it to a file
with open('first_timestamp.txt', 'w') as f:
    f.write(str(timestamp))

print(f"First Unix timestamp saved: {timestamp}")

subprocess.run(["OpenMuse", "record", "--address", "YOUR_MUSE_ADDRESS", "--outfile", "data.txt"])