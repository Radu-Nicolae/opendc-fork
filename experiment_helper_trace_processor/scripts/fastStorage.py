"""
GWA-T-12 BitBrains - fastStorage Trace Processor

Converts the raw fastStorage trace (1,250 VM performance metric files) into
OpenDC-compatible Tasks and Fragments parquet files.

Raw trace format (per file, one VM):
  Columns separated by ";\t", with a header row.
  Col 0: Timestamp (ms since epoch)
  Col 1: CPU cores provisioned
  Col 2: CPU capacity provisioned (MHz)
  Col 3: CPU usage (MHz)
  Col 4: CPU usage (%)
  Col 5: Memory provisioned (KB)
  Col 6: Memory usage (KB)
  Col 7: Disk read throughput (KB/s)
  Col 8: Disk write throughput (KB/s)
  Col 9: Network received throughput (KB/s)
  Col 10: Network transmitted throughput (KB/s)
"""

import pandas as pd
import numpy as np
import os
from tqdm import tqdm

# --- Read all VM trace files ---
folder_location = "../raw_traces/raw_fastStorage_2013-8"
files = os.listdir(folder_location)

print(f"Reading {len(files)} VM trace files...")
vms = [
    pd.read_csv(
        folder_location + "/" + file,
        sep=";",
        header=0,  # all files have a header row
        skipinitialspace=True,  # strip leading whitespace after separator
    )
    for file in tqdm(files, desc="Loading CSVs")
]  # each file is a VM, and each of these VMs will be outputted as an OpenDC task -> 1250 tasks

# --- Convert each VM dataframe to an OpenDC task + fragments ---
tasks = []
all_fragments = []

# Generate sequential IDs starting from 1 (OpenDC requires int32 IDs)
for idx, vm in enumerate(tqdm(vms, desc="Processing VMs")):
    ts = vm.iloc[:, 0].values  # timestamp column as numpy array (fast)
    vm_id = idx + 1

    task = {}
    task["id"] = vm_id
    task["submission_time"] = ts[0]  # use the timestamp of the first observation as the submission time of the task
    task["nature"] = "deferrable"  # we can delay the scheduling of the task, as we do not have information about
    task["deadline"] = ts[-1]  # use the timestamp of the last observation as the deadline of the task
    task["duration"] = ts[-1] - ts[0]  # use the difference between the timestamp of the last observation and the timestamp of the first observation as the duration of the task
    task["cpu_count"] = vm.iloc[0, 1]  # use the number of CPU cores provisioned in the first observation as the number of CPU cores required to run the task
    task["cpu_capacity"] = vm.iloc[0, 2]  # use the CPU capacity provisioned in the first observation as the amount of CPU required to run the task
    task["mem_capacity"] = vm.iloc[0, 5] / 1024  # use the memory provisioned in the first observation as the amount of memory required to run the task, convert from KB to MB
    tasks.append(task)

    # Build fragments using vectorized operations instead of row-by-row loop
    durations = np.diff(ts, prepend=ts[0])  # difference between consecutive timestamps, first element is 0
    durations[0] = 0  # for the first observation, set duration to 0

    frag_df = pd.DataFrame({
        "id": vm_id,
        "duration": durations,  # use the difference between the timestamp of the current observation and the timestamp of the previous observation as the duration of the fragment
        "cpu_count": vm.iloc[:, 1].values,  # use the number of CPU cores provisioned in the current observation as the number of CPU cores required to run the fragment
        "cpu_usage": vm.iloc[:, 3].values,  # use the CPU usage in terms of percentage in the current observation as the amount of computational CPU power required to run the fragment
    })
    all_fragments.append(frag_df)

# --- Export to OpenDC parquet format ---
output_dir = "../processed_traces/fastStorage"
os.makedirs(output_dir, exist_ok=True)

import pyarrow as pa
import pyarrow.parquet as pq

# Define exact schemas for Tasks and Fragments per OpenDC requirements (with nullable=False)
tasks_schema = pa.schema([
    pa.field("id", pa.int32(), nullable=False),
    pa.field("submission_time", pa.int64(), nullable=False),
    pa.field("nature", pa.string(), nullable=True),
    pa.field("deadline", pa.int64(), nullable=True),
    pa.field("duration", pa.int64(), nullable=False),
    pa.field("cpu_count", pa.int32(), nullable=False),
    pa.field("cpu_capacity", pa.float64(), nullable=False),
    pa.field("mem_capacity", pa.int64(), nullable=False),
])

fragments_schema = pa.schema([
    pa.field("id", pa.int32(), nullable=False),
    pa.field("duration", pa.int64(), nullable=False),
    pa.field("cpu_count", pa.int32(), nullable=False),
    pa.field("cpu_usage", pa.float64(), nullable=False),
])

# Create Tasks DataFrame with correct dtypes per OpenDC spec
tasks_df = pd.DataFrame(tasks)
tasks_df["id"] = tasks_df["id"].astype("int32")
tasks_df["submission_time"] = tasks_df["submission_time"].astype("int64")
tasks_df["duration"] = tasks_df["duration"].astype("int64")
tasks_df["cpu_count"] = tasks_df["cpu_count"].astype("int32")
tasks_df["cpu_capacity"] = tasks_df["cpu_capacity"].astype("float64")
tasks_df["mem_capacity"] = tasks_df["mem_capacity"].astype("int64")

# Create Fragments DataFrame with correct dtypes per OpenDC spec
fragments_df = pd.concat(all_fragments, ignore_index=True)
fragments_df["id"] = fragments_df["id"].astype("int32")
fragments_df["duration"] = fragments_df["duration"].astype("int64")
fragments_df["cpu_count"] = fragments_df["cpu_count"].astype("int32")
fragments_df["cpu_usage"] = fragments_df["cpu_usage"].astype("float64")

# Convert DataFrames to pyarrow Tables matching the strict schemas
tasks_table = pa.Table.from_pandas(tasks_df, schema=tasks_schema)
fragments_table = pa.Table.from_pandas(fragments_df, schema=fragments_schema)

# Write parquet files
print("Writing parquet files...")
pq.write_table(tasks_table, os.path.join(output_dir, "tasks.parquet"))
pq.write_table(fragments_table, os.path.join(output_dir, "fragments.parquet"))

print(f"Exported {len(tasks_df)} tasks and {len(fragments_df)} fragments to {output_dir}/")
