from base import BaseFingeredGripper

# ─── Register map ────────────────────────────────────────────────────────────

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


class FG15(BaseFingeredGripper):

    def __init__(self, ip: str, port: int = 502):
        super().__init__(ip, port)
        self._min_diameter_mm = self._read_min_diameter()
        self._max_diameter_mm = self._read_max_diameter()

    def _read_min_diameter(self) -> float:
        try:
            return self._read_register(REG_MIN_DIAMETER) / 10.0
        except Exception:
            return MIN_DIAMETER_MM

    def _read_max_diameter(self) -> float:
        try:
            return self._read_register(REG_MAX_DIAMETER) / 10.0
        except Exception:
            return MAX_DIAMETER_MM

    def _clamp_diameter(self, diameter_mm: float) -> float:
        return max(self._min_diameter_mm, min(self._max_diameter_mm, diameter_mm))

    def _clamp_force(self, force_percent: float) -> float:
        return max(MIN_FORCE_PERCENT, min(MAX_FORCE_PERCENT, force_percent))

    def get_diameter(self) -> float:
        return self._read_register(REG_RAW_DIAMETER) / 10.0

    def get_diameter_with_offset(self) -> float:
        return self._read_register(REG_DIAMETER_OFFSET) / 10.0

    def get_force_applied(self) -> float:
        return self._read_register(REG_FORCE_APPLIED) / 10.0

    def get_finger_length(self) -> float:
        return self._read_register(REG_FINGER_LENGTH) / 10.0

    def get_finger_position(self) -> int:
        return self._read_register(REG_FINGER_POSITION)

    def get_fingertip_offset(self) -> float:
        return self._read_register(REG_FINGERTIP_OFFSET) / 100.0

    def get_min_diameter(self) -> float:
        return self._read_register(REG_MIN_DIAMETER) / 10.0

    def get_max_diameter(self) -> float:
        return self._read_register(REG_MAX_DIAMETER) / 10.0
    def get_status(self) -> dict:
        raw = self._read_register(REG_STATUS)
        status_bits = format(raw, '016b')
        return {
            'busy':           bool(int(status_bits[-1])),
            'grip_detected':  bool(int(status_bits[-2])),
            'force_grip':     bool(int(status_bits[-3])),
            'calibration_ok': bool(int(status_bits[-4])),
        }

    def set_target_force(self, force_percent: float):
        val = int(self._clamp_force(force_percent * 10))
        self._write_register(REG_TARGET_FORCE, val)

    def set_target_diameter(self, diameter_mm: float):
        diameter_mm = self._clamp_diameter(diameter_mm)
        self._write_register(REG_TARGET_DIAMETER, int(diameter_mm * 10))

    def set_grip_type(self, grip_type: int = GRIP_EXTERNAL):
        self._write_register(REG_GRIP_TYPE, grip_type)

    def set_control(self, command: int):
        self._write_register(REG_CONTROL, command)

    def open_gripper(self, force_percent: float = 30.0):
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
        self.set_control(CMD_STOP)

    def flexible_grip(self, diameter_mm: float, force_percent: float = 30.0):
        self._write_registers(
            address=REG_TARGET_FORCE,
            values=[
                int(self._clamp_force(force_percent * 10)),
                int(self._clamp_diameter(diameter_mm) * 10),
                GRIP_EXTERNAL,
                CMD_FLEXIBLE_GRIP
            ]
        )