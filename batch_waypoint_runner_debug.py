#!/usr/bin/env python3
"""
Debug version of Batch Waypoint EECBS Runner with enhanced logging
"""

import argparse
import os
import sys
import time
import json
import traceback
from datetime import datetime
from typing import List, Dict, Tuple
from waypoint_eecbs import WaypointEECBSRunner


class DebugBatchWaypointRunner:
    """Debug version of batch runner with enhanced logging."""
    
    def __init__(self, base_output_dir: str = "batch_results"):
        self.base_output_dir = base_output_dir
        self.results = []
        
        # Ensure output directory exists
        os.makedirs(base_output_dir, exist_ok=True)
        
        # Create debug log file
        self.debug_log = os.path.join(base_output_dir, f"debug_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        
    def log(self, message: str):
        """Log message to both console and debug file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        with open(self.debug_log, 'a') as f:
            f.write(log_message + "\n")
    
    def run_scenario(self, map_name: str, scenario_name: str, scenario_file: str, num_agents: int, 
                    timeout: int, suboptimality: float = 5.0) -> Dict:
        """Run a single scenario and return results."""
        
        self.log(f"Starting scenario: {map_name} - {scenario_name} - {scenario_file}")
        
        # Construct file paths for new structure
        map_file = f"data/maps/{map_name}.map"
        scenario_file_path = f"data/scenarios/{map_name}/{map_name}_{scenario_name}/{map_name}-{scenario_file}.scen"
        
        # Check if files exist
        if not os.path.exists(map_file):
            self.log(f"ERROR: Map file not found: {map_file}")
            return {
                'success': False,
                'error': f"Map file not found: {map_file}"
            }
        
        if not os.path.exists(scenario_file_path):
            self.log(f"ERROR: Scenario file not found: {scenario_file_path}")
            return {
                'success': False,
                'error': f"Scenario file not found: {scenario_file_path}"
            }
        
        # Create output directory for this run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"{self.base_output_dir}/{map_name}_{scenario_name}_{scenario_file}_{num_agents}agents_{timestamp}"
        
        self.log(f"Running: {map_name} - {scenario_name} - {scenario_file} with {num_agents} agents")
        self.log(f"Output: {output_dir}")
        
        # Run the scenario
        start_time = time.time()
        try:
            self.log("Creating WaypointEECBSRunner...")
            runner = WaypointEECBSRunner()
            
            self.log("Calling run_waypoint_scenario...")
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
            
            self.log(f"Scenario completed in {result['run_time']:.2f}s")
            return result
            
        except Exception as e:
            self.log(f"EXCEPTION during run: {str(e)}")
            self.log(f"Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': f"Exception during run: {str(e)}",
                'traceback': traceback.format_exc(),
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
                  num_agents: int, timeout: int, suboptimality: float = 5.0) -> List[Dict]:
        """Run multiple scenarios in batch."""
        
        self.log(f"Starting batch run:")
        self.log(f"  Maps: {maps}")
        self.log(f"  Scenarios: {scenarios}")
        self.log(f"  Scenario Files: {scenario_files}")
        self.log(f"  Agents: {num_agents}")
        self.log(f"  Timeout: {timeout}s")
        self.log(f"  Suboptimality: {suboptimality}")
        self.log(f"  Output directory: {self.base_output_dir}")
        self.log("-" * 60)
        
        results = []
        total_experiments = len(maps) * len(scenarios) * len(scenario_files)
        current_experiment = 0
        
        for map_name in maps:
            for scenario_name in scenarios:
                for scenario_file in scenario_files:
                    current_experiment += 1
                    self.log(f"Experiment {current_experiment}/{total_experiments}")
                    
                    try:
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
                            self.log(f"✅ SUCCESS: {map_name} - {scenario_name} - {scenario_file}")
                            if 'total_cost' in result:
                                self.log(f"   Total Cost: {result['total_cost']}")
                            if 'total_path_length' in result:
                                self.log(f"   Path Length: {result['total_path_length']}")
                            if 'run_time' in result:
                                self.log(f"   Run Time: {result['run_time']:.2f}s")
                        else:
                            self.log(f"❌ FAILED: {map_name} - {scenario_name} - {scenario_file}")
                            self.log(f"   Error: {result.get('error', 'Unknown error')}")
                        
                        self.log("")  # Empty line for readability
                        
                    except Exception as e:
                        self.log(f"CRITICAL ERROR in batch loop: {str(e)}")
                        self.log(f"Traceback: {traceback.format_exc()}")
                        # Continue with next experiment instead of crashing
        
        # Save batch results
        self.save_batch_results(results)
        
        return results
    
    def save_batch_results(self, results: List[Dict]):
        """Save batch results to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"{self.base_output_dir}/batch_results_{timestamp}.json"
        
        try:
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            self.log(f"Batch results saved to: {results_file}")
            
            # Print summary
            successful = sum(1 for r in results if r['success'])
            failed = len(results) - successful
            
            self.log(f"\n{'='*60}")
            self.log(f"BATCH SUMMARY:")
            self.log(f"  Total runs: {len(results)}")
            self.log(f"  Successful: {successful}")
            self.log(f"  Failed: {failed}")
            self.log(f"  Results file: {results_file}")
            self.log(f"{'='*60}")
            
        except Exception as e:
            self.log(f"ERROR saving batch results: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="Debug Batch Waypoint EECBS Runner")
    parser.add_argument("--maps", nargs="+", default=["random-32-32-20"],
                       help="List of map names to run")
    parser.add_argument("--scenarios", nargs="+", default=["0wp"],
                       help="List of scenario names to run")
    parser.add_argument("--scenario-files", nargs="+", default=["random-1"],
                       help="List of scenario file numbers to run")
    parser.add_argument("--agents", type=int, default=10,
                       help="Number of agents to use")
    parser.add_argument("--timeout", type=int, default=60,
                       help="Timeout in seconds")
    parser.add_argument("--suboptimality", type=float, default=5.0,
                       help="Suboptimality factor")
    parser.add_argument("--output-dir", default="debug_batch_results",
                       help="Base output directory")
    
    args = parser.parse_args()
    
    # Run batch with debug logging
    runner = DebugBatchWaypointRunner(base_output_dir=args.output_dir)
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
