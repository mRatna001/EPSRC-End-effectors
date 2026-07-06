#!/usr/bin/env python3

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
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    module_name, class_name = config['driver'].split('.')
    module = importlib.import_module(f'gripper_driver.{module_name}')
    cls = getattr(module, class_name)
    if 'gripper_arg' in config:
        return cls(gripper=config['gripper_arg'], ip=ip, port=port), config
    return cls(ip=ip, port=port), config


class GripperNode(Node):

    def __init__(self):
        super().__init__('gripper_node')

        self.declare_parameter('config_file', 'config/rg2.yaml')
        self.declare_parameter('ip_address', '192.168.1.1')
        self.declare_parameter('port', 502)
        self.declare_parameter('status_rate_hz', 20.0)

        config_file = self.get_parameter('config_file').get_parameter_value().string_value
        ip = self.get_parameter('ip_address').get_parameter_value().string_value
        port = int(self.get_parameter('port').get_parameter_value().integer_value)
        self.status_rate_hz = float(self.get_parameter('status_rate_hz').value)

        try:
            self.gripper, self.config = load_gripper_from_config(config_file, ip, port)
        except Exception as e:
            self.get_logger().fatal(f'Failed to init gripper: {e}')
            raise

        self.lock = threading.Lock()

        qos = QoSProfile(depth=1)
        qos.reliability = ReliabilityPolicy.RELIABLE
        qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self.pub_status = self.create_publisher(String, 'status', qos)

        self.create_service(Trigger, 'open',  self.handle_open)
        self.create_service(Trigger, 'close', self.handle_close)
        self.create_service(Trigger, 'stop',  self.handle_stop)

        period = 1.0 / max(1e-3, self.status_rate_hz)
        self.timer = self.create_timer(period, self.publish_status)

        self.get_logger().info(
            f'Gripper node up: {self.config["name"]} at {ip}:{port}'
        )

    def publish_status(self):
        try:
            with self.lock:
                status = self.gripper.get_status()
            msg = String()
            msg.data = json.dumps(status)
            self.pub_status.publish(msg)
        except Exception as e:
            self.get_logger().warn(f'Status read failed: {e}')

    def handle_open(self, req, res):
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
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()