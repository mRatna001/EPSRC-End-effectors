from base import BaseFingeredGripper

REG_TARGET_WIDTH    = 0
REG_TARGET_FORCE    = 1
REG_TARGET_SPEED    = 2
REG_COMMAND         = 3

REG_STATUS          = 256
REG_EXTERNAL_WIDTH  = 257
REG_INTERNAL_WIDTH  = 258
REG_MIN_EXT_WIDTH   = 259
REG_MAX_EXT_WIDTH   = 260
REG_MIN_INT_WIDTH   = 261
REG_MAX_INT_WIDTH   = 262
REG_FORCE           = 263
REG_MAX_FORCE       = 1029

CMD_GRIP_EXTERNAL   = 1
CMD_GRIP_INTERNAL   = 2
CMD_STOP            = 3

MIN_SPEED = 10
MAX_SPEED = 100


class TWOFG7(BaseFingeredGripper):

    def __init__(self, ip: str, port: int = 502):
        super().__init__(ip, port)
        self.max_force = self._read_register(REG_MAX_FORCE)
        self.max_width = self._read_register(REG_MAX_EXT_WIDTH) / 10.0
        self.min_width = self._read_register(REG_MIN_EXT_WIDTH) / 10.0

    def get_external_width(self) -> float:
        return self._read_register(REG_EXTERNAL_WIDTH) / 10.0

    def get_internal_width(self) -> float:
        return self._read_register(REG_INTERNAL_WIDTH) / 10.0

    def get_force(self) -> float:
        return self._read_register(REG_FORCE)

    def get_status(self) -> dict:
        raw = self._read_register(REG_STATUS)
        bits = format(raw, '016b')
        return {
            'busy':           bool(int(bits[-1])),
            'grip_detected':  bool(int(bits[-2])),
            'not_calibrated': bool(int(bits[-4])),
            'sensor_error':   bool(int(bits[-5])),
        }

    def open_gripper(self, force_n: float = 20.0, speed: int = 50):
        self._write_registers(
            address=REG_TARGET_WIDTH,
            values=[int(self.max_width * 10), int(force_n), speed, CMD_GRIP_EXTERNAL]
        )

    def close_gripper(self, force_n: float = 20.0, speed: int = 50):
        self._write_registers(
            address=REG_TARGET_WIDTH,
            values=[int(self.min_width * 10), int(force_n), speed, CMD_GRIP_EXTERNAL]
        )

    def move_gripper(self, width_mm: float, force_n: float = 20.0, speed: int = 50):
        speed = max(MIN_SPEED, min(MAX_SPEED, speed))
        force_n = max(0, min(self.max_force, force_n))
        self._write_registers(
            address=REG_TARGET_WIDTH,
            values=[int(width_mm * 10), int(force_n), speed, CMD_GRIP_EXTERNAL]
        )

    def stop(self):
        self._write_register(REG_COMMAND, CMD_STOP)
