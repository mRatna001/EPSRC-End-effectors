#!/usr/bin/env python3
"""
base.py
-------
Abstract base classes for all OnRobot gripper drivers.

Hierarchy:
    BaseGripper (ABC)
    ├── BaseFingeredGripper   -- for grippers with moving fingers (RG2, RG6, 3FG15, 2FG7, SG, RG2-FT)
    └── BaseVacuumGripper     -- for suction-based grippers (VG10, VGC10)

    MG10 inherits directly from BaseGripper (magnetic, no fingers or vacuum)

Why abstract base classes?
    The ROS2 node and auto-detection script call g.open_gripper() and g.get_status()
    without knowing which gripper g is. The ABC enforces that every driver
    implements the same interface -- if a method is missing, Python raises an
    error at instantiation rather than silently failing at runtime.

Why a shared base for Modbus?
    All OnRobot grippers communicate over Modbus TCP using the same underlying
    read/write register pattern. The base class handles the connection and
    low-level register access so individual drivers only need to implement
    their gripper-specific logic.
"""

from abc import ABC, abstractmethod
from pymodbus.client import ModbusTcpClient


class BaseGripper(ABC):
    """
    Abstract base class for all OnRobot gripper drivers.

    Manages the Modbus TCP connection to the compute box and provides
    three low-level register access methods used by all drivers.

    Args:
        ip (str): IP address of the OnRobot compute box (default 192.168.1.1)
        port (int): Modbus TCP port (default 502)
        unit_id (int): Modbus device ID for this gripper.
                       66 = primary side Dual Quick Changer (most fingered grippers)
                       65 = secondary side / single port (SG, MG10)
                       Determined empirically -- scan with detect_gripper.py if unsure.
    """

    def __init__(self, ip: str, port: int = 502, unit_id: int = 66):
        self.unit_id = unit_id
        self.ip      = ip
        self.port    = port
        # timeout=1 means each Modbus request will wait up to 1 second for a response
        # before raising a ModbusIOException. This prevents hanging indefinitely
        # if the compute box is unreachable.
        self.modbus  = ModbusTcpClient(host=ip, port=port, timeout=1)
        self.open_connection()

    def open_connection(self):
        """Opens the Modbus TCP connection to the compute box."""
        self.modbus.connect()

    def close_connection(self):
        """Closes the Modbus TCP connection. Call on shutdown."""
        self.modbus.close()

    def _read_register(self, address: int) -> int:
        """
        Read one holding register and return its raw integer value.

        Modbus holding registers are 16-bit unsigned integers (0-65535).
        Each gripper's register map defines what each address means --
        e.g. register 256 is typically the status register.

        Args:
            address (int): register address to read

        Returns:
            int: raw 16-bit register value
        """
        result = self.modbus.read_holding_registers(
            address=address,
            count=1,
            device_id=self.unit_id
        )
        return result.registers[0]

    def _write_register(self, address: int, value: int):
        """
        Write a single value to one holding register (Modbus function code 6).

        Args:
            address (int): register address to write
            value (int): value to write (0-65535)
        """
        self.modbus.write_register(
            address=address,
            value=value,
            device_id=self.unit_id
        )

    def _write_registers(self, address: int, values: list):
        """
        Write multiple consecutive registers in one atomic Modbus request
        (Modbus function code 16).

        Using one request instead of multiple individual writes ensures the
        gripper receives all parameters (e.g. force, width, command) together
        and acts on them atomically, avoiding partial updates.

        Args:
            address (int): starting register address
            values (list): list of integer values to write consecutively
        """
        self.modbus.write_registers(
            address=address,
            values=values,
            device_id=self.unit_id
        )

    @abstractmethod
    def get_status(self) -> dict:
        """
        Read and decode the gripper's status register(s).

        Returns:
            dict: named status flags (e.g. {'busy': False, 'grip_detected': True})
                  Keys vary per gripper -- see individual driver docstrings.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """Halt all gripper motion immediately."""
        pass


class BaseFingeredGripper(BaseGripper):
    """
    Abstract base class for grippers with moving fingers.

    Extends BaseGripper with open, close, and move commands.
    Used by: RG2, RG6, 3FG15, 2FG7, SG, RG2-FT.
    """

    @abstractmethod
    def open_gripper(self, **kwargs) -> None:
        """Open the gripper to its maximum width/diameter."""
        pass

    @abstractmethod
    def close_gripper(self, **kwargs) -> None:
        """Close the gripper to its minimum width/diameter."""
        pass

    @abstractmethod
    def move_gripper(self, width_val: float, force_val: int) -> None:
        """
        Move gripper to a specific width or diameter.

        Args:
            width_val (float): target width or diameter in mm
            force_val (int): gripping force (units vary per gripper)
        """
        pass


class BaseVacuumGripper(BaseGripper):
    """
    Abstract base class for suction-based grippers.

    Extends BaseGripper with grip and release commands.
    Used by: VG10, VGC10.
    """

    @abstractmethod
    def grip(self, vacuum_percent: int) -> None:
        """
        Activate vacuum suction.

        Args:
            vacuum_percent (int): target vacuum level 0-80%
        """
        pass

    @abstractmethod
    def release(self) -> None:
        """Deactivate vacuum and release the workpiece."""
        pass
