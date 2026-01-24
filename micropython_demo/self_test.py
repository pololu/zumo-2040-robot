import gc
import machine
from machine import Pin
import sys
import time
from zumo_2040_robot import robot

battery = robot.Battery()
button_a = robot.ButtonA()
button_b = robot.ButtonB()
button_c = robot.ButtonC()
buzzer = robot.Buzzer()
display = robot.Display()
encoders = robot.Encoders()
motors = robot.Motors()
rgb_leds = robot.RGBLEDs()

# initialize these later after testing front pins:
imu = None
line_sensors = None
proximity_sensors = None

BEEP_WELCOME = '!>g32>>c32'
BEEP_FAIL = '<g-8r8<g-8r8<g-8'
BEEP_PASS = '>l32c>e>g>>c8'

YELLOW = [255, 64, 0]
GREEN = [0, 255, 0]

def display_line_break(lines=1, show=True):
    display.scroll(0, -8 * lines)
    display.fill_rect(0, 64 - 8 * lines, 128, 8 * lines, 0)
    if show: display.show()

def display_centered_text(text, y=56, show=True):
    display.text(text, (128 - len(text) * 8) // 2, y)
    if show: display.show()

# Custom exception for test errors
class TestError(Exception):
    pass

def show_test_error(test_error):
    sys.print_exception(test_error)

    display_line_break()
    display_centered_text('FAIL')
    display.show()

    for i in range(6):
        rgb_leds.set(i, [255, 0, 0])
    rgb_leds.show()

    buzzer.play_in_background(BEEP_FAIL)

IO_BANK0_BASE = const(0x40014000)

# reads a bit from GPIOx_STATUS register
def gpio_status_helper(pin, bit):
    if pin > 29: raise ValueError('invalid pin')
    return bool(machine.mem32[IO_BANK0_BASE + 8 * pin] >> bit & 1)

# reads GPIOx_STATUS.OETOPAD
def pin_is_output(pin):
    return gpio_status_helper(pin, 13)

# reads GPIOx_STATUS.OETOPAD
def pin_output_is_high(pin):
    # GPIOx_STATUS.OUTTOPAD
    return gpio_status_helper(pin, 9)

# Computes the expected state of a pin, considering whether and how it's driving
# and a given default state otherwise (usually determined by a pull-up or
# pull-down). If the pin is None, the expected state is the same as the default
# state. The default state can be None, which represents an indeterminate state
# when not being driven (e.g. encoder pins, which can be driven low but
# otherwise might be either high or low depending on the encoder position)
def expected_state(pin, default_state):
    if pin is None:
        return default_state
    else:
        return pin_output_is_high(pin) if pin_is_output(pin) else default_state

def check_input(pin, default_state):
    expected = expected_state(pin, default_state)
    actual = Pin(pin).value()

    if expected is not None and expected != actual:
        print(Pin(pin))
        raise TestError(f"GP{pin}: expected {int(expected)}, got {int(actual)}")

def check_front_inputs():
    check_input(4, True) # GP4: SDA; pulled up by IMU circuit
    check_input(5, True) # GP5: SCL; pulled up by IMU circuit
    check_input(16, False) # GP16: right prox LED ctrl; pulled down
    check_input(17, False) # GP17: left prox LED ctrl; pulled down
    check_input(18, False) # GP18: down sensor 5 (R); pulled down
    check_input(19, False) # GP19: down sensor 4; pulled down
    check_input(20, False) # GP20: down sensor 3; pulled down
    check_input(21, False) # GP21: down sensor 2; pulled down
    check_input(22, False) # GP22: down sensor 1 (L); pulled down
    # GP23: driven by left prox sensor; unknown state
    # GP24: driven by right prox sensor; unknown state
    check_input(26, False) # GP26: down IR LED control & BATLEV divider
    # GP24: driven by front prox sensor; unknown state
    check_input(28, False) # GP28: free; internal pull-down enabled
    check_input(29, False) # GP29: free; internal pull-down enabled

def check_driving_high_and_low(pin):
    p = Pin(pin, mode=Pin.OUT, value=1)
    check_front_inputs()
    p.value(0)
    check_front_inputs()
    p.init(mode=Pin.IN)

def test_front_pins():
    Pin(28, mode=Pin.IN, pull=Pin.PULL_DOWN)
    Pin(29, mode=Pin.IN, pull=Pin.PULL_DOWN)
    time.sleep_ms(1)

    check_front_inputs()

    for i in [4, 5, 16, 17, 18, 19, 20, 21, 22, 26, 28, 29]:
        check_driving_high_and_low(i)

def test_proximity_sensors():
    proximity_sensors = robot.ProximitySensors()

    display.text('Left Front Right', 0, 40)
    display.text('Far   Far   Far ', 0, 48)
    display.text('Near  Near  Near', 0, 56)
    display.show()
    tested = 0

    count_funcs = [
        proximity_sensors.left_counts_with_left_leds,
        proximity_sensors.front_counts_with_left_leds,
        proximity_sensors.right_counts_with_right_leds]
    notes = ['c', 'd', 'e']

    while True:
        proximity_sensors.read()

        for i in range(3):
            if not tested & (1 << i*2) and count_funcs[i]() >= 5:
                tested |= (1 << i*2)
                display.fill_rect(48*i, 56, 32, 8, 1)
                display.text('Near', 48*i, 56, 0)
                display.show()
                buzzer.play_in_background(f">{notes[i]}32")
            if not tested & (1 << i*2+1) and count_funcs[i]() <= 1:
                tested |= (1 << i*2+1)
                display.fill_rect(48*i, 48, 32, 8, 1)
                display.text('Far', 48*i, 48, 0)
                display.show()
                buzzer.play_in_background(f"{notes[i]}32")

        if tested == 0b111111:
            return

def test_line_sensors():
    line_sensors = robot.LineSensors()

    line = line_sensors.read()

    for i in range(5):
        if line[i] > 900:
            display_line_break()
            display_centered_text(f"Emitters on:")
            for j in range(5):
                display_line_break()
                display_centered_text(f"{j}: {line[j]}")
            print(line)
            raise TestError(f"Line sensor {i} (emitters on): expected <= 900, read {line[i]}")

    line_sensors.start_read(emitters_on=False)
    line = line_sensors.read()

    for i in range(5):
        if line[i] < 900:
            display_line_break()
            display_centered_text(f"Emitters off:")
            for j in range(5):
                display_line_break()
                display_centered_text(f"{j}: {line[j]}")
            print(line)
            raise TestError(f"Line sensor {i} (emitters off): expected >= 900, read {line[i]}")

def run_test():
    rgb_leds.set_brightness(2)
    display.fill(0)

    buzzer.play_in_background(BEEP_WELCOME)

    display_centered_text('Zumo 2040')
    display_line_break()
    display_centered_text('Self Test')
    time.sleep_ms(500)

    display_line_break(2)
    v = battery.get_level_millivolts()

    if v < 4000:
        display_centered_text('Power on &')
        display_line_break()
        display_centered_text('unplug USB')
        while v < 4000:
            time.sleep_ms(100)
            v = battery.get_level_millivolts()
        display_line_break(2)

    display_centered_text(f"VBAT {v:4} mV")
    if v > 7000:
        raise TestError(f"VBAT higher than expected: {v} mV")
    time.sleep_ms(250)

    display_line_break(2)
    display_centered_text('Front pins   ')
    test_front_pins()
    display_centered_text('           OK')
    rgb_leds.set(5, YELLOW) # F
    rgb_leds.show()
    time.sleep_ms(250)

    display_line_break(2)
    display_centered_text('Proximity')
    display_line_break(3)
    test_proximity_sensors()
    display_line_break()
    display_centered_text('OK')
    rgb_leds.set(4, YELLOW) # E
    rgb_leds.show()
    time.sleep_ms(250)

    display_line_break(2)
    display_centered_text('Set on surface.')
    display_line_break()
    display_centered_text('Gear ratio?')
    display_line_break()
    display_centered_text('A: 50:1 ')
    display_line_break()
    display_centered_text('B: 75:1 ')
    display_line_break()
    display_centered_text('C: 100:1')
    rgb_leds.set(3, YELLOW) # D
    rgb_leds.show()
    buzzer.play_in_background('<g32')

    # Make sure button was not held down from before (look for released-to-
    # pressed transition)
    button_a.check()
    button_b.check()
    button_c.check()
    time.sleep_ms(10)
    while True:
        if button_a.check():
            gear_ratio = 50
            display.fill_rect(0, 48, 128, 16, 0)
            buzzer.play_in_background('c32')
            break
        elif button_b.check():
            gear_ratio = 75
            display.fill_rect(0, 40, 128, 8, 0)
            display.fill_rect(0, 56, 128, 8, 0)
            buzzer.play_in_background('e32')
            break
        elif button_c.check():
            gear_ratio = 100
            display.fill_rect(0, 40, 128, 16, 0)
            buzzer.play_in_background('g32')
            break
    display.show()
    time.sleep_ms(500)

    display_line_break(2)
    display_centered_text('Line sensors   ')
    test_line_sensors()
    display_centered_text('             OK')
    rgb_leds.set(0, YELLOW) # A
    rgb_leds.show()
    time.sleep_ms(250)

    # test IMU presence
    display_line_break(2)
    display_centered_text('IMU   ')
    imu = robot.IMU()
    imu.reset()
    if not imu.detect():
        raise TestError('IMU not detected')
    display_centered_text('    OK')
    rgb_leds.set(1, YELLOW) # B
    rgb_leds.show()
    time.sleep_ms(250)
    imu.enable_default()
    imu.acc.set_output_data_rate(1666)
    imu.acc.set_full_scale(4)

    while True:
        try:
            display_line_break(2)
            display_centered_text('Motors')

            # Calibrate accelerometer: find steady-state offset to subtract from
            # subsequent readings, helping to account for inclined surfaces
            OFFSET_SAMPLES = const(50)
            acc_offset = 0
            for _ in range(OFFSET_SAMPLES):
                imu.acc.read()
                acc_offset += imu.acc.last_reading_g[0]
            acc_offset /= OFFSET_SAMPLES

            dist = 0
            speed = 0
            left, right = 0, 0

            # Force garbage collection before starting to avoid needing to do it
            # while reading the accelerometer.
            gc.collect()

            encoders.get_counts(reset=True)
            motors.set_speeds(2000, 2000)
            start = time.ticks_us()
            prev = start
            max_delta_t = 0

            # Encoders are 12 counts/revolution of the motor shaft; sprockets
            # have 12 teeth and tracks have 48 mm or 5 teeth between axles.
            #
            # Drive forward 438 encoder counts per side. This corresponds to:
            # 84 mm on a 50:1 Zumo
            # 56 mm on a 75:1 Zumo
            # 42 mm on a 100:1 Zumo
            #
            # 42 mm / (12 teeth/rev * 48 mm / 5 teeth)
            #   * 100 (gear ratio) * 12 CPR = 438 counts
            while (left + right) < 876:
                left, right = encoders.get_counts()
                imu.acc.read()

                now = time.ticks_us()
                delta_t_us = time.ticks_diff(now, prev)
                if delta_t_us > max_delta_t: max_delta_t = delta_t_us

                acc = imu.acc.last_reading_g[0]
                if abs(acc) > 3.9:
                    motors.set_speeds(0, 0)
                    display_line_break()
                    display_centered_text(f"Acc sat: {acc:.2f}")
                    raise TestError(f"Acc saturated: {acc:.2f}")

                acc -= acc_offset # in g
                speed += acc * delta_t_us # in g*us
                dist += speed * delta_t_us # in g*us^2

                prev = now

                if time.ticks_diff(now, start) > 2e6: # 2 seconds
                    motors.set_speeds(0, 0)
                    display_line_break()
                    display_centered_text(f"L={left} R={right}")
                    raise TestError(f"Timed out trying to drive forward: L={left} R={right}")

            motors.set_speeds(0, 0)

            dist /= (1e9 / 9.81) # convert from g*us^2 to mm (1 g = 9.81 m/s^2)

            # Warn if max delta t recorded was higher than expected
            if max_delta_t > 2000:
                display_line_break()
                display_centered_text(f"dt warn: {max_delta_t}")

            display_line_break(2)
            display_centered_text(f"L={left} R={right}")
            display_line_break()
            display_centered_text(f"dist={dist:.1f}")
            display_line_break(2)
            display_centered_text(f"{gear_ratio}:1:")

            # Distance measured should be within 14.3% (1/7) of the expected
            # value (this is the most tolerant we can be without allowing the
            # ranges to overlap). Encoder counts should be within 15% of the
            # expected 438.
            COUNTS_MIN = const(372)
            COUNTS_MAX = const(504)

            if gear_ratio == 50 and dist > 72 and dist < 96 and \
                    left > COUNTS_MIN and left < COUNTS_MAX and right > COUNTS_MIN and right < COUNTS_MAX:
                break
            elif gear_ratio == 75 and dist > 48 and dist < 64 and \
                    left > COUNTS_MIN and left < COUNTS_MAX and right > COUNTS_MIN and right < COUNTS_MAX:
                break
            elif gear_ratio == 100 and dist > 36 and dist < 48 and \
                    left > COUNTS_MIN and left < COUNTS_MAX and right > COUNTS_MIN and right < COUNTS_MAX:
                break
            else:
                raise TestError(f"Gear ratio mismatch: expected {gear_ratio}:1, measured L={left} R={right} dist={dist:.1f}")

        except TestError as te:
            show_test_error(te)
            display_line_break()

            display_centered_text('Any btn to retry')
            while True:
                if button_a.check() or button_b.check() or button_c.check():
                    break

            rgb_leds.off()
            buzzer.play_in_background('<g32')
            time.sleep_ms(1000)

    display_line_break()
    display_centered_text('      PASS    <B')
    for i in range(6):
        rgb_leds.set(i, GREEN)
    rgb_leds.show()
    buzzer.play_in_background(BEEP_PASS)
    while not button_b.check():
        machine.idle()

try:
    run_test()
except TestError as te:
    show_test_error(te)
    while not button_b.check():
        machine.idle()

rgb_leds.off()