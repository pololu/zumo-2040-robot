# This demo uses the accelerometer on the Zumo to detect whether it is on a
# slanted surface.  If it is on a slanted surface, then it uses the motors to
# face uphill.
#
# It also uses the encoders to avoid rolling down the surface.

from zumo_2040_robot import robot
import time

motors = robot.Motors()
encoders = robot.Encoders()
button_a = robot.ButtonA()
button_b = robot.ButtonB()
button_c = robot.ButtonC()
display = robot.Display()
yellow_led = robot.YellowLED()

display.fill(0)
display.text("Starting IMU...", 0, 0, 1)
display.show()
imu = robot.IMU()
imu.reset()
imu.enable_default()

standard_turn_speed = 2000
max_speed = standard_turn_speed * 1.5
ke = 15

drive_motors = False
ax = ay = 0
tilted = False

def constrain_speed(speed):
    if speed < -max_speed: return -max_speed
    if speed > max_speed: return max_speed
    return speed

def draw_text():
    display.fill(0)
    if drive_motors:
        display.text("A: Stop motors", 0, 0, 1)
    else:
        display.text("A: Start motors", 0, 0, 1)
    display.text("B: Exit", 0, 10)
    display.text(f"ax:", 0, 24, 1)
    display.text(f"ay:", 0, 32, 1)
    display.text(f"enc:", 0, 40, 1)

draw_text()
display.show()

while True:
    encoder_counts = sum(encoders.get_counts())

    # Read from the accelerometer.
    if imu.acc.data_ready():
        imu.acc.read()
        # Detect if the robot is tilted more than 5 degrees.
        ax = imu.acc.last_reading_g[0]
        ay = imu.acc.last_reading_g[1]
        tilted = ax * ax + ay * ay > 0.007596  # sin(5 deg)^2 = 0.007596

    # If the user presses button A, toggle whether the motors are on.
    if button_a.check() == True:
        while button_a.check() != False: pass  # wait for release
        drive_motors = not drive_motors
        if drive_motors: time.sleep_ms(250)
        draw_text()
        encoders.get_counts(reset=True)

    if button_b.check() == True:
        motors.off()
        break

    # Update the display.
    display.fill_rect(48, 24, 72, 24, 0)
    display.text(f"{ax:>9.3f}",           48, 24, 1)
    display.text(f"{ay:>9.3f}",           48, 32, 1)
    display.text(f"{encoder_counts:>5}",  48, 40, 1)
    display.show()

    if drive_motors:
        if tilted:
            if ax > 0 and abs(ay) < 0.1:
                turn_speed = 0  # Already facing uphill
            elif ay < 0:
                turn_speed = -standard_turn_speed
            else:
                turn_speed = standard_turn_speed
        else:
            turn_speed = 0

        # Avoid rolling downhill.
        forward_speed = constrain_speed(-encoder_counts * ke)

        left_speed = constrain_speed(forward_speed - turn_speed)
        right_speed = constrain_speed(forward_speed + turn_speed)
        motors.set_speeds(left_speed, right_speed)
    else:
        motors.off()

    yellow_led.value(drive_motors)

