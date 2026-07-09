from base import BaseFingeredGripper

REG_TARGET_WIDTH    = 0
REG_COMMAND         = 1
REG_GENTLE_GRIP     = 2
REG_GRIPPER_MODEL   = 3

REG_CURRENT_WIDTH   = 256
REG_STATUS          = 259
REG_MAX_WIDTH       = 262
REG_MIN_WIDTH       = 261

CMD_MOVE            = 1
CMD_STOP            = 2
CMD_INIT            = 3

MODEL_NONE          = 1
MODEL_A_HARD        = 2
MODEL_A_SOFT        = 3
MODEL_B_HARD        = 4


class SG(BaseFingeredGripper):

    def __init__(self, ip: str, port: int = 502, model: int = MODEL_A_SOFT, gentle: bool = False):
        super().__init__(ip, port)
        self.model = model
        self.gentle = gentle
        self._write_register(REG_GRIPPER_MODEL, self.model)
        self._write_register(REG_GENTLE_GRIP, 1 if gentle else 0)
        self._write_register(REG_COMMAND, CMD_INIT)

    def get_width(self) -> float:
        return self._read_register(REG_CURRENT_WIDTH) / 10.0

    def get_status(self) -> dict:
        raw = self._read_register(REG_STATUS)
        bits = format(raw, '016b')
        return {
            'busy':        bool(int(bits[-1])),
            'initialized': bool(int(bits[-2])),
            'error':       bool(int(bits[-5])) or bool(int(bits[-6])) or bool(int(bits[-7])),
        }

    def open_gripper(self, force_n: float = None, speed: int = None):
        max_width = self._read_register(REG_MAX_WIDTH)
        self._write_register(REG_TARGET_WIDTH, max_width)
        self._write_register(REG_COMMAND, CMD_MOVE)

    def close_gripper(self, force_n: float = None, speed: int = None):
        min_width = self._read_register(REG_MIN_WIDTH)
        self._write_register(REG_TARGET_WIDTH, min_width)
        self._write_register(REG_COMMAND, CMD_MOVE)

    def move_gripper(self, width_mm: float, force_n: float = None, speed: int = None):
        self._write_register(REG_TARGET_WIDTH, int(width_mm * 10))
        self._write_register(REG_COMMAND, CMD_MOVE)

    def stop(self):
        self._write_register(REG_COMMAND, CMD_STOP)