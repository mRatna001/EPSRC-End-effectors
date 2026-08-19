# EPSRC-End-effectors

A hardware-agnostic ROS2 framework for controlling OnRobot robotic end-effectors over Modbus TCP.

**EPSRC Summer Internship 2026 · National Robotarium, Heriot-Watt University**  
Maira Ratna | Supervised by Rahul Ramachandran & Romain Michalec

---

## What This Does

Plug in any OnRobot gripper, point the ROS2 node at its config file, and it works. No code changes needed when swapping grippers. The framework abstracts 9 gripper models behind a unified Python driver hierarchy, with a self-describing YAML config layer and a generic ROS2 node.

---

## Supported Grippers

| Gripper | Type | Status | Device ID |
|---------|------|--------|-----------|
| 3FG15   | Three-finger | Hardware validated ✓ | 66 |
| RG2     | Parallel-jaw | Driver complete | 65/66 |
| RG6     | Parallel-jaw | Driver complete | 65/66 |
| 2FG7    | Parallel-jaw | Driver complete | 65/66 |
| VG10    | Vacuum | Driver complete | 65/66 |
| VGC10   | Vacuum | Driver complete | 65/66 |
| SG      | Soft gripper | Hardware validated ✓ | 65 |
| MG10    | Magnetic | Hardware validated ✓ | 65 |
| RG2-FT  | Force/torque | Driver complete, not detected on lab compute box | - |

---

## Installation

```bash
# Clone the repo
git clone https://github.com/mRatna001/EPSRC-End-effectors.git
cd EPSRC-End-effectors

# Install dependencies
pip install pymodbus --break-system-packages
pip install anthropic --break-system-packages  # for LLM tooling only

# Source ROS2
source /opt/ros/jazzy/setup.bash
```

---

## Quick Start

### Test all connected grippers
```bash
python3 test_all_grippers.py
```

### Run a specific gripper
```python
from gripper_driver.fg15 import FG15

g = FG15('192.168.1.1', unit_id=66)
print(g.get_status())
g.open_gripper()
g.close_gripper()
```

### Launch the ROS2 node
```bash
source /opt/ros/jazzy/setup.bash
python3 ros2_nodes/GripperNodes.py --ros-args \
  -p config_file:=config/3fg15.yaml \
  -p ip_address:=192.168.1.1
```

The node publishes gripper status to `/status` at 20Hz and exposes `/open`, `/close`, `/stop` services.

---

## Architecture

```
EPSRC-End-effectors/
├── gripper_driver/
│   ├── base.py          # BaseGripper, BaseFingeredGripper, BaseVacuumGripper
│   ├── fg15.py          # OnRobot 3FG15
│   ├── rg2_rg6.py       # OnRobot RG2 / RG6
│   ├── TWOFG7.py        # OnRobot 2FG7
│   ├── vg10.py          # OnRobot VG10 / VGC10
│   ├── VGC10.py         # OnRobot VGC10
│   ├── SG.py            # OnRobot Soft Gripper
│   ├── mg10.py          # OnRobot MG10
│   └── rg2_ft.py        # OnRobot RG2-FT
├── config/
│   ├── 3fg15.yaml
│   ├── rg2.yaml
│   ├── rg6.yaml
│   ├── 2fg7.yaml
│   ├── vg10.yaml
│   ├── vgc10.yaml
│   ├── sg.yaml
│   └── mg10.yaml
├── ros2_nodes/
│   └── GripperNodes.py  # Generic ROS2 node
├── urdf/                # URDF files for Isaac Sim
├── test_all_grippers.py # Demo/test script
├── generate_driver.py   # LLM agent: datasheet -> driver
└── TROUBLESHOOTING.md
```

### Driver Hierarchy

```
BaseGripper (ABC)
├── BaseFingeredGripper
│   ├── FG15       (3FG15)
│   ├── RG         (RG2, RG6)
│   ├── TWOFG7     (2FG7)
│   ├── SG         (Soft Gripper)
│   └── RG2FT      (RG2-FT)
└── BaseVacuumGripper
    ├── VG10
    └── VGC10      (inherits VG10)
MG10               (inherits BaseGripper directly)
```

### Config Format (Homie-inspired)

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

The ROS2 node reads this at startup and adapts automatically -- no code changes needed when switching grippers.

---

## LLM Tooling

### Generate a driver from a register map
```bash
python3 generate_driver.py
```
Paste a gripper's Modbus register map and it writes the `.py` driver and `.yaml` config automatically using Claude.

### Grasp planning agent
Open `gripper_agent.jsx` in Claude.ai artifacts -- describe the task in plain English and it outputs the Python commands to run.

### URDF generator
Open `urdf_agent.jsx` in Claude.ai artifacts -- paste datasheet specs and it generates a complete URDF.

---

## Isaac Sim

3FG15 imported with real CAD geometry and articulated joints. Fingers move via USD physics drive API.

```bash
cd ~/isaac-sim
./isaac-sim.sh
# Then File -> Open -> ~/3fg15_urdf/3fg15.urdf
```

Move fingers in Script Editor:
```python
import omni.usd
from pxr import UsdPhysics

stage = omni.usd.get_context().get_stage()
for joint_name in ['finger_1_joint', 'finger_2_joint', 'finger_3_joint']:
    prim = stage.GetPrimAtPath(f'/tn__3fg15_/Physics/{joint_name}')
    drive = UsdPhysics.DriveAPI.Apply(prim, 'angular')
    drive.GetStiffnessAttr().Set(10000.0)
    drive.GetDampingAttr().Set(1000.0)
    drive.GetTargetPositionAttr().Set(20.0)
```

---

## Benchmarking Results

| Gripper | Cmd Latency (mean) | Cmd Latency (SD) | Motion Time (mean) | Motion Time (SD) |
|---------|-------------------|-----------------|-------------------|-----------------|
| MG10    | 14.3ms | 1.5ms | 395ms  | 5ms    |
| RG6     | 7.9ms  | 0.9ms | 7230ms | 1141ms |
| SG      | 21.0ms | 1.7ms | 1232ms | 10ms   |
| 3FG15   | TBC    | TBC   | TBC    | TBC    |
| RG2     | TBC    | TBC   | TBC    | TBC    |

All measurements: n=20 trials, Modbus TCP over Ethernet at 192.168.1.1:502.

---

## Known Issues

- **RG2-FT**: Not detected on lab compute box. Driver complete, hardware blocked.
- **Onshape URDF**: Mates required in Onshape assembly for full articulation export.
- **ros2_control**: Current node uses plain rclpy services. ros2_control hardware interface plugin rewrite is future work.

---

## References

- Torielli et al. (2023). ROS End-Effector: A Hardware-Agnostic Framework. JIRS 108, 70.
- OnRobot A/S (2024). Modbus TCP Register Maps.
- NVIDIA (2024). Isaac Sim 6.0 Documentation.
- Santello et al. (1998). Postural hand synergies. Journal of Neuroscience.
- DeliGrasp (2024). LLM-informed adaptive grasping. IEEE ICRA.
