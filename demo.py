#!/usr/bin/env python3
"""
Demo script: runs through all available OnRobot grippers,
shows status and executes a grip/release cycle on each.
Usage: python3 test_all_grippers.py
"""
import time
import sys
sys.path.insert(0, '/home/maira/EPSRC-End-effectors')

def test_gripper(name, gripper, actions):
    print(f"\n{'='*50}")
    print(f"  {name}")
    print(f"{'='*50}")
    try:
        print(f"  Status: {gripper.get_status()}")
        for action_name, action in actions:
            print(f"  -> {action_name}...")
            action()
            time.sleep(2)
            print(f"  Status: {gripper.get_status()}")
        print(f"  OK: {name} working")
    except Exception as e:
        print(f"  FAILED: {name} - {e}")

# 3FG15
try:
    from gripper_driver.fg15 import FG15
    g = FG15('192.168.1.1', unit_id=66)
    test_gripper("3FG15 Three-Finger", g, [
        ("Opening", g.open_gripper),
        ("Closing", g.close_gripper),
    ])
except Exception as e:
    print(f"\nFAILED 3FG15: {e}")

# SG
try:
    from gripper_driver.SG import SG
    g = SG('192.168.1.1', unit_id=65)
    time.sleep(3)
    test_gripper("SG Soft Gripper", g, [
        ("Opening", g.open_gripper),
        ("Closing", g.close_gripper),
    ])
except Exception as e:
    print(f"\nFAILED SG: {e}")

# MG10
try:
    from gripper_driver.mg10 import MG10
    g = MG10('192.168.1.1', unit_id=65)
    test_gripper("MG10 Magnetic", g, [
        ("Gripping 50%", lambda: g.grip(50)),
        ("Releasing", g.release),
    ])
except Exception as e:
    print(f"\nFAILED MG10: {e}")

# RG6
try:
    from gripper_driver.rg2_rg6 import RG
    g = RG('rg6', '192.168.1.1', unit_id=65)
    test_gripper("RG6 Parallel-Jaw", g, [
        ("Opening", g.open_gripper),
        ("Closing", g.close_gripper),
    ])
except Exception as e:
    print(f"\nFAILED RG6: {e}")

# VGC10
try:
    from gripper_driver.VGC10 import VGC10
    g = VGC10('192.168.1.1', unit_id=65)
    test_gripper("VGC10 Vacuum", g, [
        ("Gripping 80%", lambda: g.grip(80)),
        ("Releasing", g.release),
    ])
except Exception as e:
    print(f"\nFAILED VGC10: {e}")

print("\n" + "="*50)
print("  Demo complete")
print("="*50 + "\n")
