"""MicroPython entry point and cooperative application controller.

Copy config.py, logic.py, hardware.py and this file to the board's filesystem
root. main.py runs after boot; importing it in desktop tests has no GPIO effects.
No network connection, third-party package, or interrupt callback is required.
"""

import config
from hardware import RgbLed, WaveStepper
from logic import (
    CALIBRATING,
    FINISHED,
    LONG,
    SELECTING,
    SHORT,
    Button,
    MeetingTimer,
    indicator,
)


class TimerApplication:
    """Coordinate buttons, countdown, motor, and LEDs without blocking motion."""

    def __init__(self, settings, motor, led, set_pin, run_pin, ticks_diff, now):
        self.cfg = settings
        self.motor = motor
        self.led = led
        self.set_pin = set_pin
        self.run_pin = run_pin
        self.diff = ticks_diff
        self.timer = MeetingTimer(
            tuple(minutes * 60000 for minutes in settings.PRESET_MINUTES),
            settings.DIAL_MINUTES * 60000,
            settings.STEPS_PER_REVOLUTION,
            ticks_diff,
            now,
        )
        self.set_button = Button(
            settings.DEBOUNCE_MS,
            settings.LONG_PRESS_MS,
            ticks_diff,
            now,
            not set_pin.value(),
        )
        self.run_button = Button(
            settings.DEBOUNCE_MS,
            settings.LONG_PRESS_MS,
            ticks_diff,
            now,
            not run_pin.value(),
        )
        self.last_activity = now
        self.last_led_update = now
        self.last_jog = None
        self.chord_blocked = False
        # Without a home sensor, every reset must ask the user to establish zero.
        # Align first so an unknown initial electrical phase is not counted as a step.
        self.motor.align(now)

    def _consume_buttons(self, now):
        self.set_button.reset(now, not self.set_pin.value())
        self.run_button.reset(now, not self.run_pin.value())

    def _calibrate(self, set_pressed, run_pressed, run_event, now):
        if not set_pressed:
            self.last_jog = None
        elif self.set_button.armed and not run_pressed and self.motor.is_settled():
            if (
                self.last_jog is None
                or self.diff(now, self.last_jog) >= self.cfg.CALIBRATION_REPEAT_MS
            ):
                self.motor.set_target(
                    self.motor.position + self.cfg.CALIBRATION_JOG_STEPS
                )
                self.last_jog = now
        if run_event == SHORT and not set_pressed and self.motor.is_settled():
            self.motor.set_target(self.motor.position - self.cfg.CALIBRATION_JOG_STEPS)
        elif run_event == LONG and not set_pressed and self.motor.is_settled():
            self.motor.mark_zero()
            self.timer.reset()
            self._consume_buttons(now)

    def update(self, now):
        """Service all subsystems once; the runtime calls this every few ms."""
        old_state = self.timer.state
        self.timer.update(now)
        raw_set = not self.set_pin.value()
        raw_run = not self.run_pin.value()
        set_event = self.set_button.update(raw_set, now)
        run_event = self.run_button.update(raw_run, now)
        if raw_set or raw_run or set_event or run_event:
            self.last_activity = now

        # Ignore a two-button chord until both switches are released. This also
        # consumes pending release events, rather than turning them into clicks.
        if raw_set and raw_run:
            self.chord_blocked = True
        if self.chord_blocked:
            self._consume_buttons(now)
            if self.timer.state == CALIBRATING:
                self.motor.stop()
                self.last_jog = None
            if not raw_set and not raw_run:
                self.chord_blocked = False
        elif self.timer.state == CALIBRATING:
            self._calibrate(
                self.set_button.pressed, self.run_button.pressed, run_event, now
            )
        elif set_event == LONG:
            self.timer.transition(CALIBRATING)
            self.motor.stop()
            self.motor.align(now)
            self.last_jog = None
            self._consume_buttons(now)
        elif run_event == LONG:
            self.timer.reset()
        elif set_event == SHORT:
            self.timer.select_next()
        elif run_event == SHORT:
            self.timer.run_button(self.motor.is_settled())

        if self.timer.state != CALIBRATING:
            self.motor.set_target(self.timer.target_steps())
        self.motor.update(now)
        if self.timer.state != old_state:
            self.last_activity = now
        if self.diff(now, self.last_led_update) >= self.cfg.LED_UPDATE_MS:
            self.led.write(
                indicator(
                    self.timer,
                    self.cfg.PULSE_PERIOD_MS,
                    self.cfg.MAX_LED_DUTY,
                    self.cfg.WARNING_REMAINING_MS,
                )
            )
            self.last_led_update = now

    def can_sleep(self, now):
        """Never enter light sleep during a meeting, pause, or calibration."""
        return (
            self.cfg.LIGHT_SLEEP_ENABLED
            and self.timer.state in (SELECTING, FINISHED)
            and self.motor.is_settled()
            and self.set_pin.value()
            and self.run_pin.value()
            and not self.set_button.pressed
            and not self.run_button.pressed
            and self.diff(now, self.last_activity) >= self.cfg.IDLE_SLEEP_MS
        )

    def wake(self, now):
        """Retain the selected preset/zero and consume the RUN wake-up press."""
        # Light sleep may last longer than half the wrapping tick period. No
        # countdown was active, so establish a fresh clock reference on wake.
        self.timer.last_tick = now
        self.timer.state_elapsed_ms = 0
        self.motor.last_step_at = now
        self.last_activity = self.last_led_update = now
        self._consume_buttons(now)


def run():
    """Initialize safely, run until interrupted, and disable outputs on exit."""
    config.validate()  # Deliberately before importing or creating hardware pins.
    import time

    import bluetooth
    import machine
    import network

    # The meeting timer is self-contained. Disable both radio stacks rather
    # than connecting to Wi-Fi or keeping a Bluetooth advertiser alive.
    network.WLAN(network.STA_IF).active(False)
    network.WLAN(network.AP_IF).active(False)
    bluetooth.BLE().active(False)

    enable = None
    motor = None
    channels = []
    rgb_pins = []
    led_off_level = 1 if config.RGB_COMMON_ANODE else 0
    try:
        enable = machine.Pin(config.MOTOR_ENABLE_GPIO, machine.Pin.OUT, value=0)
        pins = tuple(
            machine.Pin(number, machine.Pin.OUT, value=1 - config.MOTOR_ACTIVE_LEVEL)
            for number in config.MOTOR_GPIOS
        )
        set_pin = machine.Pin(config.SET_GPIO, machine.Pin.IN, machine.Pin.PULL_UP)
        run_pin = machine.Pin(config.RUN_GPIO, machine.Pin.IN, machine.Pin.PULL_UP)
        for number in config.RGB_GPIOS:
            pin = machine.Pin(number, machine.Pin.OUT, value=led_off_level)
            rgb_pins.append(pin)
            channels.append(
                machine.PWM(
                    pin, freq=config.PWM_FREQUENCY_HZ, duty_u16=65535 * led_off_level
                )
            )
        led = RgbLed(channels, config.RGB_COMMON_ANODE)
        now = time.ticks_ms()
        motor = WaveStepper(
            pins,
            enable,
            config.MOTOR_PHASE_ORDER,
            config.MOTOR_ACTIVE_LEVEL,
            config.MOTOR_DIRECTION,
            config.STEPS_PER_REVOLUTION,
            config.STEP_INTERVAL_MS,
            config.COIL_SETTLE_MS,
            time.ticks_diff,
            now,
        )
        app = TimerApplication(
            config, motor, led, set_pin, run_pin, time.ticks_diff, now
        )
        if config.LIGHT_SLEEP_ENABLED:
            import esp32

            esp32.wake_on_ext0(pin=run_pin, level=esp32.WAKEUP_ALL_LOW)
        print("Calibration: SET jogs clockwise; tap RUN to jog back.")
        print("At 0/30, hold RUN for 1.5 s. Wait for preset positioning, then tap RUN.")
        previous_state = app.timer.state
        while True:
            now = time.ticks_ms()
            app.update(now)
            if app.timer.state != previous_state:
                print("Timer:", app.timer.state)
                previous_state = app.timer.state
            if app.can_sleep(now):
                motor.release()
                led.off()
                machine.lightsleep()
                app.wake(time.ticks_ms())
            time.sleep_ms(config.LOOP_SLEEP_MS)
    finally:
        # Covers Ctrl-C, runtime errors, and partially constructed peripherals.
        # A physical reset/power failure still requires startup zero calibration.
        if enable is not None:
            enable.value(0)
        if motor is not None:
            motor.release()
        for channel in channels:
            channel.deinit()
        for pin in rgb_pins:
            pin.init(machine.Pin.OUT, value=led_off_level)


if __name__ == "__main__":
    run()
