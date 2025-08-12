#!/bin/bash
## NECESSARY JOB SPECIFICATIONS
#SBATCH --job-name=waypoint_eecbs_debug
#SBATCH --time=2:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --mem=4G
#SBATCH --output=waypoint_eecbs_debug.%j
## OPTIONAL JOB SPECIFICATIONS
##SBATCH --mail-type=ALL
##SBATCH --mail-user=<MAIL_ID>

# Load the same Python module as the other job
module load Python/3.11.5

# First run the debug script
echo "Running debug tests..."
python3 debug_hprc.py

# Then run a small test with debug logging
echo "Running small debug batch..."
python3 batch_waypoint_runner_debug.py \
    --maps random-32-32-20 \
    --scenarios 0wp 1wp \
    --scenario-files random-1 random-2 \
    --agents 10 \
    --timeout 30 \
    --suboptimality 5.0 \
    --output-dir debug_results
