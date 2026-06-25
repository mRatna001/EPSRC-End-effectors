#!/usr/bin/env python3

import threading
import yaml
import importlib
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from rclpy.executors import MultiThreadedExecutor

class GripperNode(Node):
    def __init__(self):
        super().__init__('gripper_node')