import csv
import json
import os
import time
from datetime import datetime
from pylsl import resolve_stream, StreamInlet

def create_output_file(out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    filename = datetime.now().strftime("muse_athena_%Y%m%d_%H%M%S.csv")
    return os.path.join(out_dir, filename)

def save_all_muse_athena_data(duration_seconds: float = 60.0, out_dir: str = "muse_athena_data"):
    print("Resolving Muse Athena streams...")
    streams = resolve_stream()  # resolve all available LSL streams
    if not streams:
        raise RuntimeError("No LSL streams found. Make sure Muse Athena is streaming via LSL.")

    inlets = []
    for stream_info in streams:
        name = stream_info.name()
        stype = stream_info.type()
        print(f"Found stream: {name} (type={stype})")
        inlets.append((StreamInlet(stream_info), name, stype))

    output_path = create_output_file(out_dir)
    fieldnames = [
        "stream_name",
        "stream_type",
        "channel_count",
        "stream_timestamp",
        "pc_timestamp_unix",
        "pc_timestamp_iso",
        "values_json",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        if duration_seconds is None:
            print(f"Recording until keyboard interrupt to {output_path}...")
        else:
            end_time = time.time() + duration_seconds
            print(f"Recording for {duration_seconds} seconds to {output_path}...")

        try:
            while duration_seconds is None or time.time() < end_time:
                for inlet, name, stype in inlets:
                    sample, timestamp = inlet.pull_sample(timeout=0.0)
                    if sample:
                        pc_ts = time.time()
                        writer.writerow({
                            "stream_name": name,
                            "stream_type": stype,
                            "channel_count": len(sample),
                            "stream_timestamp": timestamp,
                            "pc_timestamp_unix": pc_ts,
                            "pc_timestamp_iso": datetime.fromtimestamp(pc_ts).isoformat(timespec="milliseconds"),
                            "values_json": json.dumps(sample),
                        })
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received. Stopping recording...")

    print("Recording complete.")

if __name__ == "__main__":
    save_all_muse_athena_data(duration_seconds=None, out_dir="muse_athena_data")