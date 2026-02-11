from array import array
from machine import Pin, PWM
from time import sleep_us

DEFAULT_FREQ = const(56000)
DEFAULT_BRIGHTNESS_LEVELS = [313, 1000, 2063, 3500, 5375, 7563]

class IRPulses:
    def __init__(self):
        self.left_pulses_pin = Pin(17, Pin.OUT, value=0)
        self.right_pulses_pin = Pin(16, Pin.OUT, value=0)
        self.left_pulses_pwm = PWM(self.left_pulses_pin, freq=DEFAULT_FREQ, duty_ns=0)
        self.right_pulses_pwm = PWM(self.right_pulses_pin, freq=DEFAULT_FREQ, duty_ns=0)

    def set_frequency(self, freq):
        # Normally, only one of the below calls should be necessary since the
        # default pins are on the same PWM slice (16 and 17 = 0A and 0B), but
        # we'll go ahead and do both in case different pins are in use.
        self.left_pulses_pwm.freq(freq)
        self.right_pulses_pwm.freq(freq)

        # TODO: limit or reset duty cycle (brightness) if out of range?

    def set_brightnesses(self, left, right):
        self.left_pulses_pwm.duty_ns(left)
        self.right_pulses_pwm.duty_ns(right)

    def set_left_brightness(self, brightness):
        self.left_pulses_pwm.duty_ns(brightness)

    def set_right_brightness(self, brightness):
        self.right_pulses_pwm.duty_ns(brightness)

    def off(self):
        self.set_brightnesses(0, 0)


class ProximitySensors:
    def __init__(self):
        self.ir_pulses = IRPulses()

        self.set_frequency(DEFAULT_FREQ)
        self.brightness_levels = DEFAULT_BRIGHTNESS_LEVELS

        self.left_sensor = Pin(23, Pin.IN)
        self.right_sensor = Pin(24, Pin.IN)
        self.front_sensor = Pin(27, Pin.IN)

        self.sensors = [self.left_sensor, self.front_sensor, self.right_sensor]
        self.counts = [array('B', [0, 0]) for _ in range(len(self.sensors))]

    def set_frequency(self, freq):
        self.ir_pulses.set_frequency(freq)

        # According to the TSSP770 datasheet, the delay between the start of the
        # IR pulses and the start of the sensor output pulse could be anywhere
        # between 7/freq and 13/freq.
        #
        # The default pulse on time of 14/freq (250 us for 56 kHz) guarantees we
        # are not missing output pulses by reading the sensor too soon.
        self.pulse_on_time_us = 14 * 1000000 // freq

        # According to the TSSP770 datasheet, the sensor output pulse duration
        # could be up to 4/freq longer than the duration of the IR pulses, and
        # the sensor output pulse could start as late as 13/freq after the IR
        # pulses start.  Therefore, it is possible for the sensor output pulse
        # to end up to 17/freq after the ending of the IR pulses.
        #
        # So the default off time is 18/freq (321 us for 56 kHz).
        self.pulse_off_time_us = 18 * 1000000 // freq

    def _prepare_to_read(self):
        # pull-ups on
        self.left_sensor.init(Pin.IN, Pin.PULL_UP)
        self.right_sensor.init(Pin.IN, Pin.PULL_UP)
        self.front_sensor.init(Pin.IN, Pin.PULL_UP)

    def read(self):
        self._prepare_to_read()

        self.counts = [array('B', [0, 0]) for _ in range(len(self.sensors))]

        for brightness in self.brightness_levels:
            self.ir_pulses.set_brightnesses(brightness, 0)
            sleep_us(self.pulse_on_time_us)
            for sensor, counts in zip(self.sensors, self.counts):
                if not sensor.value(): counts[0] += 1

            self.ir_pulses.off()
            sleep_us(self.pulse_off_time_us)

            self.ir_pulses.set_brightnesses(0, brightness)
            sleep_us(self.pulse_on_time_us)
            for sensor, counts in zip(self.sensors, self.counts):
                if not sensor.value(): counts[1] += 1

            self.ir_pulses.off()
            sleep_us(self.pulse_off_time_us)

    def counts_with_left_leds(self, sensor_number):
        return self.counts[sensor_number][0]

    def counts_with_right_leds(self, sensor_number):
        return self.counts[sensor_number][1]

    def left_counts_with_left_leds(self):
        return self.counts_with_left_leds(0)

    def left_counts_with_right_leds(self):
        return self.counts_with_right_leds(0)

    def front_counts_with_left_leds(self):
        return self.counts_with_left_leds(1)

    def front_counts_with_right_leds(self):
        return self.counts_with_right_leds(1)

    def right_counts_with_left_leds(self):
        return self.counts_with_left_leds(2)

    def right_counts_with_right_leds(self):
        return self.counts_with_right_leds(2)

    def total_counts(self):
        return sum(self.counts[0]) + sum(self.counts[1]) + sum(self.counts[2])

    def angle_estimate(self):
        l = sum(self.counts[0])
        fl = self.counts[1][0]
        fr = self.counts[1][1]
        r = sum(self.counts[2])
        if l + fl + fr + r == 0:
            return 0

        return (-90 * l -20 * fl + 20 * fr + 90 * r) // (l + fl + fr + r)
