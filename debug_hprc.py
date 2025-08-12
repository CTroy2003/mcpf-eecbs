#!/usr/bin/env python3
"""
Debug script for HPRC issues
"""

import os
import sys
import subprocess
import time
from waypoint_eecbs import WaypointEECBSRunner

def test_eecbs_executable():
    """Test if EECBS executable works."""
    print("Testing EECBS executable...")
    
    if not os.path.exists("./eecbs"):
        print("❌ EECBS executable not found!")
        return False
    
    try:
        # Test basic EECBS functionality
        result = subprocess.run(["./eecbs", "--help"], 
                              capture_output=True, text=True, timeout=10)
        print("✅ EECBS executable responds to --help")
        return True
    except subprocess.TimeoutExpired:
        print("❌ EECBS executable timed out")
        return False
    except Exception as e:
        print(f"❌ EECBS executable error: {e}")
        return False

def test_small_scenario():
    """Test with a very small scenario."""
    print("\nTesting small scenario...")
    
    try:
        runner = WaypointEECBSRunner()
        result = runner.run_waypoint_scenario(
            map_file="data/maps/random-32-32-20.map",
            scenario_file="data/scenarios/random-32-32-20/random-32-32-20_0wp/random-32-32-20-random-1.scen",
            scenario_index=0,
            num_agents=5,  # Very small number
            timeout=30,
            suboptimality=5.0,
            output_dir="debug_test"
        )
        
        if result['success']:
            print("✅ Small scenario test passed")
            return True
        else:
            print(f"❌ Small scenario test failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Small scenario test exception: {e}")
        return False

def test_file_access():
    """Test file access and permissions."""
    print("\nTesting file access...")
    
    # Test map file
    map_file = "data/maps/random-32-32-20.map"
    if os.path.exists(map_file):
        print(f"✅ Map file exists: {map_file}")
    else:
        print(f"❌ Map file missing: {map_file}")
        return False
    
    # Test scenario file
    scenario_file = "data/scenarios/random-32-32-20/random-32-32-20_0wp/random-32-32-20-random-1.scen"
    if os.path.exists(scenario_file):
        print(f"✅ Scenario file exists: {scenario_file}")
    else:
        print(f"❌ Scenario file missing: {scenario_file}")
        return False
    
    # Test output directory creation
    try:
        os.makedirs("debug_output", exist_ok=True)
        with open("debug_output/test.txt", "w") as f:
            f.write("test")
        print("✅ Output directory writable")
        return True
    except Exception as e:
        print(f"❌ Output directory error: {e}")
        return False

def test_python_imports():
    """Test Python imports."""
    print("\nTesting Python imports...")
    
    try:
        import tempfile
        import json
        import argparse
        from datetime import datetime
        print("✅ All required imports available")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def main():
    print("HPRC Debug Script")
    print("=" * 50)
    
    tests = [
        ("Python Imports", test_python_imports),
        ("File Access", test_file_access),
        ("EECBS Executable", test_eecbs_executable),
        ("Small Scenario", test_small_scenario),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n✅ All tests passed! The issue might be with the batch size or specific scenarios.")
    else:
        print("\n❌ Some tests failed. Check the issues above.")

if __name__ == "__main__":
    main()
