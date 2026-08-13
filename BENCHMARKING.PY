import time
import statistics
import sys
sys.path.insert(0, '/home/maira/EPSRC-End-effectors')

def benchmark_gripper(gripper, name, n=20):
    print(f"\n=== {name} ===")
    
    latencies = []
    motion_times = []
    
    for i in range(n):
        # Command latency
        start = time.perf_counter()
        gripper.open_gripper()
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)
        
        # Motion completion time
        start = time.perf_counter()
        while gripper.get_status()['busy']:
            time.sleep(0.05)
        motion = (time.perf_counter() - start) * 1000
        motion_times.append(motion)
        
        time.sleep(1)
        gripper.close_gripper()
        time.sleep(1)
        
        print(f"  Trial {i+1}: latency={latency:.1f}ms motion={motion:.0f}ms")
    
    print(f"\n  Latency:  mean={statistics.mean(latencies):.1f}ms  SD={statistics.stdev(latencies):.1f}ms")
    print(f"  Motion:   mean={statistics.mean(motion_times):.0f}ms  SD={statistics.stdev(motion_times):.0f}ms")

# Run for 3FG15
import gripper_driver.base as base
base.UNIT_ID = 66
from gripper_driver.fg15 import FG15
g = FG15('192.168.1.1')
benchmark_gripper(g, '3FG15')
