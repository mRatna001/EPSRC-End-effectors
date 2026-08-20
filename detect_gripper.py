#!/usr/bin/env python3
"""
detect_gripper.py
-----------------
Auto-detects which OnRobot gripper is connected to the compute box
and loads the appropriate driver automatically.

Usage:
    python3 detect_gripper.py                  # run standalone
    from detect_gripper import auto_connect    # import in scripts

How it works:
    1. Scans Modbus TCP device IDs 64-69 at 192.168.1.1:502
    2. Reads registers 256-260 from each responding device
    3. Matches register 260 against known firmware signatures
    4. Loads and returns the correct driver class

Register 260 Firmware Signatures (empirically determined):
    65000-65535  -> MG10 magnetic gripper
    80-100       -> VGC10 vacuum gripper
    1-5          -> SG soft gripper
    5-10         -> RG parallel-jaw gripper (RG2 or RG6)
    0            -> 3FG15 three-finger gripper (identified by reg257 > 0)

"""

import sys
import time
sys.path.insert(0, '/home/maira/EPSRC-End-effectors')

from pymodbus.client import ModbusTcpClient

IP   = '192.168.1.1'
PORT = 502

# ── Register 260 firmware signatures ──────────────────────────────
# Each gripper's firmware writes a unique constant to register 260.
# These were measured empirically -- see TROUBLESHOOTING.md for details.
#
# Gripper  | reg260 range  | Notes
# ---------|---------------|-------
# MG10     | 65000-65535   | Magnetic gripper, reg259 ~839
# VGC10    | 80-100        | Vacuum gripper, built-in pump
# SG       | 1-5           | Soft gripper, needs 3s init delay
# RG2/RG6  | 5-10          | Parallel jaw, distinguish by max width
# 3FG15    | 0             | Three-finger, reg257 = current diameter

def try_read(uid, address, count=1):
    """Read registers from a device ID, returning None on failure."""
    try:
        client = ModbusTcpClient(IP, port=PORT, timeout=1, retries=0)
        client.connect()
        r = client.read_holding_registers(address=address, count=count, device_id=uid)
        client.close()
        time.sleep(0.2)
        if not r.isError():
            return r.registers
    except:
        pass
    return None


def scan_device_ids():
    """
    Scan device IDs 64-69 and return list of (uid, registers) tuples
    for all devices that respond to a read of registers 256-260.
    
    The OnRobot compute box assigns device IDs based on which physical
    port the gripper is plugged into. Common values: 65, 66.
    Device ID 63 sometimes responds as a phantom -- excluded from scan.
    """
    responding = []
    for uid in range(64, 70):
        r = try_read(uid, 256, 5)
        if r:
            responding.append((uid, r))
        time.sleep(0.1)
    return responding


def fingerprint(uid, registers):
    """
    Identify the gripper type from its register 256-260 signature.

    Args:
        uid (int): Modbus device ID
        registers (list): Values of registers 256-260

    Returns:
        tuple: (gripper_type str, uid int)
    """
    if len(registers) < 5:
        return 'unknown', uid

    reg257 = registers[1]   # varies per gripper -- diameter for 3FG15, error code for MG10
    reg258 = registers[2]   # current width/vacuum/strength
    reg260 = registers[4]   # firmware signature -- unique per gripper model

    # MG10 magnetic gripper
    # reg260 is in range 65000-65535 (firmware constant ~65075)
    if 65000 <= reg260 <= 65535:
        return 'mg10', uid

    # VGC10 vacuum gripper (built-in electric pump, no external air needed)
    # reg260 is in range 80-100 (firmware constant ~84-87)
    if 80 <= reg260 <= 100:
        return 'vgc10', uid

    # SG soft gripper
    # reg260 is in range 1-5 (firmware constant = 1 when idle)
    # Note: SG needs a 3 second initialisation delay after connection
    if 1 <= reg260 <= 5:
        return 'sg', uid

    # RG parallel-jaw gripper (RG2 or RG6)
    # reg260 is in range 5-10 (firmware constant ~6-7)
    # RG2 and RG6 share the same firmware signature -- distinguished by
    # the 'rg' type which defaults to RG6 (most common in NR lab).
    # Set RG_MODEL=rg2 environment variable to override.
    if 5 < reg260 <= 10:
        import os
        model = os.environ.get('RG_MODEL', 'rg6')
        return model, uid

    # 3FG15 three-finger gripper
    # reg260 = 0, but reg257 contains the current finger diameter (> 0 when gripper is alive)
    if reg260 == 0 and reg257 > 0:
        return 'fg15', uid

    # SG initialising: reg256 > 100 (status = 495 when busy/initialising)
    # reg260 may read 0 during the init sequence
    if reg260 == 0 and registers[0] > 100:
        return 'sg', uid

    return 'unknown', uid


def load_gripper(gripper_type, unit_id):
    """
    Import and instantiate the correct driver class for the detected gripper.

    Args:
        gripper_type (str): one of 'fg15', 'rg2', 'rg6', 'sg', 'mg10', 'vgc10'
        unit_id (int): Modbus device ID to use

    Returns:
        gripper object or None if type unknown
    """
    if gripper_type == 'fg15':
        from gripper_driver.fg15 import FG15
        return FG15(IP, unit_id=unit_id)

    elif gripper_type in ('rg2', 'rg6'):
        from gripper_driver.rg2_rg6 import RG
        return RG(gripper_type, IP, unit_id=unit_id)

    elif gripper_type == 'sg':
        from gripper_driver.SG import SG
        g = SG(IP, unit_id=unit_id)
        time.sleep(3)  # SG requires 3s initialisation before responding
        return g

    elif gripper_type == 'mg10':
        from gripper_driver.mg10 import MG10
        return MG10(IP, unit_id=unit_id)

    elif gripper_type == 'vgc10':
        from gripper_driver.VGC10 import VG10
        return VG10(IP, unit_id=unit_id)

    return None


def auto_connect():
    """
    Scan, detect, and return a ready-to-use gripper object.

    Returns:
        tuple: (gripper object, gripper_type str)

    Raises:
        RuntimeError: if no gripper is detected

    Example:
        from detect_gripper import auto_connect
        g, gripper_type = auto_connect()
        g.open_gripper()
    """
    responding = scan_device_ids()
    if not responding:
        raise RuntimeError("No grippers detected. Check Ethernet connection to 192.168.1.1.")

    # Use the first responding device
    uid, registers = responding[0]
    gripper_type, detected_uid = fingerprint(uid, registers)
    g = load_gripper(gripper_type, uid)

    if g is None:
        raise RuntimeError(f"Could not load driver for detected type: {gripper_type}")

    print(f"Auto-connected: {gripper_type.upper()} on device ID {uid}")
    return g, gripper_type


if __name__ == '__main__':
    print("Scanning for connected grippers...")
    responding = scan_device_ids()

    if not responding:
        print("No grippers detected. Check Ethernet connection to compute box.")
        sys.exit(1)

    print(f"Found {len(responding)} responding device(s)")

    for uid, registers in responding:
        gripper_type, detected_uid = fingerprint(uid, registers)
        print(f"\nDevice ID {uid}: detected as {gripper_type.upper()}")
        print(f"  Signature registers [256-260]: {registers}")

        g = load_gripper(gripper_type, uid)
        if g:
            print(f"  Status: {g.get_status()}")
            print(f"  Driver: gripper_driver.{gripper_type}")
        else:
            print("  Could not load driver")
