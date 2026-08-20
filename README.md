# EPSRC-End-effectors

A hardware-agnostic Python driver package for OnRobot robotic end-effectors over Modbus TCP.

**EPSRC Summer Internship 2026 · National Robotarium, Heriot-Watt University**  
Maira Ratnarajah | Supervised by Rahul Ramachandran & Romain Michalec

---

## Overview

Each OnRobot gripper communicates over Modbus TCP using a different register map. This package provides a unified Python driver hierarchy so any gripper can be commanded with the same interface -- `open_gripper()`, `close_gripper()`, `get_status()`, `stop()` -- without the calling code knowing which gripper is attached.

---

## Supported Grippers

| Gripper | Type | Driver | Hardware Status | Device ID |
|---------|------|--------|----------------|-----------|
| 3FG15   | Three-finger | `fg15.FG15` | Validated ✓ | 66 |
| RG2     | Parallel-jaw | `rg2_rg6.RG` (gripper='rg2') | Driver complete | 65/66 |
| RG6     | Parallel-jaw | `rg2_rg6.RG` (gripper='rg6') | Driver complete | 65/66 |
| 2FG7    | Parallel-jaw | `TWOFG7.TWOFG7` | Driver complete | 65/66 |
| VG10    | Vacuum | `vg10.VG10` | Driver complete | 65/66 |
| VGC10   | Vacuum | `VGC10.VG10` | Driver complete | 65/66 |
| SG      | Soft gripper | `SG.SG` | Validated ✓ | 65 |
| MG10    | Magnetic | `mg10.MG10` | Validated ✓ | 65 |
| RG2-FT  | Force/torque | `rg2_ft.RG2FT` | Not detected on lab compute box | - |

---

## Installation

```bash
git clone https://github.com/mRatna001/EPSRC-End-effectors.git
cd EPSRC-End-effectors
pip install pymodbus --break-system-packages
```

---

## Driver Package

The driver hierarchy is in `gripper_driver/`:

```
BaseGripper (ABC)
├── BaseFingeredGripper  →  FG15, RG, TWOFG7, SG, RG2FT
└── BaseVacuumGripper    →  VG10, VGC10
MG10                     →  inherits BaseGripper directly
```

`BaseGripper` manages the Modbus TCP connection and provides three low-level methods all drivers use:
- `_read_register(address)` -- read one 16-bit holding register
- `_write_register(address, value)` -- write one register (Modbus FC6)
- `_write_registers(address, values)` -- write multiple consecutive registers atomically (Modbus FC16)

Each driver implements the gripper-specific register map on top of these.

### Using a driver directly

```python
from gripper_driver.fg15 import FG15

g = FG15('192.168.1.1', unit_id=66)
print(g.get_status())
g.open_gripper()
g.move_gripper(diameter_mm=45.0, force_percent=30.0)
g.close_gripper()
g.stop()
```

```python
from gripper_driver.mg10 import MG10

g = MG10('192.168.1.1', unit_id=65)
print(g.get_status())
g.grip(strength=80)
g.release()
```

```python
from gripper_driver.VGC10 import VG10

g = VG10('192.168.1.1', unit_id=65)
g.grip(vacuum_percent=80, channel='both')
g.release()
```

---

## Auto-Detection

`detect_gripper.py` scans Modbus device IDs 64-69 and identifies the connected gripper from its firmware signature in register 260.

```
Gripper  | reg260 range  | Notes
---------|---------------|-------
MG10     | 65000-65535   | Magnetic gripper
VGC10    | 80-100        | Vacuum gripper
SG       | 1-5           | Soft gripper, needs 3s init delay
RG2/RG6  | 5-10          | Parallel jaw
3FG15    | 0             | Three-finger, reg257 = current diameter
```

### Run standalone

```bash
PYTHONPATH=/path/to/EPSRC-End-effectors python3 detect_gripper.py
```

### Import in a script

```python
from detect_gripper import auto_connect

g, gripper_type = auto_connect()
print(g.get_status())
g.open_gripper()
```

For RG2 specifically (defaults to RG6):

```bash
RG_MODEL=rg2 python3 detect_gripper.py
```

---

## Config Files

Each gripper has a YAML config in `config/` describing its properties, units, and limits. These are used by the ROS2 node to adapt at runtime without code changes.

```yaml
id: fg15
name: OnRobot 3FG15
driver: fg15.FG15
unit_id: 66
nodes:
  gripper:
    properties:
      diameter:
        datatype: float
        unit: mm
        settable: true
        min: 4
        max: 150
```

---

## Device IDs

The OnRobot compute box assigns Modbus device IDs based on which physical port the gripper is plugged into. Common values:

- **66** -- primary side (most fingered grippers when using Dual Quick Changer)
- **65** -- secondary side / single port (SG, MG10, RG6 when plugged into port 2)

If unsure, run `detect_gripper.py` -- it scans and identifies automatically.

---

## Known Issues

- **RG2-FT**: Not detected on lab compute box. Driver complete, hardware blocked -- likely a firmware issue.
- **RG2 vs RG6**: Both use the same firmware signature in reg260. Auto-detection defaults to RG6. Set `RG_MODEL=rg2` to override.

---

## References

- Torielli et al. (2023). ROS End-Effector: A Hardware-Agnostic Framework. JIRS 108, 70.
- OnRobot A/S (2024). Modbus TCP Register Maps. Product documentation.
