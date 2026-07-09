from base import BaseFingeredGripper

# Write registers
REG_ZERO                = 0
REG_TARGET_FORCE        = 2
REG_TARGET_WIDTH        = 3
REG_CONTROL             = 4
REG_PROXIMITY_OFFSET_L  = 5
REG_PROXIMITY_OFFSET_R  = 6

# Read registers
REG_HEX_STATUS_HIGH_L   = 256
REG_HEX_STATUS_LOW_L    = 257
REG_FX_L                = 259
REG_FY_L                = 260
REG_FZ_L                = 261
REG_TX_L                = 262
REG_TY_L                = 263
REG_TZ_L                = 264
REG_HEX_STATUS_HIGH_R   = 266
REG_HEX_STATUS_LOW_R    = 267
REG_FX_R                = 268
REG_FY_R                = 269
REG_FZ_R                = 270
REG_TX_R                = 271
REG_TY_R                = 272
REG_TZ_R                = 273
REG_PROXIMITY_STATUS_L  = 274
REG_PROXIMITY_VALUE_L   = 275
REG_PROXIMITY_STATUS_R  = 277
REG_PROXIMITY_VALUE_R   = 278
REG_ACTUAL_WIDTH        = 280
REG_BUSY                = 281
REG_GRIP_DETECTED       = 282

# Control commands
CMD_GRIP                = 1
CMD_STOP                = 8
CMD_GRIP_WITH_OFFSET    = 16

# Limits
MAX_WIDTH               = 1100
MAX_FORCE               = 400


class RG2FT(BaseFingeredGripper):

    def __init__(self, ip: str, port: int = 502):
        super().__init__(ip, port)
        self.max_width = MAX_WIDTH
        self.max_force = MAX_FORCE

    def get_width(self) -> float:
        return self._read_register(REG_ACTUAL_WIDTH) / 10.0

    def get_status(self) -> dict:
        return {
            'busy':         bool(self._read_register(REG_BUSY)),
            'grip_detected': bool(self._read_register(REG_GRIP_DETECTED)),
        }

    def get_force_torque_left(self) -> dict:
        return {
            'Fx': self._read_register(REG_FX_L) / 100.0,
            'Fy': self._read_register(REG_FY_L) / 100.0,
            'Fz': self._read_register(REG_FZ_L) / 100.0,
            'Tx': self._read_register(REG_TX_L) / 100.0,
            'Ty': self._read_register(REG_TY_L) / 100.0,
            'Tz': self._read_register(REG_TZ_L) / 100.0,
        }

    def get_force_torque_right(self) -> dict:
        return {
            'Fx': self._read_register(REG_FX_R) / 100.0,
            'Fy': self._read_register(REG_FY_R) / 100.0,
            'Fz': self._read_register(REG_FZ_R) / 100.0,
            'Tx': self._read_register(REG_TX_R) / 100.0,
            'Ty': self._read_register(REG_TY_R) / 100.0,
            'Tz': self._read_register(REG_TZ_R) / 100.0,
        }

    def get_proximity_left(self) -> dict:
        return {
            'status': self._read_register(REG_PROXIMITY_STATUS_L),
            'value':  self._read_register(REG_PROXIMITY_VALUE_L),
        }

    def get_proximity_right(self) -> dict:
        return {
            'status': self._read_register(REG_PROXIMITY_STATUS_R),
            'value':  self._read_register(REG_PROXIMITY_VALUE_R),
        }

    def open_gripper(self, force_val: int = 400):
        self._write_registers(
            address=REG_TARGET_FORCE,
            values=[force_val, self.max_width, CMD_GRIP_WITH_OFFSET]
        )

    def close_gripper(self, force_val: int = 400):
        self._write_registers(
            address=REG_TARGET_FORCE,
            values=[force_val, 0, CMD_GRIP_WITH_OFFSET]
        )

    def move_gripper(self, width_mm: float, force_val: int = 400):
        width_10mm = int(max(0, min(self.max_width, width_mm * 10)))
        self._write_registers(
            address=REG_TARGET_FORCE,
            values=[force_val, width_10mm, CMD_GRIP_WITH_OFFSET]
        )

    def stop(self):
        self._write_register(REG_CONTROL, CMD_STOP)
