from gripper_driver.base import BaseGripper

REG_TARGET_FORCE        = 0
REG_TARGET_WIDTH        = 1
REG_CONTROL             = 2
REG_FINGERTIP_OFFSET    = 258
REG_ACTUAL_DEPTH        = 263
REG_ACTUAL_WIDTH        = 267
REG_STATUS              = 268
REG_ACTUAL_WIDTH_OFFSET = 275
REG_SET_FINGERTIP_OFFSET= 1031

CMD_GRIP         = 1
CMD_STOP         = 8
CMD_GRIP_W_OFFSET= 16

class RG(BaseGripper):
    def __init__(self, gripper: str, ip: str, port: int = 502, unit_id: int = 66):
        super().__init__(ip, port, unit_id)
        self.gripper = gripper
        if gripper == 'rg2':
            self.max_width = 1100
            self.max_force = 400
        elif gripper == 'rg6':
            self.max_width = 1600
            self.max_force = 1200
        else:
            raise ValueError(f"Unknown gripper: {gripper}")

    def get_width(self):
        return self._read_register(REG_ACTUAL_WIDTH) / 10.0

    def get_width_with_offset(self):
        return self._read_register(REG_ACTUAL_WIDTH_OFFSET) / 10.0

    def get_status(self):
        raw = self._read_register(REG_STATUS)
        bits = format(raw, '016b')
        return {
            'busy':          bool(int(bits[-1])),
            'grip_detected': bool(int(bits[-2])),
            's1_pushed':     bool(int(bits[-3])),
            's1_trigged':    bool(int(bits[-4])),
            's2_pushed':     bool(int(bits[-5])),
            's2_trigged':    bool(int(bits[-6])),
            'safety_error':  bool(int(bits[-7])),
        }

    def open_gripper(self, force_val: int = 400):
        force_val = max(0, min(self.max_force, force_val))
        self._write_registers(address=REG_TARGET_FORCE, values=[force_val, self.max_width, CMD_GRIP_W_OFFSET])

    def close_gripper(self, force_val: int = 400):
        force_val = max(0, min(self.max_force, force_val))
        self._write_registers(address=REG_TARGET_FORCE, values=[force_val, 0, CMD_GRIP_W_OFFSET])

    def move_gripper(self, width_mm: float, force_val: int = 400):
        width = int(max(0, min(self.max_width, width_mm * 10)))
        force_val = max(0, min(self.max_force, force_val))
        self._write_registers(address=REG_TARGET_FORCE, values=[force_val, width, CMD_GRIP_W_OFFSET])

    def stop(self):
        self._write_register(REG_CONTROL, CMD_STOP)
