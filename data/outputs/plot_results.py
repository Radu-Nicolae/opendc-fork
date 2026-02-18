
import pandas as pd
import matplotlib.pyplot as plt
import os
import glob
import numpy as np
import matplotlib.dates as mdates

# Setup plot style
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = [20, 10] 
plt.rcParams['font.size'] = 30
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['lines.linewidth'] = 4
plt.rcParams['axes.titlesize'] = 36
plt.rcParams['axes.labelsize'] = 32
plt.rcParams['xtick.labelsize'] = 26
plt.rcParams['ytick.labelsize'] = 26
plt.rcParams['legend.fontsize'] = 28

def get_parquet_df(output_dir, filename):
    files = glob.glob(os.path.join(output_dir, '**', filename), recursive=True)
    if not files:
        print(f"No {filename} found in {output_dir}.")
        return None
    
    dfs = []
    for f in files:
        try:
            df = pd.read_parquet(f)
            dfs.append(df)
        except Exception as e:
            print(f"Error reading {f}: {e}")
            
    if not dfs:
        return None
        
    full_df = pd.concat(dfs)
    full_df = full_df.sort_values('timestamp_absolute')
    full_df['datetime'] = pd.to_datetime(full_df['timestamp_absolute'], unit='ms')
    return full_df

def process_experiment(exp_name, exp_dir):
    print(f"Processing experiment: {exp_name} from {exp_dir}")
    power_df = get_parquet_df(exp_dir, 'powerSource.parquet')
    service_df = get_parquet_df(exp_dir, 'service.parquet')
    host_df = get_parquet_df(exp_dir, 'host.parquet')

    if power_df is None or service_df is None or host_df is None:
        return None

    # Power
    power_grouped = power_df.groupby('datetime')[['power_draw']].sum().reset_index()
    power_grouped['power_kw'] = power_grouped['power_draw'] / 1000.0
    
    # Service (Tasks)
    service_grouped = service_df.groupby('datetime')[['tasks_active', 'tasks_pending']].sum().reset_index()

    # Host (CPU Usage)
    host_grouped = host_df.groupby('datetime')[['cpu_usage', 'cpu_capacity']].sum().reset_index()
    host_grouped['cpu_utilization_pct'] = (host_grouped['cpu_usage'] / host_grouped['cpu_capacity']) * 100.0
    
    return {
        'power': power_grouped,
        'service': service_grouped,
        'host': host_grouped
    }

def smooth_data(df, column, window_size=5):
    """Apply rolling mean smoothing."""
    return df[column].rolling(window=window_size, min_periods=1).mean()

def plot_2panel_dashboard(experiments, output_file):
    # 2 Panels: Top = Workload (Active/Pending), Bottom = Efficiency (CPU/Power)
    fig, (ax_workload, ax_efficiency) = plt.subplots(2, 1, sharex=True, figsize=(20, 16))
    
    # Colors
    c_fast_active = '#1f77b4' # Blue
    c_fast_pending = '#aec7e8' # Light Blue
    
    c_rnd_active = '#ff7f0e' # Orange
    c_rnd_pending = '#ffbb78' # Light Orange
    
    window = 10 

    # --- Panel 1: Workload (Active & Pending) ---
    # We want them in the same plot. They have same units (tasks), so single Y-axis is fine.
    
    for exp_name, data in experiments.items():
        df_svc = data['service']
        
        if exp_name == 'FastStorage':
            c_act = c_fast_active
            c_pend = c_fast_pending
            ls_act = '-'
            ls_pend = '--'
        else:
            c_act = c_rnd_active
            c_pend = c_rnd_pending
            ls_act = '-'
            ls_pend = '--'
            
        ax_workload.plot(df_svc['datetime'], smooth_data(df_svc, 'tasks_active', window), 
                       label=f'{exp_name} (Active)', color=c_act, linestyle=ls_act, linewidth=3)
        
        ax_workload.plot(df_svc['datetime'], smooth_data(df_svc, 'tasks_pending', window), 
                        label=f'{exp_name} (Pending)', color=c_pend, linestyle=ls_pend, linewidth=3)
    
    ax_workload.set_title('Workload: Active & Pending Tasks', fontweight='bold')
    ax_workload.set_ylabel('Number of Tasks')
    ax_workload.set_ylim(bottom=0)
    ax_workload.legend(loc='upper right', frameon=True, fancybox=True, shadow=True, ncol=2)
    ax_workload.grid(True, linestyle=':', alpha=0.6)

    # --- Panel 2: Efficiency (CPU Utilization & Power Draw) ---
    # These have different units (% vs kW), so we need Dual Y-Axis.
    
    ax_power = ax_efficiency.twinx()
    
    # Colors for Efficiency
    c_fast_cpu = '#2ca02c' # Green
    c_fast_pwr = '#98df8a' # Light Green
    
    c_rnd_cpu = '#d62728' # Red
    c_rnd_pwr = '#ff9896' # Light Red
    
    for exp_name, data in experiments.items():
        df_host = data['host']
        df_power = data['power']
        
        if exp_name == 'FastStorage':
            c_c = c_fast_cpu
            c_p = c_fast_pwr
        else:
            c_c = c_rnd_cpu
            c_p = c_rnd_pwr
            
        # Plot CPU on Left Axis
        ax_efficiency.plot(df_host['datetime'], smooth_data(df_host, 'cpu_utilization_pct', window),
                           label=f'{exp_name} (CPU)', color=c_c, linestyle='-', linewidth=3)
        
        # Plot Power on Right Axis
        ax_power.plot(df_power['datetime'], smooth_data(df_power, 'power_kw', window),
                      label=f'{exp_name} (Power)', color=c_p, linestyle='--', linewidth=3)

    ax_efficiency.set_title('Efficiency: CPU Utilization vs. Power Draw', fontweight='bold')
    
    ax_efficiency.set_ylabel('CPU Utilization [%]', fontweight='bold')
    ax_efficiency.set_ylim(0, 105)
    
    ax_power.set_ylabel('Power Draw [kW]', fontweight='bold')
    ax_power.set_ylim(0, 2.0)
    
    # Combined Legend for Efficiency Panel
    lines_1, labels_1 = ax_efficiency.get_legend_handles_labels()
    lines_2, labels_2 = ax_power.get_legend_handles_labels()
    ax_efficiency.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper left', frameon=True, fancybox=True, shadow=True, ncol=2)
    
    ax_efficiency.grid(True, linestyle=':', alpha=0.6)

    # Date Formatting
    date_fmt = mdates.DateFormatter('%Y-%m-%d')
    ax_efficiency.xaxis.set_major_formatter(date_fmt)
    ax_efficiency.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.setp(ax_efficiency.get_xticklabels(), rotation=30, ha='right')
    ax_efficiency.set_xlabel('Date', fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    print(f"2-Panel Dashboard saved to {output_file}")

if __name__ == "__main__":
    base_dir = '/Users/radu/Atlarge/opendc-fork/data/outputs'
    
    experiments_map = {
        'FastStorage': '20260218_1906_fastStorage',
        'Rnd': '20260218_1906_rnd'
    }
    
    processed_data = {}
    for name, dirname in experiments_map.items():
        exp_path = os.path.join(base_dir, dirname)
        if os.path.exists(exp_path):
            data = process_experiment(name, exp_path)
            if data:
                processed_data[name] = data
        else:
            print(f"Experiment path not found: {exp_path}")

    output_pdf = os.path.join(base_dir, 'combined_dashboard.pdf')
    plot_2panel_dashboard(processed_data, output_pdf)
