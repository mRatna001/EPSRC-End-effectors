#!/usr/bin/env python3
"""
Auto-detects which OnRobot gripper is connected and loads the right driver.
Usage: python3 detect_gripper.py
"""
import sys
import time
sys.path.insert(0, '/home/maira/EPSRC-End-effectors')

from pymodbus.client import ModbusTcpClient

IP = '192.168.1.1'
PORT = 502

def scan_device_ids():
    """Find which device IDs respond."""
    responding = []
    for uid in range(63, 70):
        try:
            client = ModbusTcpClient(IP, port=PORT, timeout=1, retries=0)
            client.connect()
            r = client.read_holding_registers(address=256, count=3, device_id=uid)
            if not r.isError():
                responding.append((uid, r.registers))
            client.close()
            time.sleep(0.3)
        except:
            try: client.close()
            except: pass
    return responding

def fingerprint(uid, registers):
    """
    Identify gripper from status register patterns.
    Each gripper has a distinctive register layout at address 256-258.
    """
    if len(registers) < 2:
        return None, None

    status = registers[0]
    reg2 = registers[1] if len(registers) > 1 else 0
    reg3 = registers[2] if len(registers) > 2 else 0

    # MG10: reg2 is error code, reg3 is magnet strength 0-100
    if 0 <= reg3 <= 100 and reg3 != reg2:
        return 'mg10', uid

    # SG: status has initialized bit (bit 1), width registers follow
    bits = format(status, '016b')
    if int(bits[-2]) == 1:  # initialized bit set
        return 'sg', uid

    # VGC10/VG10: registers 258/259 are vacuum readings in mbar*1000
    try:
        client = ModbusTcpClient(IP, port=PORT, timeout=1, retries=0)
        client.connect()
        r = client.read_holding_registers(address=258, count=2, device_id=uid)
        client.close()
        if not r.isError():
            a, b = r.registers
            if 0 <= a <= 100000 and 0 <= b <= 100000:
                return 'vgc10', uid
    except:
        pass

    # RG2/RG6: status at 268, width at 267
    try:
        client = ModbusTcpClient(IP, port=PORT, timeout=1, retries=0)
        client.connect()
        r = client.read_holding_registers(address=267, count=2, device_id=uid)
        client.close()
        if not r.isError():
            width = r.registers[0]
            if 0 <= width <= 1600:  # valid width range
                if width <= 1100:
                    return 'rg2', uid
                else:
                    return 'rg6', uid
    except:
        pass

    # 3FG15: has diameter register at 257
    try:
        client = ModbusTcpClient(IP, port=PORT, timeout=1, retries=0)
        client.connect()
        r = client.read_holding_registers(address=257, count=1, device_id=uid)
        client.close()
        if not r.isError():
            diameter = r.registers[0]
            if 0 <= diameter <= 1500:
                return 'fg15', uid
    except:
        pass

    return 'unknown', uid

def load_gripper(gripper_type, unit_id):
    """Load the right driver based on detected gripper type."""
    if gripper_type == 'fg15':
        from gripper_driver.fg15 import FG15
        return FG15(IP, unit_id=unit_id)
    elif gripper_type == 'rg2':
        from gripper_driver.rg2_rg6 import RG
        return RG('rg2', IP, unit_id=unit_id)
    elif gripper_type == 'rg6':
        from gripper_driver.rg2_rg6 import RG
        return RG('rg6', IP, unit_id=unit_id)
    elif gripper_type == 'sg':
        from gripper_driver.SG import SG
        return SG(IP, unit_id=unit_id)
    elif gripper_type == 'mg10':
        from gripper_driver.mg10 import MG10
        return MG10(IP, unit_id=unit_id)
    elif gripper_type == 'vgc10':
        from gripper_driver.VGC10 import VGC10
        return VGC10(IP, unit_id=unit_id)
    return None

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

        g = load_gripper(gripper_type, uid)
        if g:
            print(f"Status: {g.get_status()}")
            print(f"Driver loaded: gripper_driver.{gripper_type}")
        else:
            print("Could not load driver")
