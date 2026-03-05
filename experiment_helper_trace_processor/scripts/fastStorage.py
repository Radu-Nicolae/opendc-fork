"""
GWA-T-12 BitBrains - fastStorage Trace Processor

Converts the raw fastStorage trace (1,250 VM performance metric files) into
OpenDC-compatible Tasks and Fragments parquet files.

Raw trace format (per file, one VM):
  Columns separated by ";\t", with a header row.
  Col 0: Timestamp (seconds since epoch, despite the header saying [ms])
  Col 1: CPU cores provisioned
  Col 2: CPU capacity provisioned (MHz)
  Col 3: CPU usage (MHz)
  Col 4: CPU usage (%)
  Col 5: Memory provisioned (KB)
  Col 6: Memory usage (KB)
  Col 7-10: Disk/Network throughput (not used)

OpenDC expects:
  - submission_time, deadline, duration: milliseconds
  - fragment duration: milliseconds
  - cpu_usage: MHz
  - mem_capacity: KB (OpenDC internally divides by 1000 to get MB)
"""

import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import os
from tqdm import tqdm

# ── Configuration ────────────────────────────────────────────────────────────
RAW_DIR = "../raw_traces/raw_fastStorage_2013-8"
OUT_DIR = "../processed_traces/fastStorage"
SECONDS_TO_MS = 1000  # raw timestamps are in seconds, OpenDC expects milliseconds

# ── Read all raw VM trace files ──────────────────────────────────────────────
files = sorted(os.listdir(RAW_DIR))
print(f"Reading {len(files)} VM trace files...")

vms = []
for f in tqdm(files, desc="Loading CSVs"):
    vm = pd.read_csv(
        os.path.join(RAW_DIR, f),
        sep=";",
        header=0,
        skipinitialspace=True,
    )
    vms.append(vm)

# ── Build tasks and fragments ────────────────────────────────────────────────
tasks = []
all_fragments = []

for i in tqdm(range(len(files)), desc="Processing VMs"):
    file = files[i]
    vm = vms[i]
    vm_id = int(file.replace(".csv", ""))  # extract ID from filename (e.g., "42.csv" → 42)

    timestamps = vm.iloc[:, 0].values      # seconds since epoch
    cpu_cores  = vm.iloc[:, 1].values      # number of CPU cores
    cpu_mhz    = vm.iloc[:, 2].values      # CPU capacity (MHz)
    cpu_usage  = vm.iloc[:, 3].values      # CPU usage (MHz)
    mem_kb     = vm.iloc[:, 5].values      # memory provisioned (KB)

    # Skip VMs with no CPU cores or no capacity (they can't be scheduled)
    if cpu_cores[0] == 0 or cpu_mhz[0] == 0:
        continue

    # ── Task (one per VM) ────────────────────────────────────────────────
    tasks.append({
        "id":              vm_id,
        "submission_time": int(timestamps[0])  * SECONDS_TO_MS,
        "duration":        int(timestamps[-1] - timestamps[0]) * SECONDS_TO_MS,
        "cpu_count":       int(cpu_cores[0]),
        "cpu_capacity":    float(cpu_mhz[0]),
        "mem_capacity":    int(mem_kb[0]),  # keep in KB — OpenDC divides by 1000 internally
    })

    # ── Fragments (one per observation) ──────────────────────────────────
    # duration[i] = time since previous observation, in milliseconds
    durations = np.zeros(len(timestamps), dtype=np.int64)
    durations[1:] = (timestamps[1:] - timestamps[:-1]) * SECONDS_TO_MS

    frag_df = pd.DataFrame({
        "id":        np.int32(vm_id),
        "duration":  durations,
        "cpu_count": cpu_cores.astype(np.int32),
        "cpu_usage": cpu_usage.astype(np.float64),
    })
    all_fragments.append(frag_df)

# ── Export to parquet ─────────────────────────────────────────────────────────
os.makedirs(OUT_DIR, exist_ok=True)

tasks_df = pd.DataFrame(tasks)
tasks_df["id"]              = tasks_df["id"].astype("int32")
tasks_df["submission_time"] = tasks_df["submission_time"].astype("int64")
tasks_df["duration"]        = tasks_df["duration"].astype("int64")
tasks_df["cpu_count"]       = tasks_df["cpu_count"].astype("int32")
tasks_df["cpu_capacity"]    = tasks_df["cpu_capacity"].astype("float64")
tasks_df["mem_capacity"]    = tasks_df["mem_capacity"].astype("int64")

fragments_df = pd.concat(all_fragments, ignore_index=True)

tasks_schema = pa.schema([
    pa.field("id",              pa.int32(),   nullable=False),
    pa.field("submission_time", pa.int64(),   nullable=False),
    pa.field("duration",        pa.int64(),   nullable=False),
    pa.field("cpu_count",       pa.int32(),   nullable=False),
    pa.field("cpu_capacity",    pa.float64(), nullable=False),
    pa.field("mem_capacity",    pa.int64(),   nullable=False),
])

fragments_schema = pa.schema([
    pa.field("id",        pa.int32(),   nullable=False),
    pa.field("duration",  pa.int64(),   nullable=False),
    pa.field("cpu_count", pa.int32(),   nullable=False),
    pa.field("cpu_usage", pa.float64(), nullable=False),
])

pq.write_table(pa.Table.from_pandas(tasks_df, schema=tasks_schema),
               os.path.join(OUT_DIR, "tasks.parquet"))
pq.write_table(pa.Table.from_pandas(fragments_df, schema=fragments_schema),
               os.path.join(OUT_DIR, "fragments.parquet"))

print(f"\nExported {len(tasks_df)} tasks and {len(fragments_df)} fragments to {OUT_DIR}/")
