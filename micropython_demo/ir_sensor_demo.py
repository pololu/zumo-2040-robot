# Demonstrates the five downward-looking infrared reflectace/line
# sensors on the Zumo robot.
#
# Press button A to calibrate the sensors.
#
# Press button C to switch between displaying calibrated and
# uncalibrated values.

from zumo_2040_robot import robot
import time

line_sensors = robot.LineSensors()
display = robot.Display()
last_update = 0
button_a = robot.ButtonA()
button_b = robot.ButtonB()
button_c = robot.ButtonC()

calibrate = 0
use_calibrated_read = False
ir_emitters_on = True

while True:
    # Start a background read; we'll time how long the
    # non-blocking part takes later.
    line_sensors.start_read(emitters_on = ir_emitters_on)

    # In a real program you could do slow things while
    # waiting for the sensors.
    time.sleep_ms(2)

    if use_calibrated_read and not calibrate:
        start = time.ticks_us()
        line = line_sensors.read_calibrated()
        stop = time.ticks_us()
    else:
        start = time.ticks_us()
        line = line_sensors.read()
        stop = time.ticks_us()

    if calibrate == 1:
        line_sensors.calibrate()

    if stop - last_update > 200000:
        last_update = stop

        display.fill_rect(0, 0, 128, 30, 0)

        if use_calibrated_read:
            display.text("Calibrated {}us".format(stop-start), 0, 0)
        else:
            display.text("Uncalib.   {}us".format(stop-start), 0, 0)
        if calibrate == 0:
            display.text('A: calibrate', 0, 10)
            if ir_emitters_on:
                display.text('B: down IR (on)', 0, 20)
            else:
                display.text('B: down IR (off)', 0, 20)
            display.text('C: switch mode', 0, 30)
        elif calibrate == 1:
            display.text('cal line sens...', 0, 10)
            display.text('A: stop', 0, 20)

    if button_a.check():
        last_update = 0 # force display refresh
        if calibrate == 0:
            calibrate = 1 # calibrate line sensors
        else:
            calibrate = 0

    if button_b.check():
        last_update = 0
        ir_emitters_on = not ir_emitters_on

    if button_c.check():
        last_update = 0
        use_calibrated_read = not use_calibrated_read

    # 64-40 = 24
    scale = 24/1023

    display.fill_rect(0, 40, 128, 24, 0)

    if button_b.is_long_pressed():
        break
    elif button_b.is_pressed():
        display.text("Hold B to exit", 0, 56)
    else:
        display.fill_rect(36, 64-int(line[0]*scale), 8, int(line[0]*scale), 1)
        display.fill_rect(48, 64-int(line[1]*scale), 8, int(line[1]*scale), 1)
        display.fill_rect(60, 64-int(line[2]*scale), 8, int(line[2]*scale), 1)
        display.fill_rect(72, 64-int(line[3]*scale), 8, int(line[3]*scale), 1)
        display.fill_rect(84, 64-int(line[4]*scale), 8, int(line[4]*scale), 1)

    display.show()
