#!/usr/bin/env python3

"""
MIT License

Copyright (c) 2023 Matthew Lock

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

# Interface between Joy messages and the smarc_joy_controller for the Xbox controller

import rospy

from std_msgs.msg import Bool
from sensor_msgs.msg import Joy
from smarc_joy_msgs.msg import JoyButtons

import threading

from evdev import ecodes
from evdev import InputDevice
from evdev import ff
from evdev import util

import time

class xbox_joy():

    def __init__(self):

        rospy.init_node('ds5_teleop', anonymous=True)
        rate = rospy.Rate(1) # 10hz

        self.button_pressed_flag = threading.Event()
        self.enable_teleop_pressed = False
        self.teleop_enabled = False

        self.teleop_enabled_pub = rospy.Publisher('ctrl/teleop/enable', Bool, queue_size=1)
        self.joy_btn_pub = rospy.Publisher('ctrl/joy_buttons', JoyButtons, queue_size=1)
        self.joy_sub = rospy.Subscriber('joy', Joy, self.joy_callback)

        rospy.loginfo("[XBOX CONTROLLER] Starting Xbox controller node")

        # CONTROLER SETUP
        self.device_file = None
        for name in util.list_devices():
            self.device_file = InputDevice(name)
            if ecodes.EV_FF in self.device_file.capabilities():
                break
        if self.device_file is None:
            rospy.logerr_once("[XBOX CONTROLLER] Sorry, no FF capable device found")

        self.load_effects()

        while not rospy.is_shutdown():
            self.send_teleop_enabled(self.teleop_enabled)
            rate.sleep()  

    def load_effects(self):
        """
        Load the effects for the controller
        Taken from https://github.com/atar-axis/xpadneo/blob/master/misc/examples/python_asyncio_evdev/gamepad.py
        """
        # effect 1, light rumble
        rumble = ff.Rumble(strong_magnitude=0xc000, weak_magnitude=0x500)
        duration_ms = 300
        effect = ff.Effect(ecodes.FF_RUMBLE, -1, 0, ff.Trigger(0, 0), ff.Replay(duration_ms, 0), ff.EffectType(ff_rumble_effect=rumble))
        effect = ff.Effect(ecodes.FF_RUMBLE, -1, 0, ff.Trigger(0, 0), ff.Replay(duration_ms, 0), ff.EffectType(ff_rumble_effect=rumble))
        self.effect1_id = self.device_file.upload_effect(effect)
        # effect 2, strong rumble
        rumble = ff.Rumble(strong_magnitude=0xc000, weak_magnitude=0x0000)
        duration_ms = 200
        effect = ff.Effect(ecodes.FF_RUMBLE, -1, 0, ff.Trigger(0, 0), ff.Replay(duration_ms, 0), ff.EffectType(ff_rumble_effect=rumble))
        self.effect2_id = self.device_file.upload_effect(effect)

    # ================================================================================
    # Callbacks
    # ================================================================================

    def joy_callback(self, msg:Joy):
        """
        Callback function for the joystick subscriber
        """

        teleop_btn_pressed = msg.buttons[0] == 1

        if teleop_btn_pressed and not self.enable_teleop_pressed:
            self.teleop_enabled = not self.teleop_enabled
            self.enable_teleop_pressed = True
            rospy.loginfo("[XBOX CONTROLLER] Teleop enabled: {}".format(self.teleop_enabled))

            if self.teleop_enabled:
                # Only rumble if teleop is enabled
                self.rumble(1)
            else:
                # Two rumbles if teleop is disabled
                self.rumble(2)

        if not teleop_btn_pressed:
            self.enable_teleop_pressed = False
            
        joy_buttons_msg = JoyButtons()
        joy_buttons_msg.left_x = msg.axes[0]
        joy_buttons_msg.left_y = msg.axes[1]
        joy_buttons_msg.right_x = msg.axes[3]
        joy_buttons_msg.right_y = msg.axes[4]

        joy_buttons_msg.teleop_enable = self.teleop_enabled

        self.joy_btn_pub.publish(joy_buttons_msg)

    # ================================================================================
    # Publish Functions
    # ================================================================================

    def send_teleop_enabled(self, teleop_enabled: bool):
        """
        Send a teleop enabled message to the core
        """
        
        teleop_enabled_msg = Bool()
        teleop_enabled_msg.data = teleop_enabled
        self.teleop_enabled_pub.publish(teleop_enabled_msg)

    # ================================================================================
    # Controller Function
    # ================================================================================

    def rumble(self, no_pulses = 1):
        """
        Set the rumble motors on the controller
        
        Parameters
        ----------
        left_motor : int
            Left motor speed between 0 and 255
        right_motor : int
            Right motor speed between 0 and 255
        """

        repeat_count = no_pulses
        self.device_file.write(ecodes.EV_FF, self.effect1_id, repeat_count)

if __name__ == '__main__':
    try:
        xbox_joy()
    except rospy.ROSInterruptException:
        pass