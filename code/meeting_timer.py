"""Standalone MicroPython integration test for the team's current breadboard.

Open this one file in Thonny and press F5. No supporting files need uploading.
QUICK_TEST=True uses 30/40/50/60 SECOND runs for the 15/20/25/30 preset labels.
Set QUICK_TEST=False for the actual 15/20/25/30 MINUTE durations.

At startup, purple means calibration: SET jogs forward, a RUN tap jogs back.
Hold RUN for 1.5 seconds to accept the current position as 0/30. Wait about
27 seconds for the initial half-turn to the 15-minute position. Tap RUN to
start; tap again to pause/resume. SET cycles presets while selecting. Hold
RUN to cancel/reset or hold SET to recalibrate. Short actions occur on release.

Green pulses during the first part of a run, then red for the last third of
the 15-minute preset (last 10 seconds in quick mode). Blue indicates selection
or pause. Both buttons held together are ignored until both are released.

Current wiring: motor D0-D3/GPIO1-4, SET D4/GPIO5, RUN D5/GPIO6; RGB red GPIO8,
green GPIO9, blue GPIO7, active-high, with individual series resistors. L293D
pins 8/16 and motor red common use USB 5V, with common ground. Enables 1/9 stay
HIGH; D7 is unused. Ctrl+C stops phase commands and PWM, but fixed enables do
not disconnect the windings. Unplug USB after testing. Low-power operation and
physical timer accuracy are not established by this bench build.

Generated from repository logic, with a fixed-enable driver option and the
team's observed phase order/speed. Position is estimated; no encoder is fitted.
"""

QUICK_TEST = False  # Explicit accelerated test; False selects real-minute timing.

class BenchSettings:
    """Hardware and timing configuration for the XIAO ESP32-S3 meeting timer.

    GPIO numbers below are ESP32 numbers, not the D-labels printed on the XIAO.
    Bench settings match the team's reported button, RGB, and motor checks.
    The complete timer and its power consumption still need physical testing.
    """

    # This bench profile uses the wiring already exercised by the diagnostics.
    WIRING_CONFIRMED = True
    # Active-high RGB operation confirmed by the team's two-cycle bench test.
    # False = common cathode to GND; True = common anode to 3V3.
    RGB_COMMON_ANODE = False

    # L293D inputs 1A/2A/3A/4A: pins 2/7/10/15; XIAO D0/D1/D2/D3.
    # Output wires respectively: orange/pink/yellow/blue; motor red common to 5V.
    MOTOR_GPIOS = (1, 2, 3, 4)
    # A cyclic order for the nominal 28BYJ-48: orange, yellow, pink, blue.
    # Case A at 25 ms: user reported a smooth approximate half-turn and return.
    MOTOR_PHASE_ORDER = (0, 2, 1, 3)
    MOTOR_ACTIVE_LEVEL = 0  # Common at +5V: the selected output must sink current.
    # Existing wiring ties L293D enables HIGH; None means D7 is never configured.
    # This profile does not provide true high-impedance coil release.
    MOTOR_ENABLE_GPIO = None
    SET_GPIO = 5  # D4, normally-open switch to GND; internal pull-up.
    RUN_GPIO = 6  # D5, normally-open switch to GND; also the light-sleep wake pin.
    # Bench test: GPIO7 lit blue, GPIO9 green, and GPIO8 red.
    RGB_GPIOS = (8, 9, 7)  # R/G/B = D9/D10/D8, each through its own 220-ohm resistor.

    PRESET_MINUTES = (15, 20, 25, 30)
    DIAL_MINUTES = 30  # Matches the printed face: 0/30 at the top, 15 at the bottom.
    MINUTE_MS = 2000 if QUICK_TEST else 60000
    WARNING_REMAINING_MS = 5 * MINUTE_MS
    # Nominal full/wave steps, NOT the 4096 half-step convention.
    # TODO: measure an output revolution and adjust for your motor's gear ratio.
    STEPS_PER_REVOLUTION = 2048
    MOTOR_DIRECTION = 1  # Change to -1 if a positive jog goes counterclockwise.
    STEP_INTERVAL_MS = 25  # Conservative starting rate; no blocking motor loops.
    COIL_SETTLE_MS = 100  # Dwell before removing phase commands; fixed enables remain active.
    CALIBRATION_JOG_STEPS = 8
    CALIBRATION_REPEAT_MS = 160

    DEBOUNCE_MS = 30
    LONG_PRESS_MS = 1500
    PWM_FREQUENCY_HZ = 1000
    PULSE_PERIOD_MS = 1000
    MAX_LED_DUTY = 32768  # 16-bit duty limit; resistors still limit peak LED current.
    LED_UPDATE_MS = 20
    LOOP_SLEEP_MS = 2
    LIGHT_SLEEP_ENABLED = False  # Fixed-enable bench wiring; keep USB/Thonny responsive.
    IDLE_SLEEP_MS = 60 * 1000

    def validate(self):
        """Reject unsafe or inconsistent configuration before creating GPIOs."""
        if not self.WIRING_CONFIRMED:
            raise ValueError('Check docs/firmware.md, then set WIRING_CONFIRMED=True')
        if type(self.RGB_COMMON_ANODE) is not bool:
            raise ValueError('Set RGB_COMMON_ANODE to True or False after checking LED')
        pins = self.MOTOR_GPIOS + self.RGB_GPIOS + (self.SET_GPIO, self.RUN_GPIO)
        if self.MOTOR_ENABLE_GPIO is not None:
            pins += (self.MOTOR_ENABLE_GPIO,)
        if self.MOTOR_ENABLE_GPIO is None and self.LIGHT_SLEEP_ENABLED:
            raise ValueError('Fixed enables cannot provide the coil-off sleep mode')
        exposed = (1, 2, 3, 4, 5, 6, 7, 8, 9, 43, 44)
        if len(set(pins)) != len(pins) or any((pin not in exposed for pin in pins)):
            raise ValueError('Use unique exposed XIAO GPIOs; D0 is GPIO1, not GPIO0')
        if len(self.MOTOR_GPIOS) != 4 or len(self.RGB_GPIOS) != 3:
            raise ValueError('Exactly four motor inputs and three RGB channels required')
        if tuple(sorted(self.MOTOR_PHASE_ORDER)) != (0, 1, 2, 3):
            raise ValueError('MOTOR_PHASE_ORDER must be a permutation of 0,1,2,3')
        if self.MOTOR_ACTIVE_LEVEL not in (0, 1) or self.MOTOR_DIRECTION not in (-1, 1):
            raise ValueError('Invalid motor polarity or direction')
        if not isinstance(self.STEPS_PER_REVOLUTION, int) or self.STEPS_PER_REVOLUTION < 4:
            raise ValueError('STEPS_PER_REVOLUTION must be a positive calibrated count')
        if self.PRESET_MINUTES != (15, 20, 25, 30) or self.DIAL_MINUTES != 30:
            raise ValueError('Keep the course presets and the 30-minute printed dial')
        intervals = (self.STEP_INTERVAL_MS, self.COIL_SETTLE_MS, self.DEBOUNCE_MS, self.LONG_PRESS_MS, self.CALIBRATION_REPEAT_MS, self.PWM_FREQUENCY_HZ, self.PULSE_PERIOD_MS, self.LED_UPDATE_MS, self.LOOP_SLEEP_MS, self.IDLE_SLEEP_MS)
        if any((value <= 0 for value in intervals)):
            raise ValueError('Timing constants must be positive')
        if self.LONG_PRESS_MS <= self.DEBOUNCE_MS or not 0 < self.MAX_LED_DUTY <= 65535:
            raise ValueError('Invalid button timing or LED duty limit')
        if not 0 < self.CALIBRATION_JOG_STEPS < self.STEPS_PER_REVOLUTION // 2:
            raise ValueError('Calibration jog must be less than half a revolution')
        if self.LIGHT_SLEEP_ENABLED and self.RUN_GPIO not in (1, 2, 3, 4, 5, 6, 7, 8, 9):
            raise ValueError('Light-sleep wake must use an exposed RTC-capable GPIO')


config = BenchSettings()


class WaveStepper:
    """Drive a four-phase unipolar motor through a noninverting L293D.

    An enable GPIO provides high-impedance release when connected. With
    enable=None, release() only removes active phase commands; outputs remain
    driven and residual winding current can flow through the L293D.
    Only the selected input has active_level; all others are inactive. With
    the red motor common at +5V, active_level MUST be 0 (current sinking).
    Position is an open-loop estimate, not a sensor reading.
    """

    def __init__(
        self,
        pins,
        enable,
        phase_order,
        active_level,
        direction,
        steps_per_rev,
        interval_ms,
        settle_ms,
        ticks_diff,
        now,
    ):
        self.pins = pins
        self.enable = enable
        self.order = phase_order
        self.active = active_level
        self.direction = direction
        self.steps_per_rev = steps_per_rev
        self.interval_ms = interval_ms
        self.settle_ms = settle_ms
        self.diff = ticks_diff
        self.position = self.target = 0
        self.phase = 0
        self.last_step_at = now
        self.energized = False
        self.release()

    def release(self):
        """Remove phase commands, disabling outputs only when an enable GPIO exists."""
        if self.enable is not None:
            self.enable.value(0)
        for pin in self.pins:
            pin.value(1 - self.active)
        self.energized = False

    def _energize(self, now):
        # Remove the previous active command before selecting the next winding.
        if self.enable is not None:
            self.enable.value(0)
        for pin in self.pins:
            pin.value(1 - self.active)
        self.pins[self.order[self.phase]].value(self.active)
        if self.enable is not None:
            self.enable.value(1)
        self.energized = True
        self.last_step_at = now

    def align(self, now):
        """Seat the rotor at a known phase before the user sets the hand zero."""
        self.target = self.position
        self._energize(now)

    def set_target(self, position):
        """Request a modulo position; motion proceeds via update()."""
        self.target = position % self.steps_per_rev

    def stop(self):
        """Cancel queued motion without discarding the estimated position."""
        self.target = self.position
        self.release()

    def mark_zero(self):
        """Accept a user-confirmed physical zero only when the rotor is settled."""
        if not self.is_settled():
            raise ValueError("Wait for motor motion to finish before setting zero")
        self.position = self.target = 0

    def is_settled(self):
        """True once all requested steps and the final coil dwell are complete."""
        return self.position == self.target and not self.energized

    def update(self, now):
        """Issue at most one step; never burst missed steps after a loop delay."""
        elapsed = self.diff(now, self.last_step_at)
        if self.position == self.target:
            if self.energized and elapsed >= self.settle_ms:
                self.release()
            return
        if elapsed < self.interval_ms:
            return
        delta = (self.target - self.position) % self.steps_per_rev
        step = 1 if delta <= self.steps_per_rev // 2 else -1
        self.phase = (self.phase + step * self.direction) % 4
        self._energize(now)
        self.position = (self.position + step) % self.steps_per_rev


class RgbLed:
    """Translate logical brightness into PWM, including common-anode inversion."""

    def __init__(self, channels, common_anode):
        self.channels = channels
        self.common_anode = common_anode

    def write(self, rgb):
        """Set three duties in [0, 65535]; a logical zero always means off."""
        for channel, duty in zip(self.channels, rgb):
            duty = max(0, min(65535, int(duty)))
            channel.duty_u16(65535 - duty if self.common_anode else duty)

    def off(self):
        """Turn off all three colours without allocating new PWM channels."""
        self.write((0, 0, 0))


CALIBRATING = "calibrating"
SELECTING = "selecting"
RUNNING = "running"
PAUSED = "paused"
FINISHED = "finished"
SHORT = "short"
LONG = "long"


class Button:
    """Debounce an active-low switch; emit short on release or long once.

    A switch held during boot/wake is ignored until released. A long press
    never also emits a short press, preventing an unintended second action.
    """

    def __init__(self, debounce_ms, long_ms, ticks_diff, now, pressed=False):
        self.debounce_ms = debounce_ms
        self.long_ms = long_ms
        self.diff = ticks_diff
        self.reset(now, pressed)

    def reset(self, now, pressed):
        """Consume any held switch, including the press that woke the board."""
        self.raw = self.pressed = bool(pressed)
        self.changed_at = self.pressed_at = now
        self.armed = not pressed
        self.long_sent = False

    def update(self, pressed, now):
        """Return SHORT, LONG, or None after processing one sampled level."""
        pressed = bool(pressed)
        if pressed != self.raw:
            self.raw = pressed
            self.changed_at = now
        if (
            self.raw != self.pressed
            and self.diff(now, self.changed_at) >= self.debounce_ms
        ):
            self.pressed = self.raw
            if self.pressed:
                self.pressed_at = now
                self.long_sent = False
            else:
                # Decide duration here too: a late poll must not misclassify
                # an entire long press as short just because its hold was missed.
                held_ms = self.diff(self.changed_at, self.pressed_at)
                event = None
                if self.armed and not self.long_sent:
                    event = LONG if held_ms >= self.long_ms else SHORT
                self.armed = True
                return event
        if (
            self.pressed
            and self.raw
            and self.armed
            and not self.long_sent
            and self.diff(now, self.pressed_at) >= self.long_ms
        ):
            self.long_sent = True
            return LONG
        return None


class MeetingTimer:
    """Finite-state countdown with no dependence on motor speed or loop rate."""

    def __init__(self, presets_ms, dial_ms, steps_per_rev, ticks_diff, now):
        self.presets = tuple(presets_ms)
        if not self.presets or min(self.presets) <= 0 or max(self.presets) > dial_ms:
            raise ValueError("Presets must fit the positive dial duration")
        self.dial_ms = dial_ms
        self.steps_per_rev = steps_per_rev
        self.diff = ticks_diff
        self.selected = 0
        self.state = CALIBRATING
        self.remaining_ms = self.presets[0]
        self.state_elapsed_ms = 0
        self.last_tick = now

    def transition(self, state):
        """Change state and restart its LED animation phase."""
        self.state = state
        self.state_elapsed_ms = 0

    def update(self, now):
        """Account for elapsed real time, including late loop iterations."""
        elapsed = self.diff(now, self.last_tick)
        if elapsed < 0:
            raise ValueError(
                "Clock moved backward or was not serviced within half a wrap"
            )
        self.last_tick = now
        self.state_elapsed_ms += elapsed
        if self.state == RUNNING:
            self.remaining_ms = max(0, self.remaining_ms - elapsed)
            if self.remaining_ms == 0:
                self.transition(FINISHED)

    def reset(self):
        """Cancel/rearm the selected duration without forgetting the hand zero."""
        self.remaining_ms = self.presets[self.selected]
        self.transition(SELECTING)

    def select_next(self):
        """Cycle presets only while selecting or after completion."""
        if self.state in (SELECTING, FINISHED):
            self.selected = (self.selected + 1) % len(self.presets)
            self.reset()

    def run_button(self, motor_ready):
        """Start/resume only after positioning; pause or acknowledge otherwise."""
        if self.state in (SELECTING, PAUSED) and motor_ready:
            self.transition(RUNNING)
        elif self.state == RUNNING:
            self.transition(PAUSED)
        elif self.state == FINISHED:
            self.reset()

    def target_steps(self):
        """Map remaining time to the fixed dial, rounded to the nearest step.

        Zero and 30 minutes share a physical angle. Modulo positioning avoids
        an unnecessary full revolution when selecting the 30-minute preset.
        """
        rounded = (
            self.remaining_ms * self.steps_per_rev + self.dial_ms // 2
        ) // self.dial_ms
        return rounded % self.steps_per_rev


def indicator(timer, period_ms, max_duty, warning_ms):
    """Return logical R/G/B 16-bit brightness; driver handles LED polarity."""
    age = timer.state_elapsed_ms
    phase = age % period_ms
    duty = max_duty * (period_ms - abs(2 * phase - period_ms)) // period_ms
    if timer.state == CALIBRATING:
        return duty, 0, duty  # Purple identifies the uncalibrated state.
    if timer.state == SELECTING:
        # 1/2/3/4 blue pulses identify 15/20/25/30, followed by a two-second gap.
        pulses = timer.selected + 1
        if age % ((pulses + 2) * period_ms) >= pulses * period_ms:
            duty = 0
        return 0, 0, duty
    if timer.state == PAUSED:
        return 0, 0, duty
    if timer.state == FINISHED or timer.remaining_ms <= warning_ms:
        return duty, 0, 0
    return 0, duty, 0


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
            tuple(minutes * settings.MINUTE_MS for minutes in settings.PRESET_MINUTES),
            settings.DIAL_MINUTES * settings.MINUTE_MS,
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
    """Run the application; remove phase commands and stop PWM on exit."""
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
    pins = []
    channels = []
    rgb_pins = []
    led_off_level = 1 if config.RGB_COMMON_ANODE else 0
    try:
        if config.MOTOR_ENABLE_GPIO is not None:
            enable = machine.Pin(config.MOTOR_ENABLE_GPIO, machine.Pin.OUT, value=0)
        for number in config.MOTOR_GPIOS:
            pins.append(machine.Pin(
                number, machine.Pin.OUT, value=1 - config.MOTOR_ACTIVE_LEVEL
            ))
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
        if config.MINUTE_MS != 60000:
            print("QUICK BENCH TEST: 15/20/25/30 presets run for 30/40/50/60 seconds.")
        else:
            print("REAL TIMER: 15/20/25/30 minute presets.")
        if config.MOTOR_ENABLE_GPIO is None:
            print("Fixed-enable wiring: D7 is unused. Unplug USB after testing.")
        print("Calibration: SET jogs forward; tap RUN to jog back.")
        print("At 0/30, hold RUN for 1.5 s. Wait for preset positioning, then tap RUN.")
        previous_state = app.timer.state
        previous_selected = None
        last_status = now
        while True:
            now = time.ticks_ms()
            app.update(now)
            if app.timer.state != previous_state:
                print("Timer:", app.timer.state)
                previous_state = app.timer.state
            if app.timer.selected != previous_selected:
                print("Preset:", config.PRESET_MINUTES[app.timer.selected],
                      "minutes; actual run:", app.timer.presets[app.timer.selected] // 1000, "seconds")
                previous_selected = app.timer.selected
            if time.ticks_diff(now, last_status) >= 5000:
                print("Status:", app.timer.state, "remaining:",
                      (app.timer.remaining_ms + 999) // 1000, "s; hand:",
                      "ready" if motor.is_settled() else "moving")
                last_status = now
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
        for pin in pins:
            pin.value(1 - config.MOTOR_ACTIVE_LEVEL)
        for channel in channels:
            channel.deinit()
        for pin in rgb_pins:
            pin.init(machine.Pin.OUT, value=led_off_level)
        if config.MOTOR_ENABLE_GPIO is None:
            print("Phase commands stopped; driver remains enabled. Unplug USB.")


if __name__ == "__main__":
    run()
