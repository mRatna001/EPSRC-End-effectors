from gripper_driver.base import BaseGripper

# Write registers
REG_CONTROL         = 0    # Magnet engage/disengage/smart grip/calibrate
REG_STRENGTH        = 1    # Target magnet strength 0-100%

# Read registers
REG_STATUS          = 256  # Status bits
REG_ERROR_CODE      = 257  # Error bits
REG_ACTUAL_STRENGTH = 258  # Current magnet strength 0-100%

# Read/Write registers
REG_FINGER_HEIGHT   = 1025  # Finger height in 1/10 mm
REG_FINGER_TYPE     = 1026  # Finger type (1=no pads, 2=protective pads, 3=custom)

# Control values
CMD_DISENGAGE       = 0
CMD_ENGAGE          = 1
CMD_SMART_GRIP      = 2
CMD_AUTO_CALIBRATE  = 6

# Finger types
FINGER_NO_PADS      = 1
FINGER_PROT_PADS    = 2
FINGER_CUSTOM       = 3

class MG10(BaseGripper):
    """
    Driver for the OnRobot MG10 magnetic gripper.

    The MG10 uses a BLDC electric motor to control magnetism strength
    across 10 discrete steps (0-100%). Unlike fingered grippers, there
    are no moving mechanical parts -- grip is achieved by energising the
    magnet, release by demagnetising it.

    Specs:
        Max payload:    10 kg (flat steel, no pads, parallel to ground)
        Pulling force:  300 N
        Gripping time:  300 ms (including brake activation)
        Proximity:      detects workpieces within 2 mm
        Weight:         0.8 kg
        IP rating:      IP67
        Dimensions:     Ø71 x 80.2 mm
    """

    def __init__(self, ip: str, port: int = 502, unit_id: int = 66):
        super().__init__(ip, port, unit_id)

    def get_status(self) -> dict:
        """
        Returns gripper status decoded from the 16-bit status register.

        Returns:
            dict with keys:
                part_gripped (bool):              workpiece gripped
                near_part (bool):                 proximity sensor detects ferromagnetic part within 2mm
                busy (bool):                      gripper is moving
                magnet_strength_not_reached (bool): target strength not yet reached
                smart_grip_available (bool):      Smart Grip feature available
                smart_grip_failed (bool):         Smart Grip failed
                part_dropped (bool):              workpiece lost since last grip
                internal_temp_warning (bool):     internal temperature exceeds 55°C
                actual_strength (int):            current magnet strength 0-100%
        """
        raw = self._read_register(REG_STATUS)
        bits = format(raw, '016b')
        return {
            'part_gripped':               bool(int(bits[-1])),
            'near_part':                  bool(int(bits[-2])),
            'busy':                       bool(int(bits[-3])),
            'magnet_strength_not_reached': bool(int(bits[-4])),
            'smart_grip_available':       bool(int(bits[-5])),
            'smart_grip_failed':          bool(int(bits[-6])),
            'part_dropped':               bool(int(bits[-7])),
            'internal_temp_warning':      bool(int(bits[-8])),
            'actual_strength':            self._read_register(REG_ACTUAL_STRENGTH),
        }

    def get_error(self) -> dict:
        """
        Returns error register decoded as named flags.

        Returns:
            dict with keys:
                overheating, sensor_target_mismatch, no_motor_calibration,
                no_magnet_calibration, no_hall_calibration, over_current,
                position_error
        """
        raw = self._read_register(REG_ERROR_CODE)
        bits = format(raw, '016b')
        return {
            'overheating':             bool(int(bits[-1])),
            'sensor_target_mismatch':  bool(int(bits[-2])),
            'no_motor_calibration':    bool(int(bits[-3])),
            'no_magnet_calibration':   bool(int(bits[-4])),
            'no_hall_calibration':     bool(int(bits[-5])),
            'over_current':            bool(int(bits[-6])),
            'position_error':          bool(int(bits[-7])),
        }

    def grip(self, strength: int = 100) -> None:
        """
        Engages the magnet at the given strength.

        Args:
            strength (int): target magnet strength 0-100%.
                            10 discrete steps; values rounded internally.
                            Default 100% for maximum 300N pulling force.
        """
        strength = max(0, min(100, int(strength)))
        self._write_register(REG_STRENGTH, strength)
        self._write_register(REG_CONTROL, CMD_ENGAGE)

    def smart_grip(self, strength: int = 100) -> None:
        """
        Engages magnet using Smart Grip feature.
        Only valid without fingers or with protective pads, gripping
        with all four fingers. Cannot be used with Eyes Location app.

        Args:
            strength (int): target magnet strength 0-100%.
        """
        strength = max(0, min(100, int(strength)))
        self._write_register(REG_STRENGTH, strength)
        self._write_register(REG_CONTROL, CMD_SMART_GRIP)

    def release(self) -> None:
        """
        Disengages the magnet and releases the workpiece.
        Allow ~300ms for brake activation to complete.
        """
        self._write_register(REG_CONTROL, CMD_DISENGAGE)

    def stop(self) -> None:
        """Alias for release()."""
        self.release()

    def auto_calibrate(self) -> None:
        """
        Runs auto-calibration sequence.
        Disengage magnet before calling. During calibration, status
        register busy bit and error register noHallCalibration bit go high.
        Disengage after calibration completes.
        """
        self._write_register(REG_CONTROL, CMD_AUTO_CALIBRATE)

    def set_finger_type(self, finger_type: int = FINGER_NO_PADS) -> None:
        """
        Sets the finger type configuration.

        Args:
            finger_type (int): FINGER_NO_PADS (1), FINGER_PROT_PADS (2), FINGER_CUSTOM (3)
        """
        self._write_register(REG_FINGER_TYPE, finger_type)

    def set_finger_height(self, height_mm: float = 0.0) -> None:
        """
        Sets the finger height in mm (resolution 0.1mm).
        No pads: 0mm, Protective pads: 0.5mm, Custom: user defined.

        Args:
            height_mm (float): finger height in mm.
        """
        self._write_register(REG_FINGER_HEIGHT, int(height_mm * 10))

    def get_finger_height(self) -> float:
        """Returns current finger height in mm."""
        return self._read_register(REG_FINGER_HEIGHT) / 10.0

    def get_finger_type(self) -> int:
        """Returns current finger type register value."""
        return self._read_register(REG_FINGER_TYPE)
