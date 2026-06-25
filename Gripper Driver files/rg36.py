
from base import BaseFingeredGripper

UNIT_ID = 65


class RG(BaseFingeredGripper):
    def __init__(self, gripper: str, ip: str, port: int = 502):
    self.gripper = gripper
    if gripper == 'rg2':
        self.max_width = 1100
        self.max_force = 400
    elif gripper == 'rg6':
        self.max_width = 1600
        self.max_force = 1200
    super().__init__(ip, port)
    



    



    def get_width(self):
        return self._read_register(267)/10.0

    def get_width_with_offset(self) -> float:
        return self._read_register(275) / 10.0

    def get_fingertip_offset(self) -> float:
        return self._read_register(258) / 10.0

    def get_status(self) -> dict:
        raw = self._read_register(268)
        bits = format(raw, '016b')
        return {
            'busy':         bool(int(bits[-1])),
            'grip':         bool(int(bits[-2])),
            's1_pushed':    bool(int(bits[-3])),
            's1_trigged':   bool(int(bits[-4])),
            's2_pushed':    bool(int(bits[-5])),
            's2_trigged':   bool(int(bits[-6])),
            'safety_error': bool(int(bits[-7])),
        }


    def set_target_force(self, force_val: int):
        force_val = max(0, min(self.max_force, force_val))
        self._write_register(0, force_val)

    def set_target_width(self, width_val:int):
        width_val = max(0, min(self.max_width, width_val))
        self._write_register(1,width_val)

    def set_control_mode(self, command:int):
        self._write_register(2,command)


    def open_gripper(self, force_val: int=400 ):
        self._write_registers(
            address=0,
            values=[force_val, self.max_width, 16]
        )
        

    def close_gripper(self, force_val: int=400, ):
        self._write_registers(
            address = 0,
            values = [force_val, 0, 16]

        )

    def move_gripper(self, force_val: int, width_val: int):
        self._write_registers(
            address = 0,
            values = [force_val, width_val*10,16]
        )

    def stop(self):
        self.set_control_mode(8)