import json
import string

def convert_hosts_to_topology(input_path, output_path, limit=60):
    with open(input_path, 'r') as f:
        hosts_data = json.load(f)

    clusters_map = {}
    items_to_process = list(hosts_data.items())[:limit]

    for host_id, host_info in items_to_process:
        datacenter = int(host_info['datacenter'])
        cluster_num = host_info['cluster']

        dc_letter = string.ascii_uppercase[datacenter - 1]
        cluster_name = f"{dc_letter}{cluster_num}"

        if cluster_name not in clusters_map:
            clusters_map[cluster_name] = []

        cores = int(host_info['cores'])
        speed_mhz = int(float(host_info['speed']) * 1000)
        memory_bytes = int(float(host_info['memory']) * 1024 * 1024 * 1024)

        host_entry = {
            "name": f"H{host_id}",
            "cpu": {"coreCount": cores, "coreSpeed": speed_mhz},
            "memory": {"memorySize": memory_bytes},
            "cpuPowerModel": {"modelType": "linear", "power": 400.0, "idlePower": 100.0, "maxPower": 200.0},
            "count": 1
        }
        clusters_map[cluster_name].append(host_entry)

    topology = {"clusters": []}
    for c_name, hosts_list in clusters_map.items():
        topology["clusters"].append({"name": c_name, "hosts": hosts_list})

    with open(output_path, 'w') as f:
        json.dump(topology, f, indent=4)

    print(f"Total hosts in input file: {len(hosts_data)}")
    print(f"Total clusters/hosts generated in topology: {len(topology['clusters'])}")
    print(f"Topology saved to {output_path}")

if __name__ == "__main__":
    INPUT_FILE = "hosts.json"
    OUTPUT_FILE = "converted_topology.json"
    convert_hosts_to_topology(INPUT_FILE, OUTPUT_FILE, limit=91)
