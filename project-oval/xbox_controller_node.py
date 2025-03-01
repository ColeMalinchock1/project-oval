#!/usr/bin/env python
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from std_msgs.msg import Int64, Bool
import threading
import curses
import time

stdscr = curses.initscr()

# Throttle max and min
MAX_MANUAL_THROTTLE_FORWARD = 100
MAX_MANUAL_THROTTLE_REVERSE = 100

# Steering should be bounded between [-100, +100]
manual = True
steering = 0
throttle = 0
switch_time = time.time()

def joy_callback(data):
	global steering, throttle, manual, switch_time

	# Check for toggle between manual and auto driving (A Button)
	if(data.buttons[0] == 1 and time.time() - switch_time > 0.1):
		manual = not manual
		switch_time = time.time()
	# Input for throttle and steering are between [-1.0, 1.0]
	throttle_input = data.axes[1]
	steering_input = data.axes[2]

	# Convert this to [-20, +20] for throttle and [-100, 100] for steering
	throttle = int(100 * throttle_input)
	if throttle > MAX_MANUAL_THROTTLE_FORWARD:
		throttle = MAX_MANUAL_THROTTLE_FORWARD
	elif throttle < (-1 * MAX_MANUAL_THROTTLE_REVERSE):
		throttle = (-1 * MAX_MANUAL_THROTTLE_REVERSE)
	
	steering = int(-100 * steering_input)


def main(args=None):

	rclpy.init(args=args)
	node = Node("xbox_controller_node")

	# Subscription to joy topic - gets info from controller
	joy_sub = node.create_subscription(Joy, "joy", joy_callback, 5)
	# Publishers to manual throttle and steering - publishes bounded number pre-PWM
	manual_throttle_pub = node.create_publisher(Int64, "manual_throttle", 10)
	manual_steering_pub = node.create_publisher(Int64, "manual_steer", 10)
	mode_pub = node.create_publisher(Bool, "/xbox_controller/mode", 10)

	thread = threading.Thread(target=rclpy.spin, args=(node, ), daemon=True)
	thread.start()

	rate = node.create_rate(20, node.get_clock())
        
	while rclpy.ok():

		try:
			# If we're in manual mode, we send the actuation
			if(manual):
				send_data = Bool()
				send_data.data = True
				mode_pub.publish(send_data)
				# Publishing for actuation
				manual_throttle_msg = Int64()
				manual_throttle_msg.data = throttle
				manual_throttle_pub.publish(manual_throttle_msg)

				manual_steering_msg = Int64()
				manual_steering_msg.data = steering
				manual_steering_pub.publish(manual_steering_msg)
			else:
				send_data = Bool()
				send_data.data = False
				mode_pub.publish(send_data)
			
			stdscr.refresh()
			stdscr.addstr(1, 25, 'Xbox Controller       ')
			stdscr.addstr(2, 25, 'Throttle: %.2f  ' % throttle)
			stdscr.addstr(3, 25, 'Steering: %.2f  ' % steering)
			stdscr.addstr(4, 25, 'Manual: %s  ' % str(manual))
			rate.sleep()
		except KeyboardInterrupt:
			curses.endwin()
			print("Ctrl+C captured, ending...")
			break
	
	rclpy.shutdown()

if __name__ == '__main__':
	main()
