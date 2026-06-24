from abc import ABC, abstractmethod


class BaseGripper(ABC):
    @abstractmethod
    def open_connection(self):
        pass

    @abstractmethod
    def close_connection(self):
        pass

    @abstractmethod
    def get_status(self) -> dict:
        pass

    @abstractmethod
    def stop(self):
        pass
    def open_connection(self):
        self.modbus.connect()

    def close_connection(self):
        self.modbus.close()

    def _read_register(self, address: int) -> int:
            """Reads one holding register, returns raw integer value."""
            result = self.modbus.read_holding_registers(
                address=address,
                count=1,
                slave=UNIT_ID
            )
            return result.registers[0]


    

    def _write_register(self, address: int, value: int):
            """Writes one value to one holding register."""
            self.modbus.write_register(
                address=address,
                value=value,
                slave=UNIT_ID
            )

    def _write_registers(self, address: int, values: list):
            """Writes multiple consecutive registers in one request."""
            self.modbus.write_registers(
                address=address,
                values=values,
                slave=UNIT_ID
            )


class BaseFingeredGripper(BaseGripper):
    @abstractmethod
    def open_gripper(self):
        pass

    @abstractmethod
    def close_gripper(self):
        pass

    @abstractmethod
    def move_gripper(self, width_val: float, force_val: int):
        pass


class BaseVacuumGripper(BaseGripper):
    @abstractmethod
    def grip(self, vacuum_percent: int):
        pass

    @abstractmethod
    def release(self):
        pass