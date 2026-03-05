# GWA-T-12 BitBrains
## Source:
https://atlarge-research.com/gwa-t-12/

## Grid description:
The dataset contains the performance metrics of 1,750 VMs from a distributed datacenter from Bitbrains, which is a service provider that specializes in managed hosting and business computation for enterprises. Customers include many major banks (ING), credit card operators (ICS), insurers (Aegon), etc. Bitbrains hosts applications used in the solvency domain; examples of application vendors are Towers Watson and Algorithmics. These applications are typically used for financial reporting, which is used predominately at the end of financial quarters.

Each file contains the performance metrics of a VM. These files are organized according by traces: fastStorage and Rnd.

The first trace, fastStorage, consists of 1,250 VMs that are connected to fast storage area network (SAN) storage devices. The second trace, Rnd, consists of 500 VMs that are either connected to the fast SAN devices or to much slower Network Attached Storage (NAS) devices. The fastStorage trace includes a higher fraction of application servers and compute nodes than the Rnd trace, which is due to the higher performance of the storage attached to the fastStorage machines. Conversely, for the Rnd trace we observe a higher fraction of management machines, which only require storage with lower performance and less frequent access.

In the Rnd directory, the files are organized into 3 sub-directories by the month that the metrics are recorded.

The format of each file is row-based, each row represent an observation of the performance metrics. Each column of a row is separate by “;\t” The format of each row is

Timestamp: number of milliseconds since 1970-01-01.
CPU cores: number of virtual CPU cores provisioned.
CPU capacity provisioned (CPU requested): the capacity of the CPUs in terms of MHZ, it equals to number of cores x speed per core.
CPU usage: in terms of MHZ.
CPU usage: in terms of percentage
Memory provisioned (memory requested): the capacity of the memory of the VM in terms of KB.
Memory usage: the memory that is actively used in terms of KB.
Disk read throughput: in terms of KB/s
Disk write throughput: in terms of KB/s
Network received throughput: in terms of KB/s
Network transmitted throughput: in terms of KB/s

## Fast Storage Trace:
The fastStorage trace contains the performance metrics of 1,250 VMs. Each VM is processed as an OpenDC task.

## OpenDC Tasks and Fragments documentation
source: https://atlarge-research.github.io/opendc/docs/documentation/Input/Workload
```
Workloads define what tasks in the simulation, when they were submitted, and their computational requirements. Workload are defined using two files:

Tasks: The Tasks file contains the metadata of the tasks
Fragments: The Fragments file contains the computational demand of each task over time
Both files are provided using the parquet format.

Tasks
The Tasks file provides an overview of the tasks:

Metric	Required?	Datatype	Unit	Summary
id	Yes	string		The id of the server
submission_time	Yes	int64	datetime	The submission time of the server
nature	No	string	[deferrable, non-deferrable]	Defines if a task can be delayed
deadline	No	string	datetime	The latest the scheduling of a task can be delayed to.
duration	Yes	int64	datetime	The finish time of the submission
cpu_count	Yes	int32	count	The number of CPUs required to run this task
cpu_capacity	Yes	float64	MHz	The amount of CPU required to run this task
mem_capacity	Yes	int64	MB	The amount of memory required to run this task
gpu_count	No	int32	count	The number of GPUs required to run this task
gpu_capacity	No	float64	MHz	The amount of GPU required to run this task
gpu_mem_capacity	No	int64	MB	The amount of memory required to run this task. (Currently ignored)
Fragments
The Fragments file provides information about the computational demand of each task over time:

Metric	Required?	Datatype	Unit	Summary
id	Yes	string		The id of the task
duration	Yes	int64	milli seconds	The duration since the last sample
cpu_count	Yes	int32	count	The number of cpus required
cpu_usage	Yes	float64	MHz	The amount of computational CPU power required.
gpu_count	No	int32	count	The number of gpus required
gpu_usage	No	float64	MHz	The amount of computational GPU power required.
```
