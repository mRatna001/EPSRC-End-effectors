from enum import Enum

class GripperType(Enum):
    RG2         = 'rg2'
    RG6         = 'rg6'
    TWO_FG7     = '2fg7'
    THREE_FG15  = '3fg15'
    VG10        = 'vg10'
    VGC10       = 'vgc10'
    GECKO       = 'gecko'
    SOFT_GRIPPER= 'soft_gripper'


class ControlCommand(Enum):
    GRIP = 1
    STOP = 8
    GRIP_WITH_OFFSET = 16


class GripType(Enum):
    GRIP_EXTERNAL = 0
    GRIP_INTERNAL = 1
    