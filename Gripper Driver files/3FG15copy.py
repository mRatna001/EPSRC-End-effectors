


from base import BaseFingeredGripper


REG_TARGET_FORCE    = 0     
REG_TARGET_DIAMETER = 1     
REG_GRIP_TYPE       = 2     
REG_CONTROL         = 3     

REG_STATUS          = 256   
REG_RAW_DIAMETER    = 257   
REG_DIAMETER_OFFSET = 258   
REG_FORCE_APPLIED   = 259   
REG_FINGER_LENGTH   = 270   
REG_FINGER_POSITION = 272   
REG_FINGERTIP_OFFSET= 273   
REG_MIN_DIAMETER    = 513   
REG_MAX_DIAMETER    = 514   

# Read/Write registers
REG_SET_FINGER_LENGTH   = 1025  
REG_SET_FINGER_POSITION = 1027  
REG_SET_FINGERTIP_OFFSET= 1028  


CMD_GRIP            = 1    
CMD_MOVE            = 2     
CMD_STOP            = 4     
CMD_FLEXIBLE_GRIP   = 5     


GRIP_EXTERNAL       = 0     
GRIP_INTERNAL       = 1     


MAX_FORCE_PERCENT   = 1000  
MIN_FORCE_PERCENT   = 0
MAX_DIAMETER_MM     = 150   
MIN_DIAMETER_MM     = 0     


UNIT_ID             = 65


class THREEFG15(BaseFingeredGripper):
    def __init__(self, ip: str, port: int = 502):
    super().__init__(ip, port)
    self._min_diameter_mm = self._read_min_diameter()
    self._max_diameter_mm = self._read_max_diameter()
   


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