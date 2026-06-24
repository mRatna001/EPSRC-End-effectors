"""
OnRobot 3FG15 Modbus TCP driver.
Register map from OnRobot Modbus documentation section 3.1.5.3
"""

from pymodbus.client import ModbusTcpClient
import BaseGripper

# ─── Register map ────────────────────────────────────────────────────────────

# Write registers
REG_TARGET_FORCE    = 0     # 0x0000 -- target force in % (0-1000)
REG_TARGET_DIAMETER = 1     # 0x0001 -- target diameter in 1/10 mm
REG_GRIP_TYPE       = 2     # 0x0002 -- 0=external, 1=internal
REG_CONTROL         = 3     # 0x0003 -- control command

# Read registers
REG_STATUS          = 256   # 0x0100 -- status flags
REG_RAW_DIAMETER    = 257   # 0x0101 -- raw diameter in 1/10 mm
REG_DIAMETER_OFFSET = 258   # 0x0102 -- diameter with fingertip offset in 1/10 mm
REG_FORCE_APPLIED   = 259   # 0x0103 -- force applied in 1/10 %
REG_FINGER_LENGTH   = 270   # 0x010E -- finger length in 1/10 mm
REG_FINGER_POSITION = 272   # 0x0110 -- finger position (1, 2 or 3)
REG_FINGERTIP_OFFSET= 273   # 0x0111 -- fingertip offset in 1/100 mm
REG_MIN_DIAMETER    = 513   # 0x0201 -- minimum reachable diameter
REG_MAX_DIAMETER    = 514   # 0x0202 -- maximum reachable diameter

# Read/Write registers
REG_SET_FINGER_LENGTH   = 1025  # 0x0401 -- set finger length in 1/10 mm
REG_SET_FINGER_POSITION = 1027  # 0x0403 -- set finger position (1, 2 or 3)
REG_SET_FINGERTIP_OFFSET= 1028  # 0x0404 -- set fingertip offset in 1/100 mm

# ─── Control commands ─────────────────────────────────────────────────────────
CMD_GRIP            = 1     # 0x0001 -- start motion with target force and diameter
CMD_MOVE            = 2     # 0x0002 -- move without applying force
CMD_STOP            = 4     # 0x0004 -- stop current motion
CMD_FLEXIBLE_GRIP   = 5     # 0x0005 -- flexible grip

# ─── Grip types ───────────────────────────────────────────────────────────────
GRIP_EXTERNAL       = 0     # diameter measured inside fingertips
GRIP_INTERNAL       = 1     # diameter measured outside fingertips

# ─── Physical limits ──────────────────────────────────────────────────────────
MAX_FORCE_PERCENT   = 1000  # max force in % (maps to 140N at 100%)
MIN_FORCE_PERCENT   = 0
MAX_DIAMETER_MM     = 150   # approximate -- real max read from REG_MAX_DIAMETER
MIN_DIAMETER_MM     = 0     # approximate -- real min read from REG_MIN_DIAMETER

# Modbus unit ID -- via Quick Changer = 65
UNIT_ID             = 65


class FG15(BaseFingeredGripper):
    """Driver for OnRobot 3FG15 three-finger gripper over Modbus TCP."""

    def __init__(self, ip: str, port: int = 502):
        self.ip = ip
        self.port = port
        self.client = ModbusTcpClient(host=ip, port=port, timeout=1)
        self.open_connection()
        # Read real limits from gripper after connecting
        self._min_diameter_mm = self._read_min_diameter()
        self._max_diameter_mm = self._read_max_diameter()

    # ─── Connection ───────────────────────────────────────────────────────────

    def open_connection(self):
        """Opens Modbus TCP connection to gripper."""
        self.client.connect()

    def close_connection(self):
        """Closes Modbus TCP connection."""
        self.client.close()

    # ─── Private helpers ──────────────────────────────────────────────────────

    def _read_register(self, address: int) -> int:
        """Reads one holding register, returns raw integer value."""
        result = self.client.read_holding_registers(
            address=address,
            count=1,
            slave=UNIT_ID
        )
        return result.registers[0]

    def _write_register(self, address: int, value: int):
        """Writes one value to one holding register."""
        self.client.write_register(
            address=address,
            value=value,
            slave=UNIT_ID
        )

    def _write_registers(self, address: int, values: list):
        """Writes multiple consecutive registers in one request."""
        self.client.write_registers(
            address=address,
            values=values,
            slave=UNIT_ID
        )

    def _read_min_diameter(self) -> float:
        """Reads minimum reachable diameter from gripper in mm."""
        try:
            return self._read_register(REG_MIN_DIAMETER) / 10.0
        except Exception:
            return MIN_DIAMETER_MM

    def _read_max_diameter(self) -> float:
        """Reads maximum reachable diameter from gripper in mm."""
        try:
            return self._read_register(REG_MAX_DIAMETER) / 10.0
        except Exception:
            return MAX_DIAMETER_MM

    def _clamp_diameter(self, diameter_mm: float) -> float:
        return max(self._min_diameter_mm, min(self._max_diameter_mm, diameter_mm))

    def _clamp_force(self, force_percent: float) -> float:
        return max(MIN_FORCE_PERCENT, min(MAX_FORCE_PERCENT, force_percent))

    # ─── Read registers (sense) ───────────────────────────────────────────────

    def get_diameter(self) -> float:
        """Current raw diameter in mm (center of fingertips)."""
        return self._read_register(REG_RAW_DIAMETER) / 10.0

    def get_diameter_with_offset(self) -> float:
        """Current diameter with fingertip offset in mm."""
        return self._read_register(REG_DIAMETER_OFFSET) / 10.0

    def get_force_applied(self) -> float:
        """Current force applied as percentage (0-100%)."""
        return self._read_register(REG_FORCE_APPLIED) / 10.0

    def get_finger_length(self) -> float:
        """Current finger length in mm."""
        return self._read_register(REG_FINGER_LENGTH) / 10.0

    def get_finger_position(self) -> int:
        """Current finger position (1, 2 or 3)."""
        return self._read_register(REG_FINGER_POSITION)

    def get_fingertip_offset(self) -> float:
        """Current fingertip offset in mm."""
        return self._read_register(REG_FINGERTIP_OFFSET) / 100.0

    def get_min_diameter(self) -> float:
        """Minimum reachable diameter in mm."""
        return self._read_register(REG_MIN_DIAMETER) / 10.0

    def get_max_diameter(self) -> float:
        """Maximum reachable diameter in mm."""
        return self._read_register(REG_MAX_DIAMETER) / 10.0

    def get_status(self) -> dict:
        """
        Reads status register and returns dict of flags:
            busy            -- motion ongoing
            grip_detected   -- object gripped
            force_grip      -- grip with target force detected
            calibration_ok  -- calibration status
        """
        raw = self._read_register(REG_STATUS)
        status_bits = format(raw, '016b')
        return {
            'busy':           bool(int(status_bits[-1])),
            'grip_detected':  bool(int(status_bits[-2])),
            'force_grip':     bool(int(status_bits[-3])),
            'calibration_ok': bool(int(status_bits[-4])),
        }

    # ─── Write registers (move) ───────────────────────────────────────────────

    def set_target_force(self, force_percent: float):
        """
        Sets target gripping force as percentage (0-100).
        Internally maps to 0-1000 register range.
        100% = 140N maximum force.
        """
        val = int(self._clamp_force(force_percent * 10))
        self._write_register(REG_TARGET_FORCE, val)

    def set_target_diameter(self, diameter_mm: float):
        """
        Sets target diameter in mm.
        Converts to 1/10 mm before writing.
        Clamped to gripper's actual min/max range.
        """
        diameter_mm = self._clamp_diameter(diameter_mm)
        self._write_register(REG_TARGET_DIAMETER, int(diameter_mm * 10))

    def set_grip_type(self, grip_type: int = GRIP_EXTERNAL):
        """Sets grip type: GRIP_EXTERNAL (0) or GRIP_INTERNAL (1)."""
        self._write_register(REG_GRIP_TYPE, grip_type)

    def set_control(self, command: int):
        """
        Sends control command:
            CMD_GRIP (1)          -- grip with force
            CMD_MOVE (2)          -- move without force
            CMD_STOP (4)          -- stop
            CMD_FLEXIBLE_GRIP (5) -- flexible grip
        """
        self._write_register(REG_CONTROL, command)

    # ─── High level commands ──────────────────────────────────────────────────

    def open_gripper(self, force_percent: float = 30.0):
        """Opens gripper to maximum diameter."""
        self._write_registers(
            address=REG_TARGET_FORCE,
            values=[
                int(self._clamp_force(force_percent * 10)),
                int(self._max_diameter_mm * 10),
                GRIP_EXTERNAL,
                CMD_GRIP
            ]
        )

    def close_gripper(self, force_percent: float = 30.0):
        """Closes gripper to minimum diameter."""
        self._write_registers(
            address=REG_TARGET_FORCE,
            values=[
                int(self._clamp_force(force_percent * 10)),
                int(self._min_diameter_mm * 10),
                GRIP_EXTERNAL,
                CMD_GRIP
            ]
        )

    def move_gripper(self, diameter_mm: float, force_percent: float = 30.0,
                     grip_type: int = GRIP_EXTERNAL):
        """
        Moves gripper to specified diameter at specified force.
        
        Args:
            diameter_mm:    target diameter in mm
            force_percent:  gripping force as percentage 0-100
            grip_type:      GRIP_EXTERNAL (0) or GRIP_INTERNAL (1)
        """
        self._write_registers(
            address=REG_TARGET_FORCE,
            values=[
                int(self._clamp_force(force_percent * 10)),
                int(self._clamp_diameter(diameter_mm) * 10),
                grip_type,
                CMD_GRIP
            ]
        )

    def move_without_force(self, diameter_mm: float):
        """Moves to diameter without applying gripping force."""
        self._write_registers(
            address=REG_TARGET_FORCE,
            values=[
                0,
                int(self._clamp_diameter(diameter_mm) * 10),
                GRIP_EXTERNAL,
                CMD_MOVE
            ]
        )

    def stop(self):
        """Stops current motion immediately."""
        self.set_control(CMD_STOP)

    def flexible_grip(self, diameter_mm: float, force_percent: float = 30.0):
        """
        Flexible grip -- fingers move toward target then grip.
        Maximum force 140N at 100%, maximum payload 8kg.
        """
        self._write_registers(
            address=REG_TARGET_FORCE,
            values=[
                int(self._clamp_force(force_percent * 10)),
                int(self._clamp_diameter(diameter_mm) * 10),
                GRIP_EXTERNAL,
                CMD_FLEXIBLE_GRIP
            ]
        )