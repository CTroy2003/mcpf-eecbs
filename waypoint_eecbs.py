#!/usr/bin/env python3
"""
Waypoint EECBS Runner

This script runs EECBS for multiple waypoints, parsing scenario files with waypoints
and stitching together the paths from start to waypoint1 to waypoint2 to ... to goal.

Usage:
    python waypoint_eecbs.py <map_file> <scenario_file> [options]

Example:
    python waypoint_eecbs.py data/maps/empty-8-8.map data/scenarios/empty-8-8/empty-8-8-2wp.scen -k 1 -t 60
"""

import argparse
import os
import subprocess
import tempfile
import re
from typing import List, Tuple, Dict, Optional
import csv
import json


class WaypointScenarioParser:
    """Parser for scenario files with waypoints."""
    
    def __init__(self, scenario_file: str):
        self.scenario_file = scenario_file
        self.scenarios = self._parse_scenarios()
    
    def _parse_scenarios(self) -> List[Dict]:
        """Parse the scenario file and extract waypoint information."""
        scenarios = []
        
        with open(self.scenario_file, 'r') as f:
            lines = f.readlines()
        
        # Skip version line
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
                
            parts = line.split('\t')
            if len(parts) < 10:
                continue
            
            # Parse scenario line
            # Format: bucket map width height start_x start_y goal_x goal_y optimal_length num_waypoints waypoint1_x waypoint1_y waypoint2_x waypoint2_y ...
            try:
                bucket = int(parts[0])
                map_name = parts[1]
                width = int(parts[2])
                height = int(parts[3])
                start_x = int(parts[4])
                start_y = int(parts[5])
                goal_x = int(parts[6])
                goal_y = int(parts[7])
                optimal_length = float(parts[8])
                num_waypoints = int(parts[9])  # This is number of waypoints, not agents
                
                # Extract waypoints (space-separated coordinates in the last field)
                waypoints = []
                if len(parts) > 10:
                    waypoint_coords = parts[10].split()  # Split by spaces
                    for i in range(0, len(waypoint_coords) - 1, 2):
                        if i + 1 < len(waypoint_coords):
                            wp_x = int(waypoint_coords[i])
                            wp_y = int(waypoint_coords[i + 1])
                            waypoints.append((wp_x, wp_y))
                
                # The goal is already given in columns 6-7, not the last waypoint
                scenarios.append({
                    'bucket': bucket,
                    'map_name': map_name,
                    'width': width,
                    'height': height,
                    'start': (start_x, start_y),
                    'goal': (goal_x, goal_y),  # Use the actual goal from columns 6-7
                    'optimal_length': optimal_length,
                    'num_waypoints': num_waypoints,
                    'waypoints': waypoints
                })
                
            except (ValueError, IndexError) as e:
                print(f"Warning: Could not parse line: {line.strip()}")
                print(f"Error: {e}")
                continue
        
        return scenarios


class WaypointEECBSRunner:
    """Runs EECBS for multiple waypoints and stitches paths together."""
    
    def __init__(self, eecbs_executable: str = "./eecbs"):
        self.eecbs_executable = eecbs_executable
        self.temp_files = []
    
    def __del__(self):
        """Clean up temporary files."""
        for temp_file in self.temp_files:
            try:
                os.remove(temp_file)
            except:
                pass
    
    def _create_temp_scenario(self, start: Tuple[int, int], goal: Tuple[int, int]) -> str:
        """Create a temporary scenario file for a single start-goal pair."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.scen', delete=False)
        temp_file.write("version 1\n")
        temp_file.write(f"0\tmap.map\t8\t8\t{start[0]}\t{start[1]}\t{goal[0]}\t{goal[1]}\t0.0\n")
        temp_file.close()
        
        self.temp_files.append(temp_file.name)
        return temp_file.name
    
    def _create_temp_scenario_multi(self, map_name: str, width: int, height: int,
                                   agent_pairs: List[Tuple[Tuple[int,int], Tuple[int,int]]]) -> str:
        """
        Create a temporary scenario file for multiple agents in a single segment.
        
        Args:
            map_name: Name of the map file
            width: Map width
            height: Map height  
            agent_pairs: List of ((start_x, start_y), (goal_x, goal_y)) for ALL agents in this segment
            
        Returns:
            Path to the temporary scenario file
        """
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.scen', delete=False)
        temp_file.write("version 1\n")
        
        for bucket, (start, goal) in enumerate(agent_pairs):
            temp_file.write(f"{bucket}\t{map_name}\t{width}\t{height}\t{start[0]}\t{start[1]}\t{goal[0]}\t{goal[1]}\t0\n")
        
        temp_file.close()
        self.temp_files.append(temp_file.name)
        return temp_file.name
    
    def _run_eecbs(self, map_file: str, scenario_file: str, num_agents: int = 1, 
                   timeout: int = 60, suboptimality: float = 1.2, 
                   output_stats: str = None, output_paths: str = None) -> Dict:
        """Run EECBS for a single start-goal pair."""
        
        cmd = [
            self.eecbs_executable,
            '-m', map_file,
            '-a', scenario_file,
            '-k', str(num_agents),
            '-t', str(timeout),
            '--suboptimality', str(suboptimality)
        ]
        
        if output_stats:
            cmd.extend(['-o', output_stats])
        if output_paths:
            cmd.extend(['--outputPaths', output_paths])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': f"EECBS failed with return code {result.returncode}",
                    'stderr': result.stderr
                }
            
            # Parse the output
            output_lines = result.stdout.strip().split('\n')
            if not output_lines:
                return {
                    'success': False,
                    'error': "No output from EECBS"
                }
            
            # Parse the result line (e.g., "WDG+R+C+T+BP with AStar : Succeed,6,2.1e-05,0,7,6,6,6,")
            result_line = output_lines[-1]
            if 'Succeed' not in result_line:
                return {
                    'success': False,
                    'error': f"EECBS did not succeed: {result_line}"
                }
            
            # Extract cost from the result
            parts = result_line.split(',')
            if len(parts) >= 5:
                cost = int(parts[4])
            else:
                cost = None
            
            return {
                'success': True,
                'cost': cost,
                'output': result_line,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': f"EECBS timed out after {timeout} seconds"
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Error running EECBS: {str(e)}"
            }
    
    def _parse_paths_file(self, paths_file: str) -> List[List[Tuple[int, int]]]:
        """Parse the paths output file from EECBS."""
        paths = []
        
        try:
            with open(paths_file, 'r') as f:
                content = f.read().strip()
                
            # Parse paths like "Agent 0: (1,0)->(2,0)->(2,1)->(2,2)->(3,2)->(3,3)->(3,4)->"
            agent_pattern = r'Agent (\d+): (.+?)(?=Agent \d+:|$)'
            coordinate_pattern = r'\((\d+),(\d+)\)'
            
            for match in re.finditer(agent_pattern, content, re.DOTALL):
                agent_id = int(match.group(1))
                path_str = match.group(2).strip()
                
                # Extract coordinates
                coordinates = []
                for coord_match in re.finditer(coordinate_pattern, path_str):
                    x = int(coord_match.group(1))
                    y = int(coord_match.group(2))
                    coordinates.append((x, y))
                
                # Ensure we have a path for this agent
                while len(paths) <= agent_id:
                    paths.append([])
                paths[agent_id] = coordinates
                
        except Exception as e:
            print(f"Warning: Could not parse paths file: {e}")
        
        return paths
    
    def run_waypoint_scenario(self, map_file: str, scenario_file: str, 
                             scenario_index: int = 0, num_agents: int = 1,
                             timeout: int = 60, suboptimality: float = 1.2,
                             output_dir: str = None) -> Dict:
        """Run EECBS for a complete waypoint scenario."""
        
        # Parse the scenario file
        parser = WaypointScenarioParser(scenario_file)
        if not parser.scenarios:
            return {
                'success': False,
                'error': "No scenarios found in file"
            }
        
        if scenario_index >= len(parser.scenarios):
            return {
                'success': False,
                'error': f"Scenario index {scenario_index} out of range (0-{len(parser.scenarios)-1})"
            }
        
        # Choose k agents starting at scenario_index
        agents = parser.scenarios[scenario_index:scenario_index + num_agents]
        if len(agents) < num_agents:
            return {
                'success': False,
                'error': f"Not enough agents: need {num_agents}, have {len(agents)}"
            }
        
        print(f"Running scenario {scenario_index} with {num_agents} agents:")
        for i, agent in enumerate(agents):
            print(f"  Agent {i}: Start at {agent['start']}, visit waypoints {agent['waypoints']}, end at {agent['goal']}")
            print(f"    Number of waypoints: {agent['num_waypoints']}")
        
        # Each agent's sequence: start -> wp1 -> ... -> wpN -> goal
        seqs = []
        for agent in agents:
            seqs.append([agent['start']] + agent['waypoints'] + [agent['goal']])
        
        num_segments = max(len(seq) - 1 for seq in seqs)
        map_name = agents[0]['map_name']
        width = agents[0]['width']
        height = agents[0]['height']
        
        # Build the complete path through waypoints
        complete_paths = [[] for _ in range(num_agents)]
        total_cost = 0
        segment_results = []
        
        for seg in range(num_segments):
            print(f"\nSegment {seg+1}:")
            
            # For this segment, gather each agent's (start, end)
            agent_pairs = []
            for seq in seqs:
                if seg < len(seq) - 1:
                    start_point = seq[seg]
                    end_point = seq[seg + 1]
                    agent_pairs.append((start_point, end_point))
                    print(f"  Agent {len(agent_pairs)-1}: {start_point} -> {end_point}")
                else:
                    # Agent already at its final goal; keep it stationary
                    final_pos = seq[-1]
                    agent_pairs.append((final_pos, final_pos))
                    print(f"  Agent {len(agent_pairs)-1}: {final_pos} -> {final_pos} (stationary)")
            
            # Create temporary scenario file for this segment with all agents
            temp_scenario = self._create_temp_scenario_multi(map_name, width, height, agent_pairs)
            
            # Create temporary output files
            temp_stats = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
            temp_paths = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            temp_stats.close()
            temp_paths.close()
            
            self.temp_files.extend([temp_stats.name, temp_paths.name])
            
            # Run EECBS for this segment with all agents
            result = self._run_eecbs(
                map_file=map_file,
                scenario_file=temp_scenario,
                num_agents=num_agents,
                timeout=timeout,
                suboptimality=suboptimality,
                output_stats=temp_stats.name,
                output_paths=temp_paths.name
            )
            
            if not result['success']:
                return {
                    'success': False,
                    'error': f"Segment {seg+1} failed: {result['error']}"
                }
            
            # Parse the paths for this segment
            segment_paths = self._parse_paths_file(temp_paths.name)
            
            # Store segment result
            segment_results.append({
                'segment': seg + 1,
                'agent_pairs': agent_pairs,
                'cost': result['cost'],
                'paths': segment_paths,
                'eecbs_output': result['output']
            })
            
            total_cost += result['cost'] if result['cost'] else 0
            print(f"  Cost: {result['cost']}")
            
            # Stitch paths; skip first coordinate of each segment to avoid duplicates
            for agent_id in range(num_agents):
                path = segment_paths[agent_id] if agent_id < len(segment_paths) else []
                if seg == 0:
                    # First segment: include all coordinates
                    complete_paths[agent_id] = path[:]
                else:
                    # Subsequent segments: append coordinates starting from index 1
                    if len(path) > 1:
                        complete_paths[agent_id].extend(path[1:])
                    else:
                        complete_paths[agent_id].append(path[0])
        
        # Create final output
        final_result = {
            'success': True,
            'agents': agents,
            'total_cost': total_cost,
            'segment_results': segment_results,
            'complete_paths': complete_paths,
            'num_segments': num_segments,
            'num_agents': num_agents
        }
        
        # Save results if output directory is specified
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
            # Save complete paths
            paths_file = os.path.join(output_dir, f"waypoint_paths_{scenario_index}.txt")
            with open(paths_file, 'w') as f:
                for agent_id, path in enumerate(complete_paths):
                    f.write(f"Agent {agent_id}: ")
                    f.write("->".join([f"({x},{y})" for x, y in path]))
                    f.write("\n")
            
            # Save detailed results as JSON
            json_file = os.path.join(output_dir, f"waypoint_results_{scenario_index}.json")
            with open(json_file, 'w') as f:
                # Convert tuples to lists for JSON serialization
                json_result = json.loads(json.dumps(final_result, default=lambda x: list(x) if isinstance(x, tuple) else x))
                json.dump(json_result, f, indent=2)
            
            print(f"\nResults saved to:")
            print(f"  Paths: {paths_file}")
            print(f"  Details: {json_file}")
        
        return final_result


def main():
    parser = argparse.ArgumentParser(description='Run EECBS for multiple waypoints')
    parser.add_argument('map_file', help='Path to the map file')
    parser.add_argument('scenario_file', help='Path to the scenario file with waypoints')
    parser.add_argument('-s', '--scenario', type=int, default=0, 
                       help='Scenario index to run (default: 0)')
    parser.add_argument('-k', '--agents', type=int, default=1,
                       help='Number of agents (default: 1)')
    parser.add_argument('-t', '--timeout', type=int, default=60,
                       help='Timeout in seconds for each segment (default: 60)')
    parser.add_argument('--suboptimality', type=float, default=1.2,
                       help='Suboptimality bound (default: 1.2)')
    parser.add_argument('-o', '--output', help='Output directory for results')
    parser.add_argument('--eecbs', default='./eecbs',
                       help='Path to EECBS executable (default: ./eecbs)')
    
    args = parser.parse_args()
    
    # Check if files exist
    if not os.path.exists(args.map_file):
        print(f"Error: Map file '{args.map_file}' not found")
        return 1
    
    if not os.path.exists(args.scenario_file):
        print(f"Error: Scenario file '{args.scenario_file}' not found")
        return 1
    
    if not os.path.exists(args.eecbs):
        print(f"Error: EECBS executable '{args.eecbs}' not found")
        print("Make sure to build EECBS first with: cmake . && make")
        return 1
    
    # Run the waypoint scenario
    runner = WaypointEECBSRunner(args.eecbs)
    
    try:
        result = runner.run_waypoint_scenario(
            map_file=args.map_file,
            scenario_file=args.scenario_file,
            scenario_index=args.scenario,
            num_agents=args.agents,
            timeout=args.timeout,
            suboptimality=args.suboptimality,
            output_dir=args.output
        )
        
        if result['success']:
            print(f"\n✅ Successfully completed waypoint scenario!")
            print(f"Total cost: {result['total_cost']}")
            print(f"Number of segments: {result['num_segments']}")
            print(f"Total path length: {len(result['complete_paths'][0]) if result['complete_paths'] else 0}")
        else:
            print(f"\n❌ Failed to complete waypoint scenario: {result['error']}")
            return 1
            
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 