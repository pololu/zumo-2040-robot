# This example uses the proximity sensors on the Zumo 2040's Front Sensor Array
# to locate an opponent robot or any other reflective object. Using the motors
# to turn, it scans its surroundings. If it senses an object, it turns on its
# RGB LEDs and attempts to face towards that object.

from zumo_2040_robot import robot
import time

motors = robot.Motors()
proximity_sensors = robot.ProximitySensors()
button_a = robot.ButtonA()
button_b = robot.ButtonB()
display = robot.Display()
rgb_leds = robot.RGBLEDs()
rgb_leds.set_brightness(2)

# A sensors reading must be greater than or equal to this threshold in order for
# the program to consider that sensor as seeing an object.
SENSOR_THRESHOLD = const(1)

# The maximum speed to drive the motors while turning.  6000 is full speed.
TURN_SPEED_MAX = const(6000)

# The minimum speed to drive the motors while turning.  6000 is full speed.
TURN_SPEED_MIN = const(1500)

# The amount to decrease the motor speed by during each cycle when an object is
# seen.
DECELERATION = const(150)

# The amount to increase the speed by during each cycle when an object is not
# seen.
ACCELERATION = const(150)

DIR_LEFT = const(0)
DIR_RIGHT = const(1)

# Stores the last indication from the sensors about what direction to turn to
# face the object.  When no object is seen, this variable helps us make a good
# guess about which direction to turn.
sense_dir = DIR_RIGHT

# True if the robot is turning left (counter-clockwise).
turning_left = False

# True if the robot is turning right (clockwise).
turning_right = False

# If the robot is turning, this is the speed it will use.
turn_speed = TURN_SPEED_MAX

drive_motors = False

# 64 display height - 40 bar top = 24 bar height
# / 6 max proximity reading = 4 scale factor
BAR_SCALE = const(4)

RGB_OFF = (0, 0, 0)
RGB_GREEN = (0, 255, 0)
RGB_YELLOW = (255, 64, 0)
RGB_RED = (255, 0, 0)

def turn_right():
    global turning_left, turning_right
    motors.set_speeds(turn_speed, -turn_speed)
    turning_left = False
    turning_right = True

def turn_left():
    global turning_left, turning_right
    motors.set_speeds(-turn_speed, turn_speed)
    turning_left = True
    turning_right = False

def stop():
    global turning_left, turning_right
    motors.set_speeds(0, 0)
    turning_left = False
    turning_right = False

def draw_text():
    display.fill(0)
    if drive_motors:
        display.text("A: Stop motors", 0, 0, 1)
    else:
        display.text("A: Start motors", 0, 0, 1)
    display.text("B: Exit", 0, 10)

def set_front_rgb_leds(front_left, front, front_right):
    rgb_leds.set(5, front_left)
    rgb_leds.set(4, front)
    rgb_leds.set(3, front_right)
    rgb_leds.show()

draw_text()
display.show()

while True:
    # Read the proximity sensors.
    proximity_sensors.read()
    reading_left = proximity_sensors.left_counts_with_left_leds()
    reading_front_left = proximity_sensors.front_counts_with_left_leds()
    reading_front_right = proximity_sensors.front_counts_with_right_leds()
    reading_right = proximity_sensors.right_counts_with_right_leds()

    # If the user presses button A, toggle whether the motors are on.
    if button_a.check() == True:
        while button_a.check() != False: pass  # wait for release
        drive_motors = not drive_motors
        if drive_motors:
            time.sleep_ms(250)
        else:
            stop()
        draw_text()

    if button_b.check() == True:
        stop()
        break

    # Update the display.
    display.fill_rect(0, 24, 48, 8, 0)
    if drive_motors:
        display.text('R' if turning_right else 'L' if turning_left else ' ', 0, 24)
        display.text(str(turn_speed), 16, 24)
    display.fill_rect(18, 40, 92, 24, 0)
    display.fill_rect( 18, 64-int(reading_left       *BAR_SCALE), 8, int(reading_left       *BAR_SCALE), 1)
    display.fill_rect( 54, 64-int(reading_front_left *BAR_SCALE), 8, int(reading_front_left *BAR_SCALE), 1)
    display.fill_rect( 66, 64-int(reading_front_right*BAR_SCALE), 8, int(reading_front_right*BAR_SCALE), 1)
    display.fill_rect(102, 64-int(reading_right      *BAR_SCALE), 8, int(reading_right      *BAR_SCALE), 1)
    display.show()

    # Determine if an object is visible or not.
    object_seen = any(reading > SENSOR_THRESHOLD for reading in \
        (reading_left, reading_front_left, reading_front_right, reading_right))

    if object_seen:
        # An object is visible, so we will start decelerating in order to help
        # the robot find the object without overshooting or oscillating.
        turn_speed -= DECELERATION
    else:
        # An object is not visible, so we will accelerate in order to help find the
        # object sooner.
        turn_speed += ACCELERATION


    # Constrain the turn speed so it is between TURN_SPEED_MIN and
    # TURN_SPEED_MAX.
    turn_speed = min(TURN_SPEED_MAX, max(TURN_SPEED_MIN, turn_speed))

    if object_seen:
        if max(reading_left, reading_front_left) < max(reading_right, reading_front_right):
            # The larger of the right values is greater, so the object is
            # probably closer to the robot's right LEDs, which means the robot
            # is not facing it directly.  Turn to the right to try to make it
            # more even.
            if drive_motors: turn_right()
            sense_dir = DIR_RIGHT
            set_front_rgb_leds(RGB_OFF, RGB_OFF, RGB_YELLOW)

        elif max(reading_left, reading_front_left) > max(reading_right, reading_front_right):
            # The larger of the left values is greater, so turn to the left.
            if drive_motors: turn_left()
            sense_dir = DIR_LEFT
            set_front_rgb_leds(RGB_YELLOW, RGB_OFF, RGB_OFF)

        else:
            # The values are equal, so stop the motors.
            stop()
            set_front_rgb_leds(RGB_OFF, RGB_GREEN, RGB_OFF)

    else:
        # No object is seen, so just keep turning in the direction that we last
        # sensed the object.
        if sense_dir == DIR_RIGHT:
            if drive_motors: turn_right()
            set_front_rgb_leds(RGB_OFF, RGB_OFF, RGB_RED)

        else:
            if drive_motors: turn_left()
            set_front_rgb_leds(RGB_RED, RGB_OFF, RGB_OFF)
