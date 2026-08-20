#!/usr/bin/env python3
"""
GripperNodes.py
---------------
Generic ROS2 node for controlling any OnRobot gripper over Modbus TCP.

The node loads whichever gripper is specified in the config file at startup
and exposes a consistent ROS2 interface regardless of which gripper is attached.
This is the hardware-agnostic layer -- the robot arm talks to this node and
never needs to know which gripper model is physically connected.

Usage:
    source /opt/ros/jazzy/setup.bash
    python3 ros2_nodes/GripperNodes.py --ros-args \
        -p config_file:=config/3fg15.yaml \
        -p ip_address:=192.168.1.1

Published topics:
    /status  (std_msgs/String, 20Hz)  -- JSON-encoded gripper state

Services:
    /open   (std_srvs/Trigger) -- open or disengage gripper
    /close  (std_srvs/Trigger) -- close or engage gripper
    /stop   (std_srvs/Trigger) -- halt motion immediately
"""

import threading
import yaml
import importlib
import json

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from rclpy.executors import MultiThreadedExecutor
from std_msgs.msg import String
from std_srvs.srv import Trigger


def load_gripper_from_config(config_path: str, ip: str, port: int):
    """
    Dynamically load and instantiate a gripper driver from a YAML config file.

    The config file specifies which driver class to use (e.g. 'fg15.FG15'),
    the Modbus device ID (unit_id), and any gripper-specific constructor
    arguments (e.g. gripper_arg: 'rg6' for the RG class).

    This uses importlib so the node doesn't need to know about any specific
    gripper at import time -- it adapts entirely at runtime based on the config.

    Args:
        config_path (str): path to the gripper YAML config file
        ip (str): IP address of the OnRobot compute box
        port (int): Modbus TCP port (default 502)

    Returns:
        tuple: (gripper object, config dict)
    """
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Parse the driver field e.g. 'fg15.FG15' -> module='fg15', class='FG15'
    module_name, class_name = config['driver'].split('.')
    module = importlib.import_module(f'gripper_driver.{module_name}')
    cls = getattr(module, class_name)

    # Read unit_id from config -- defaults to 66 (primary Dual Quick Changer side)
    # Some grippers use 65 (e.g. SG, MG10) -- this must be set correctly in the config
    unit_id = config.get('unit_id', 66)

    # Some drivers (e.g. RG) need a model string argument to distinguish RG2 from RG6
    if 'gripper_arg' in config:
        return cls(gripper=config['gripper_arg'], ip=ip, port=port, unit_id=unit_id), config

    return cls(ip=ip, port=port, unit_id=unit_id), config


class GripperNode(Node):
    """
    Generic ROS2 gripper node.

    Loads any supported OnRobot gripper from a config file, publishes its
    status at 20Hz, and exposes open/close/stop services. The same node
    binary works for all gripper models -- only the config file changes.
    """

    def __init__(self):
        super().__init__('gripper_node')

        # ── Parameters ────────────────────────────────────────────────────
        # These can be overridden at launch with --ros-args -p name:=value
        self.declare_parameter('config_file', 'config/rg2.yaml')
        self.declare_parameter('ip_address', '192.168.1.1')
        self.declare_parameter('port', 502)
        self.declare_parameter('status_rate_hz', 20.0)

        config_file         = self.get_parameter('config_file').get_parameter_value().string_value
        ip                  = self.get_parameter('ip_address').get_parameter_value().string_value
        port                = int(self.get_parameter('port').get_parameter_value().integer_value)
        self.status_rate_hz = float(self.get_parameter('status_rate_hz').value)

        # ── Load gripper driver ───────────────────────────────────────────
        try:
            self.gripper, self.config = load_gripper_from_config(config_file, ip, port)
        except Exception as e:
            self.get_logger().fatal(f'Failed to init gripper: {e}')
            raise

        # ── Threading lock ────────────────────────────────────────────────
        # The status publisher runs on a timer thread; service callbacks run
        # on separate threads via MultiThreadedExecutor. Without this lock,
        # a status read and a command write could occur simultaneously over
        # the same Modbus TCP connection, corrupting both messages.
        self.lock = threading.Lock()

        # ── Status publisher ──────────────────────────────────────────────
        # RELIABLE: every message is guaranteed to be delivered
        # TRANSIENT_LOCAL: new subscribers receive the last published message
        # immediately on connection -- the arm always knows gripper state
        # even if it subscribes after the node starts
        qos = QoSProfile(depth=1)
        qos.reliability = ReliabilityPolicy.RELIABLE
        qos.durability  = DurabilityPolicy.TRANSIENT_LOCAL
        self.pub_status = self.create_publisher(String, 'status', qos)

        # ── Services ──────────────────────────────────────────────────────
        # Trigger services are request-response -- the arm sends a command
        # and gets success/failure confirmation back. Safer than a topic
        # (fire-and-forget) for actuator commands.
        self.create_service(Trigger, 'open',  self.handle_open)
        self.create_service(Trigger, 'close', self.handle_close)
        self.create_service(Trigger, 'stop',  self.handle_stop)

        # ── Status timer ──────────────────────────────────────────────────
        # Publish gripper status at status_rate_hz (default 20Hz = every 50ms)
        # Fast enough for the arm to react; slow enough not to flood Modbus
        period = 1.0 / max(1e-3, self.status_rate_hz)
        self.timer = self.create_timer(period, self.publish_status)

        self.get_logger().info(
            f'Gripper node up: {self.config["name"]} at {ip}:{port}'
        )

    def publish_status(self):
        """
        Read gripper status and publish as JSON to /status topic.
        Called by the timer at status_rate_hz. Uses the lock to prevent
        concurrent Modbus access with service callbacks.
        """
        try:
            with self.lock:
                status = self.gripper.get_status()
            msg = String()
            msg.data = json.dumps(status)
            self.pub_status.publish(msg)
        except Exception as e:
            self.get_logger().warn(f'Status read failed: {e}')

    def handle_open(self, req, res):
        """
        Service callback for /open.
        Opens the gripper or disengages magnet/vacuum for non-fingered types.
        Acquires the lock before writing to prevent concurrent Modbus access.
        """
        try:
            with self.lock:
                self.gripper.open_gripper()
            res.success = True
            res.message = 'opening'
        except Exception as e:
            res.success = False
            res.message = str(e)
        return res

    def handle_close(self, req, res):
        """
        Service callback for /close.
        Closes the gripper or engages magnet/vacuum for non-fingered types.
        """
        try:
            with self.lock:
                self.gripper.close_gripper()
            res.success = True
            res.message = 'closing'
        except Exception as e:
            res.success = False
            res.message = str(e)
        return res

    def handle_stop(self, req, res):
        """
        Service callback for /stop.
        Halts all gripper motion immediately. Safe to call at any time.
        """
        try:
            with self.lock:
                self.gripper.stop()
            res.success = True
            res.message = 'stopped'
        except Exception as e:
            res.success = False
            res.message = str(e)
        return res


def main():
    rclpy.init()
    node = GripperNode()

    # MultiThreadedExecutor allows service callbacks and the timer to run
    # concurrently on separate threads -- the threading.Lock in the node
    # ensures Modbus access remains safe
    executor = MultiThreadedExecutor()
    executor.add_node(node)

    try:
        executor.spin()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
