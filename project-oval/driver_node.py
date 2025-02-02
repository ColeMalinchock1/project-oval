#!/usr/bin/env python
import rclpy
from rclpy.node import Node
from std_msgs.msg import Int64
import serial
import sys
import threading

MAX_MIN_THROTTLE = 20

class DriverNode(Node):
    def __init__(self):
        super().__init__("driver")
        self.throttle = 0
        self.steer = 0
        self.init_serial()
        self.create_subscription(Int64, '/xbox_controller/steer', self.steer_callback, 10)
        self.create_subscription(Int64, '/xbox_controller/throttle', self.throttle_callback, 10)

    def init_serial(self):
        try:
            self.ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1, write_timeout=1)
            print(f"Opened {self.ser.name}")
        except serial.SerialException as e:
            print(f"Error: {e}")
            sys.exit(1)

    def steer_callback(self, msg):
        self.steer = msg.data
        print(f"Steer: {self.steer}")

    def throttle_callback(self, msg):
        if (msg.data > MAX_MIN_THROTTLE):
            self.throttle = MAX_MIN_THROTTLE
        elif (msg.data < -MAX_MIN_THROTTLE):
            self.throttle = -MAX_MIN_THROTTLE
        else:
            self.throttle = msg.data

        print(f"Throttle: {self.throttle}")
    
    def converter(self, throttle, steer):

        steer_factor_left = 1
        steer_factor_right = 1

        if (steer > 0):
            steer_factor_right = steer / 100.0
        elif (steer < 0):
            steer_factor_left = abs(steer / 100.0)
        

        throttle_left = int((self.throttle + 100) * 4095 / 200 * steer_factor_left)
        throttle_right = int((self.throttle + 100) * 4095 / 200 * steer_factor_right)

        return throttle_left, throttle_right

    def send_speeds(self):
        
        throttle_left, throttle_right = self.converter(self.throttle, self.steer)

        try:
            data = f"{throttle_left},{throttle_right},{(throttle_left + throttle_right) & 0xFFFF}\n"
            self.ser.write(data.encode())
            print(f"Sent: {data.strip()}")
            return self.ser.readline().decode().strip() == "OK"
        except Exception as e:
            print(f"Error: {e}")
            return False

def main():
    rclpy.init()
    node = DriverNode()
    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()
    
    try:
        while rclpy.ok():
            node.send_speeds()
    except KeyboardInterrupt:
        node.ser.close()
    
    rclpy.shutdown()

if __name__ == '__main__':
    main()