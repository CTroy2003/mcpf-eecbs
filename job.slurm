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

# Set up logging
echo "Starting EECBS waypoint benchmark job at $(date)"
echo "Working directory: $(pwd)"

# Build EECBS first
echo "Building EECBS..."
cmake -DCMAKE_BUILD_TYPE=RELEASE .
make

if [ $? -ne 0 ]; then
    echo "ERROR: EECBS build failed!"
    exit 1
fi

echo "EECBS build completed successfully"

# Check if EECBS executable exists
if [ ! -f "./eecbs" ]; then
    echo "ERROR: EECBS executable not found after build!"
    exit 1
fi

echo "EECBS executable found: $(ls -la ./eecbs)"



# Run the batch waypoint runner with explicit arguments
echo "Starting batch waypoint runner..."
python3 batch_waypoint_runner.py \
    --maps random-32-32-20 \
    --scenarios 0wp 1wp 2wp 4wp 8wp \
    --scenario-files random-1 random-2 random-3 random-4 random-5 random-6 random-7 random-8 random-9 random-10 random-11 random-12 random-13 random-14 random-15 random-16 random-17 random-18 random-19 random-20 random-21 random-22 random-23 random-24 random-25 \
    --agents 250 \
    --timeout 60 \
    --suboptimality 1.2 \
    --output-dir batch_results

if [ $? -ne 0 ]; then
    echo "ERROR: Batch waypoint runner failed!"
    exit 1
fi

echo "Batch waypoint runner completed at $(date)"
