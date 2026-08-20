#!/usr/bin/env python3
import sys, time
sys.path.insert(0, "/home/maira/EPSRC-End-effectors")
from pymodbus.client import ModbusTcpClient

IP = "192.168.1.1"
PORT = 502

SIGNATURES = {
    65075: "mg10",
    87:    "vgc10",
    1:     "sg",
    6:     "rg",      # rg2 or rg6, check reg258
}

def try_read(uid, address, count=1):
    try:
        client = ModbusTcpClient(IP, port=PORT, timeout=1, retries=0)
        client.connect()
        r = client.read_holding_registers(address=address, count=count, device_id=uid)
        client.close()
        time.sleep(0.2)
        if not r.isError():
            return r.registers
    except: pass
    return None

def scan_device_ids():
    responding = []
    for uid in range(63, 70):
        r = try_read(uid, 256, 5)
        if r:
            responding.append((uid, r))
        time.sleep(0.1)
    return responding

def fingerprint(uid, registers):
    reg258 = registers[2] if len(registers) > 2 else 0
    reg257 = registers[1] if len(registers) > 1 else 0
    reg260 = registers[4] if len(registers) >= 5 else 0

    if reg260 in SIGNATURES:
        gtype = SIGNATURES[reg260]
        if gtype == "rg":
            return ("rg6" if reg258 > 1100 else "rg2"), uid
        return gtype, uid

    # 3FG15: reg260=0 but reg257 > 0 (diameter reading)
    if reg260 == 0 and reg257 > 0:
        return "fg15", uid

    return "unknown", uid

def load_gripper(gripper_type, unit_id):
    if gripper_type == "fg15":
        from gripper_driver.fg15 import FG15
        return FG15(IP, unit_id=unit_id)
    elif gripper_type == "rg2":
        from gripper_driver.rg2_rg6 import RG
        return RG("rg2", IP, unit_id=unit_id)
    elif gripper_type == "rg6":
        from gripper_driver.rg2_rg6 import RG
        return RG("rg6", IP, unit_id=unit_id)
    elif gripper_type == "sg":
        from gripper_driver.SG import SG
        return SG(IP, unit_id=unit_id)
    elif gripper_type == "mg10":
        from gripper_driver.mg10 import MG10
        return MG10(IP, unit_id=unit_id)
    elif gripper_type == "vgc10":
        from gripper_driver.VGC10 import VG10
        return VG10(IP, unit_id=unit_id)
    return None

def auto_connect():
    responding = scan_device_ids()
    if not responding:
        raise RuntimeError("No grippers detected")
    uid, registers = responding[0]
    gripper_type, detected_uid = fingerprint(uid, registers)
    g = load_gripper(gripper_type, uid)
    print(f"Auto-connected: {gripper_type.upper()} on device ID {uid}")
    return g, gripper_type

if __name__ == "__main__":
    print("Scanning for connected grippers...")
    responding = scan_device_ids()
    if not responding:
        print("No grippers detected.")
        sys.exit(1)
    print(f"Found {len(responding)} responding device(s)")
    for uid, registers in responding:
        gripper_type, detected_uid = fingerprint(uid, registers)
        print(f"Device ID {uid}: detected as {gripper_type.upper()}")
        g = load_gripper(gripper_type, uid)
        if g:
            print(f"Status: {g.get_status()}")
        else:
            print("Could not load driver")
