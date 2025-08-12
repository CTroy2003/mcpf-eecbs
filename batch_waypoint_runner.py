#!/usr/bin/env python3
"""
Batch Waypoint EECBS Runner

This script runs waypoint EECBS on multiple maps and scenarios with configurable parameters.
It's designed to be easily extensible for adding more scenarios and maps in the future.

Usage:
    python batch_waypoint_runner.py [options]

Example:
    python batch_waypoint_runner.py --maps random-32-32-20 --scenarios 2wp,4wp,8wp --agents 250 --timeout 60
"""

import argparse
import os
import sys
import time
import json
from datetime import datetime
from typing import List, Dict, Tuple
from waypoint_eecbs import WaypointEECBSRunner


class BatchWaypointRunner:
    """Batch runner for waypoint EECBS scenarios."""
    
    def __init__(self, base_output_dir: str = "batch_results"):
        self.base_output_dir = base_output_dir
        self.results = []
        
        # Ensure output directory exists
        os.makedirs(base_output_dir, exist_ok=True)
    
    def run_scenario(self, map_name: str, scenario_name: str, scenario_file: str, num_agents: int, 
                    timeout: int, suboptimality: float = 1.2) -> Dict:
        """Run a single scenario and return results."""
        
        # Construct file paths for new structure
        map_file = f"data/maps/{map_name}.map"
        scenario_file_path = f"data/scenarios/{map_name}/{map_name}_{scenario_name}/{map_name}-{scenario_file}.scen"
        
        # Check if files exist
        if not os.path.exists(map_file):
            return {
                'success': False,
                'error': f"Map file not found: {map_file}"
            }
        
        if not os.path.exists(scenario_file_path):
            return {
                'success': False,
                'error': f"Scenario file not found: {scenario_file_path}"
            }
        
        # Create output directory for this run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"{self.base_output_dir}/{map_name}_{scenario_name}_{scenario_file}_{num_agents}agents_{timestamp}"
        
        print(f"Running: {map_name} - {scenario_name} - {scenario_file} with {num_agents} agents")
        print(f"Output: {output_dir}")
        
        # Run the scenario
        start_time = time.time()
        try:
            runner = WaypointEECBSRunner()
            result = runner.run_waypoint_scenario(
                map_file=map_file,
                scenario_file=scenario_file_path,
                scenario_index=0,  # Use first scenario
                num_agents=num_agents,
                timeout=timeout,
                suboptimality=suboptimality,
                output_dir=output_dir
            )
            
            result['map_name'] = map_name
            result['scenario_name'] = scenario_name
            result['num_agents'] = num_agents
            result['timeout'] = timeout
            result['suboptimality'] = suboptimality
            result['output_dir'] = output_dir
            result['run_time'] = time.time() - start_time
            result['timestamp'] = timestamp
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Exception during run: {str(e)}",
                'map_name': map_name,
                'scenario_name': scenario_name,
                'num_agents': num_agents,
                'timeout': timeout,
                'suboptimality': suboptimality,
                'output_dir': output_dir,
                'run_time': time.time() - start_time,
                'timestamp': timestamp
            }
    
    def run_batch(self, maps: List[str], scenarios: List[str], scenario_files: List[str], 
                  num_agents: int, timeout: int, suboptimality: float = 1.2) -> List[Dict]:
        """Run multiple scenarios in batch."""
        
        print(f"Starting batch run:")
        print(f"  Maps: {maps}")
        print(f"  Scenarios: {scenarios}")
        print(f"  Scenario Files: {scenario_files}")
        print(f"  Agents: {num_agents}")
        print(f"  Timeout: {timeout}s")
        print(f"  Suboptimality: {suboptimality}")
        print(f"  Output directory: {self.base_output_dir}")
        print("-" * 60)
        
        results = []
        
        for map_name in maps:
            for scenario_name in scenarios:
                for scenario_file in scenario_files:
                    result = self.run_scenario(
                        map_name=map_name,
                        scenario_name=scenario_name,
                        scenario_file=scenario_file,
                        num_agents=num_agents,
                        timeout=timeout,
                        suboptimality=suboptimality
                    )
                    
                    results.append(result)
                    
                    # Print result summary
                    if result['success']:
                        print(f"✅ SUCCESS: {map_name} - {scenario_name} - {scenario_file}")
                        if 'total_cost' in result:
                            print(f"   Total Cost: {result['total_cost']}")
                        if 'total_path_length' in result:
                            print(f"   Path Length: {result['total_path_length']}")
                        if 'run_time' in result:
                            print(f"   Run Time: {result['run_time']:.2f}s")
                    else:
                        print(f"❌ FAILED: {map_name} - {scenario_name} - {scenario_file}")
                        print(f"   Error: {result.get('error', 'Unknown error')}")
                    
                    print()
        
        # Save batch results
        self.save_batch_results(results)
        
        return results
    
    def save_batch_results(self, results: List[Dict]):
        """Save batch results to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"{self.base_output_dir}/batch_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Batch results saved to: {results_file}")
        
        # Print summary
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        print(f"\n{'='*60}")
        print(f"BATCH SUMMARY:")
        print(f"  Total runs: {len(results)}")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")
        print(f"  Results file: {results_file}")
        print(f"{'='*60}")


def create_waypoint_scenarios(base_scenario_file: str, map_name: str, 
                            waypoint_counts: List[int]) -> None:
    """Create waypoint scenarios from a base scenario file."""
    
    print(f"Creating waypoint scenarios for {map_name}...")
    
    # Read base scenario
    with open(base_scenario_file, 'r') as f:
        lines = f.readlines()
    
    # Create scenarios directory if it doesn't exist
    scenarios_dir = f"data/scenarios/{map_name}"
    os.makedirs(scenarios_dir, exist_ok=True)
    
    for wp_count in waypoint_counts:
        scenario_dir = f"{scenarios_dir}/{map_name}_{wp_count}wp"
        os.makedirs(scenario_dir, exist_ok=True)
        scenario_file = f"{scenario_dir}/{map_name}-random-1.scen"
        
        print(f"  Creating {wp_count}wp scenario...")
        
        with open(scenario_file, 'w') as f:
            f.write("version 1\n")
            
            for line in lines[1:]:  # Skip version line
                parts = line.strip().split('\t')
                if len(parts) < 8:
                    continue
                
                # Parse base scenario line
                bucket = parts[0]
                width = parts[2]
                height = parts[3]
                start_x = parts[4]
                start_y = parts[5]
                goal_x = parts[6]
                goal_y = parts[7]
                optimal_length = parts[8]
                
                # Generate random waypoints between start and goal
                import random
                waypoints = []
                for i in range(wp_count):
                    # Generate waypoint between start and goal
                    # Use weighted random to prefer positions between start and goal
                    start_x, start_y = int(start_x), int(start_y)
                    goal_x, goal_y = int(goal_x), int(goal_y)
                    
                    # Generate waypoint with some preference for the middle area
                    if random.random() < 0.7:  # 70% chance to be in middle area
                        wp_x = random.randint(min(start_x, goal_x), max(start_x, goal_x))
                        wp_y = random.randint(min(start_y, goal_y), max(start_y, goal_y))
                    else:  # 30% chance to be anywhere
                        wp_x = random.randint(0, int(width)-1)
                        wp_y = random.randint(0, int(height)-1)
                    
                    waypoints.extend([str(wp_x), str(wp_y)])
                
                # Write waypoint scenario line
                waypoint_line = f"{bucket}\t{map_name}.map\t{width}\t{height}\t{start_x}\t{start_y}\t{goal_x}\t{goal_y}\t{optimal_length}\t{wp_count}\t{' '.join(waypoints)}\n"
                f.write(waypoint_line)
        
        print(f"    Created: {scenario_file}")


def main():
    parser = argparse.ArgumentParser(description="Batch Waypoint EECBS Runner")
    parser.add_argument("--maps", nargs="+", default=["random-32-32-20", "random-64-64-20", "warehouse-20-40-10-2-1", "brc202d"],
                       help="List of map names to run")
    parser.add_argument("--scenarios", nargs="+", default=["0wp", "1wp", "2wp", "4wp", "8wp"],
                       help="List of scenario names to run")
    parser.add_argument("--agents", type=int, default=250,
                       help="Number of agents to use")
    parser.add_argument("--timeout", type=int, default=60,
                       help="Timeout in seconds")
    parser.add_argument("--suboptimality", type=float, default=1.2,
                       help="Suboptimality factor")
    parser.add_argument("--output-dir", default="batch_results",
                       help="Base output directory")
    parser.add_argument("--create-scenarios", action="store_true",
                       help="Create waypoint scenarios from base scenarios")
    parser.add_argument("--base-scenario", default="random-32-32-20-random-1.scen",
                       help="Base scenario file for creating waypoint scenarios")
    parser.add_argument("--scenario-files", nargs="+", default=["random-1"],
                       help="List of scenario file numbers to run (e.g., random-1, random-2, etc.)")
    
    args = parser.parse_args()
    
    # Create waypoint scenarios if requested
    if args.create_scenarios:
        for map_name in args.maps:
            create_waypoint_scenarios(
                base_scenario_file=args.base_scenario,
                map_name=map_name,
                waypoint_counts=[2, 4, 8]
            )
        print("Waypoint scenarios created successfully!")
        return
    
    # Run batch
    runner = BatchWaypointRunner(base_output_dir=args.output_dir)
    results = runner.run_batch(
        maps=args.maps,
        scenarios=args.scenarios,
        scenario_files=args.scenario_files,
        num_agents=args.agents,
        timeout=args.timeout,
        suboptimality=args.suboptimality
    )
    
    return results


if __name__ == "__main__":
    main() 