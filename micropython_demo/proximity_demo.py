from zumo_2040_robot import robot
import time
import math
from array import array

proximity_sensors = robot.ProximitySensors()
display = robot.Display()
button_b = robot.ButtonB()
count = 0

while not button_b.check():
    start = time.ticks_us()
    proximity_sensors.read()
    stop = time.ticks_us()

    display.fill(0)
    display.text("{:.1f}ms".format(time.ticks_diff(stop, start) / 1000), 0, 0)
    display.text("<B", 112, 0)
    count = 0

    readings = [
        proximity_sensors.left_counts_with_left_leds(),
        proximity_sensors.left_counts_with_right_leds(),
        0,
        proximity_sensors.front_counts_with_left_leds(),
        proximity_sensors.front_counts_with_right_leds(),
        0,
        proximity_sensors.right_counts_with_left_leds(),
        proximity_sensors.right_counts_with_right_leds(),
    ]

    if proximity_sensors.total_counts() > 0:
        angle_estimate = proximity_sensors.angle_estimate()
        display.text(str(angle_estimate), 0, 10)

        dx = round(25 * math.sin(angle_estimate * math.pi / 180))
        dy = round(-25 * math.cos(angle_estimate * math.pi / 180))
        dx2 = round(4 * math.sin((angle_estimate + 90) * math.pi / 180))
        dy2 = round(-4 * math.cos((angle_estimate + 90) * math.pi / 180))
        display.poly(64, 32,
                     array('h', [dx2, dy2, dx, dy, -dx2, -dy2]), 1, 1)

    # 64-40 = 24
    scale = 24/6

    for i, reading in enumerate(readings):
        display.fill_rect(18+i*12, 64-int(reading*scale), 8, int(reading*scale), 1)

    display.show()
