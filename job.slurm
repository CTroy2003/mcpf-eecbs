#!/bin/bash
## NECESSARY JOB SPECIFICATIONS
#SBATCH --job-name=eecbs_waypoint_benchmark
#SBATCH --time=10:00:00
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=48
#SBATCH --mem=10G
#SBATCH --output=eecbs_waypoint_benchmark.%j
## OPTIONAL JOB SPECIFICATIONS
##SBATCH --mail-type=ALL
##SBATCH --mail-user=<MAIL_ID>

# Load the same Python module as the other job
module load Python/3.11.5

# Build EECBS first
cmake -DCMAKE_BUILD_TYPE=RELEASE .
make

# Run the batch waypoint runner
python3 batch_waypoint_runner.py
