"""Regression tests for the final standalone firmware; GPIOs and time are simulated.

Run from the repository root: python3 -m unittest discover -s tests -v
The fake clock wraps deliberately so long meetings exercise wrap-safe timing.
"""

import importlib
import pathlib
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "code"))
from meeting_timer import config, RgbLed, WaveStepper
from meeting_timer import (
    CALIBRATING,
    FINISHED,
    LONG,
    PAUSED,
    RUNNING,
    SELECTING,
    SHORT,
    Button,
    MeetingTimer,
    indicator,
)
from meeting_timer import TimerApplication

TICK_PERIOD = 1 << 20


def ticks_diff(new, old):
    return ((new - old + TICK_PERIOD // 2) % TICK_PERIOD) - TICK_PERIOD // 2


class Pin:
    def __init__(self, value=1, changed=None):
        self.level = value
        self.changed = changed

    def value(self, level=None):
        if level is not None:
            self.level = level
            if self.changed:
                self.changed()
        return self.level


class PWM:
    def __init__(self):
        self.duty = None

    def duty_u16(self, value):
        self.duty = value


def settings(**overrides):
    result = {key: getattr(config, key) for key in dir(config) if key.isupper()}
    result.update(overrides)
    return types.SimpleNamespace(**result)


class Rig:
    """Run the real application/driver with a wrapping clock and fake I/O."""

    def __init__(self, **overrides):
        self.cfg = settings(**overrides)
        self.now = 0
        self.set_pin, self.run_pin = Pin(), Pin()
        self.coils = [Pin() for _ in range(4)]
        self.enable = Pin(0) if self.cfg.MOTOR_ENABLE_GPIO is not None else None
        self.motor = WaveStepper(
            self.coils,
            self.enable,
            self.cfg.MOTOR_PHASE_ORDER,
            self.cfg.MOTOR_ACTIVE_LEVEL,
            self.cfg.MOTOR_DIRECTION,
            self.cfg.STEPS_PER_REVOLUTION,
            self.cfg.STEP_INTERVAL_MS,
            self.cfg.COIL_SETTLE_MS,
            ticks_diff,
            self.now,
        )
        self.channels = [PWM() for _ in range(3)]
        self.led = RgbLed(self.channels, False)
        self.app = TimerApplication(
            self.cfg,
            self.motor,
            self.led,
            self.set_pin,
            self.run_pin,
            ticks_diff,
            self.now,
        )

    def advance(self, duration, quantum=5):
        while duration:
            elapsed = min(duration, quantum)
            self.now = (self.now + elapsed) % TICK_PERIOD
            self.app.update(self.now)
            duration -= elapsed

    def press(self, pin, duration=80):
        pin.value(0)
        self.advance(duration)
        pin.value(1)
        self.advance(50)

    def ready(self):
        self.advance(50)
        self.press(self.run_pin, self.cfg.LONG_PRESS_MS + 80)
        self.advance(28000)
        assert self.app.timer.state == SELECTING and self.motor.is_settled()


class ButtonTests(unittest.TestCase):
    def test_contact_bounce_produces_one_short_event(self):
        button = Button(30, 1500, ticks_diff, 0)
        for t, state in [
            (1, True),
            (10, False),
            (15, True),
            (25, False),
            (30, True),
            (60, True),
            (90, False),
            (100, True),
            (110, False),
        ]:
            self.assertIsNone(button.update(state, t))
        self.assertEqual(button.update(False, 140), SHORT)
        self.assertIsNone(button.update(False, 180))

    def test_long_press_fires_once_and_suppresses_release_click(self):
        button = Button(30, 1500, ticks_diff, 0)
        button.update(True, 10)
        button.update(True, 40)
        self.assertEqual(button.update(True, 1540), LONG)
        self.assertIsNone(button.update(True, 2500))
        button.update(False, 2600)
        self.assertIsNone(button.update(False, 2630))

    def test_held_at_boot_is_consumed(self):
        button = Button(30, 1500, ticks_diff, 0, pressed=True)
        self.assertIsNone(button.update(True, 2000))
        button.update(False, 2050)
        self.assertIsNone(button.update(False, 2080))

    def test_short_press_across_tick_wrap(self):
        start = TICK_PERIOD - 60
        button = Button(30, 1500, ticks_diff, start)
        button.update(True, start + 10)
        button.update(True, start + 40)
        button.update(False, 30)
        self.assertEqual(button.update(False, 60), SHORT)

    def test_late_poll_does_not_turn_long_press_into_short(self):
        button = Button(30, 1500, ticks_diff, 0)
        button.update(True, 10)
        button.update(True, 40)
        button.update(False, 2000)
        self.assertEqual(button.update(False, 2030), LONG)


class TimerTests(unittest.TestCase):
    def make_timer(self):
        return MeetingTimer(
            [900000, 1200000, 1500000, 1800000], 1800000, 2048, ticks_diff, 0
        )

    def test_exact_presets_and_fixed_dial(self):
        timer = self.make_timer()
        timer.reset()
        for expected_ms, angle in [
            (900000, 1024),
            (1200000, 1365),
            (1500000, 1707),
            (1800000, 0),
            (900000, 1024),
        ]:
            self.assertEqual(timer.remaining_ms, expected_ms)
            self.assertEqual(timer.target_steps(), angle)
            timer.select_next()

    def test_each_full_duration_expires_across_clock_wraps(self):
        for selected in range(4):
            timer = self.make_timer()
            timer.selected = selected
            timer.reset()
            duration = timer.remaining_ms
            timer.run_button(True)
            elapsed = 0
            # Uneven service intervals expose cumulative-loop-delay mistakes.
            while elapsed < duration:
                elapsed = min(duration, elapsed + 137)
                timer.update(elapsed % TICK_PERIOD)
                self.assertEqual(timer.remaining_ms, duration - elapsed)
            self.assertEqual(timer.state, FINISHED)
            self.assertEqual(timer.target_steps(), 0)

    def test_pause_resume_preserves_remaining_time(self):
        timer = self.make_timer()
        timer.reset()
        timer.run_button(True)
        timer.update(12345)
        timer.run_button(True)
        self.assertEqual(timer.state, PAUSED)
        timer.update(212345)
        self.assertEqual(timer.remaining_ms, 887655)
        timer.run_button(True)
        timer.update(222345)
        self.assertEqual(timer.remaining_ms, 877655)

    def test_selection_is_locked_during_running_and_pause(self):
        timer = self.make_timer()
        timer.reset()
        timer.run_button(True)
        timer.select_next()
        self.assertEqual(timer.selected, 0)
        timer.run_button(True)
        timer.select_next()
        self.assertEqual(timer.selected, 0)

    def test_overshoot_stops_at_zero_and_reset_rearms(self):
        timer = self.make_timer()
        timer.reset()
        timer.remaining_ms = 50
        timer.run_button(True)
        timer.update(200)
        self.assertEqual((timer.state, timer.remaining_ms), (FINISHED, 0))
        timer.run_button(True)
        self.assertEqual((timer.state, timer.remaining_ms), (SELECTING, 900000))

    def test_cannot_start_before_hand_is_positioned(self):
        timer = self.make_timer()
        timer.reset()
        timer.run_button(False)
        self.assertEqual(timer.state, SELECTING)


class MotorTests(unittest.TestCase):
    def test_wave_outputs_never_activate_two_coils_including_transients(self):
        rig = Rig()
        observations = []

        def observe():
            selected = [i for i, pin in enumerate(rig.coils) if pin.value() == 0]
            self.assertLessEqual(len(selected), 1)

        for pin in rig.coils:
            pin.changed = observe
        rig.motor.set_target(4)
        for now in (25, 50, 75, 100):
            rig.motor.update(now)
            observations.append(next(i for i, pin in enumerate(rig.coils) if pin.value() == 0))
        self.assertEqual(observations, [3, 1, 2, 0])
        rig.motor.update(200)
        self.assertTrue(all(pin.value() == 1 for pin in rig.coils))
        self.assertTrue(rig.motor.is_settled())

    def test_reverse_wrap_uses_one_step_not_full_revolution(self):
        rig = Rig()
        rig.motor.set_target(2047)
        rig.motor.update(25)
        self.assertEqual(rig.motor.position, 2047)
        self.assertEqual(rig.motor.phase, 1)

    def test_direction_setting_reverses_phases_not_logical_angle(self):
        for direction, phase in ((-1, 3), (1, 1)):
            rig = Rig(MOTOR_DIRECTION=direction)
            rig.motor.set_target(1)
            rig.motor.update(25)
            self.assertEqual((rig.motor.phase, rig.motor.position), (phase, 1))

    def test_late_service_never_creates_a_burst_of_steps(self):
        rig = Rig()
        rig.motor.set_target(20)
        rig.motor.update(1000)
        rig.motor.update(1000)
        self.assertEqual(rig.motor.position, 1)

    def test_pulse_dwell_and_step_interval_work_across_wrap(self):
        rig = Rig()
        rig.motor.last_step_at = TICK_PERIOD - 10
        rig.motor.set_target(1)
        rig.motor.update(14)
        self.assertEqual(rig.motor.position, 0)
        rig.motor.update(15)
        self.assertEqual(rig.motor.position, 1)
        rig.motor.update(114)
        self.assertTrue(rig.motor.energized)
        rig.motor.update(115)
        self.assertFalse(rig.motor.energized)

    def test_zero_cannot_be_marked_during_motion(self):
        rig = Rig()
        with self.assertRaises(ValueError):
            rig.motor.mark_zero()
        rig.motor.update(100)
        rig.motor.mark_zero()


class IndicatorTests(unittest.TestCase):
    def test_pwm_polarities_have_correct_off_and_on_values(self):
        for anode in (False, True):
            channels = [PWM() for _ in range(3)]
            led = RgbLed(channels, anode)
            led.write((0, 12345, 65535))
            expected = (65535, 53190, 0) if anode else (0, 12345, 65535)
            self.assertEqual(tuple(c.duty for c in channels), expected)
            led.off()
            self.assertEqual(
                tuple(c.duty for c in channels), (65535 if anode else 0,) * 3
            )

    def test_leds_pulse_at_one_second_and_switch_at_five_minutes(self):
        timer = TimerTests().make_timer()
        timer.reset()
        timer.run_button(True)
        for age, expected in [(0, 0), (250, 16384), (500, 32768), (1000, 0)]:
            timer.state_elapsed_ms = age
            self.assertEqual(indicator(timer, 1000, 32768, 300000), (0, expected, 0))
        timer.remaining_ms = 300000
        timer.state_elapsed_ms = 500
        self.assertEqual(indicator(timer, 1000, 32768, 300000), (32768, 0, 0))

    def test_preset_blink_count_and_gap(self):
        timer = TimerTests().make_timer()
        timer.reset()
        for selected in range(4):
            timer.selected = selected
            count = 0
            for pulse in range(selected + 3):
                timer.state_elapsed_ms = pulse * 1000 + 500
                count += indicator(timer, 1000, 32768, 300000)[2] > 0
            self.assertEqual(count, selected + 1)


class ApplicationTests(unittest.TestCase):
    def test_startup_calibration_jogs_and_long_confirm_do_not_start_timer(self):
        rig = Rig()
        rig.advance(50)
        self.assertEqual(rig.app.timer.state, CALIBRATING)
        rig.press(rig.set_pin)
        rig.advance(300)
        self.assertEqual(rig.motor.position, 8)
        rig.press(rig.run_pin)
        rig.advance(300)
        self.assertEqual(rig.motor.position, 0)
        rig.press(rig.run_pin, 1580)
        self.assertEqual(rig.app.timer.state, SELECTING)
        rig.advance(28000)
        self.assertEqual(rig.motor.position, 1024)
        self.assertEqual(rig.app.timer.remaining_ms, 900000)

    def test_controls_complete_a_start_pause_resume_reset_cycle(self):
        rig = Rig()
        rig.ready()
        rig.press(rig.set_pin)
        rig.advance(10000)
        self.assertEqual(rig.app.timer.remaining_ms, 1200000)
        rig.press(rig.run_pin)
        self.assertEqual(rig.app.timer.state, RUNNING)
        rig.advance(1230)
        rig.press(rig.run_pin)
        paused_ms = rig.app.timer.remaining_ms
        rig.advance(7000)
        self.assertEqual(rig.app.timer.remaining_ms, paused_ms)
        rig.press(rig.run_pin)
        rig.advance(300)
        self.assertLess(rig.app.timer.remaining_ms, paused_ms)
        rig.press(rig.run_pin, 1580)
        self.assertEqual(rig.app.timer.state, SELECTING)
        self.assertEqual(rig.app.timer.remaining_ms, 1200000)

    def test_both_buttons_are_ignored_until_both_released(self):
        rig = Rig()
        rig.ready()
        rig.set_pin.value(0)
        rig.run_pin.value(0)
        rig.advance(2000)
        rig.set_pin.value(1)
        rig.advance(100)
        rig.run_pin.value(1)
        rig.advance(100)
        self.assertEqual((rig.app.timer.state, rig.app.timer.selected), (SELECTING, 0))

    def test_low_power_excludes_active_paused_and_calibration_states(self):
        rig = Rig(IDLE_SLEEP_MS=1000, LIGHT_SLEEP_ENABLED=True, MOTOR_ENABLE_GPIO=44)
        rig.advance(2000)
        self.assertFalse(rig.app.can_sleep(rig.now))
        rig.ready()
        self.assertTrue(rig.app.can_sleep(rig.now))
        rig.press(rig.run_pin)
        rig.advance(2000)
        self.assertFalse(rig.app.can_sleep(rig.now))
        rig.press(rig.run_pin)
        rig.advance(2000)
        self.assertFalse(rig.app.can_sleep(rig.now))

    def test_wake_after_long_sleep_consumes_press_and_resets_motor_clock(self):
        rig = Rig()
        rig.ready()
        rig.now = (rig.now + TICK_PERIOD // 2 + 100) % TICK_PERIOD
        rig.run_pin.value(0)
        rig.app.wake(rig.now)
        rig.advance(2000)
        rig.run_pin.value(1)
        rig.advance(100)
        self.assertEqual(rig.app.timer.state, SELECTING)
        rig.press(rig.set_pin)
        rig.advance(10000)
        self.assertTrue(rig.motor.is_settled())
        self.assertEqual(rig.motor.position, 1365)

    def test_recalibration_cancels_countdown_and_requires_confirmation(self):
        rig = Rig()
        rig.ready()
        rig.press(rig.run_pin)
        rig.press(rig.set_pin, 1600)
        self.assertEqual(rig.app.timer.state, CALIBRATING)
        rig.advance(1000)
        self.assertTrue(rig.motor.is_settled())


class ConfigurationTests(unittest.TestCase):
    def test_commissioning_guard_can_inhibit_hardware(self):
        config.validate()
        with patch.object(config, "WIRING_CONFIRMED", False):
            with self.assertRaisesRegex(ValueError, "WIRING_CONFIRMED"):
                config.validate()

    def test_unknown_led_and_duplicate_pins_are_rejected(self):
        with patch.object(config, "WIRING_CONFIRMED", True):
            with patch.object(config, "RGB_COMMON_ANODE", None):
                with self.assertRaisesRegex(ValueError, "RGB_COMMON_ANODE"):
                    config.validate()
            with patch.object(config, "RGB_COMMON_ANODE", False):
                config.validate()
                with patch.object(config, "SET_GPIO", config.RUN_GPIO):
                    with self.assertRaisesRegex(ValueError, "unique"):
                        config.validate()


class RuntimeTests(unittest.TestCase):
    def make_runtime(self, fail_pwm=None):
        """Stub only MicroPython APIs; execute the actual production run()."""
        created_pins = {}
        created_pwm = []

        class MachinePin(Pin):
            OUT, IN, PULL_UP = 1, 0, 2

            def __init__(self, number, mode, pull=None, value=1):
                super().__init__(value)
                self.number = number
                created_pins[number] = self

            def init(self, mode, value):
                self.value(value)

        class MachinePWM(PWM):
            def __init__(self, pin, freq, duty_u16):
                if len(created_pwm) == fail_pwm:
                    raise OSError("Injected PWM initialization failure")
                super().__init__()
                self.duty = duty_u16
                self.closed = False
                created_pwm.append(self)

            def deinit(self):
                self.closed = True

        def stop_loop(_milliseconds):
            raise KeyboardInterrupt()

        radio = types.SimpleNamespace(active=lambda enabled: None)
        modules = {
            "machine": types.SimpleNamespace(Pin=MachinePin, PWM=MachinePWM),
            "time": types.SimpleNamespace(
                ticks_ms=lambda: 0, ticks_diff=ticks_diff, sleep_ms=stop_loop
            ),
            "network": types.SimpleNamespace(
                STA_IF=0, AP_IF=1, WLAN=lambda interface: radio
            ),
            "bluetooth": types.SimpleNamespace(BLE=lambda: radio),
        }
        return modules, created_pins, created_pwm

    def test_ctrl_c_releases_motor_and_closes_pwm_for_both_led_polarities(self):
        entry = importlib.import_module("meeting_timer")
        for anode in (False, True):
            modules, pins, pwms = self.make_runtime()
            with (
                patch.dict(sys.modules, modules),
                patch.multiple(
                    config,
                    WIRING_CONFIRMED=True,
                    RGB_COMMON_ANODE=anode,
                    LIGHT_SLEEP_ENABLED=False,
                ),
                patch("builtins.print"),
            ):
                with self.assertRaises(KeyboardInterrupt):
                    entry.run()
            self.assertNotIn(44, pins)
            self.assertTrue(all(pins[p].value() == 1 for p in config.MOTOR_GPIOS))
            self.assertEqual(len(pwms), 3)
            self.assertTrue(all(pwm.closed for pwm in pwms))
            self.assertTrue(
                all(pins[gpio].value() == int(anode) for gpio in config.RGB_GPIOS)
            )

    def test_partial_initialization_failure_disables_motor_and_existing_pwm(self):
        entry = importlib.import_module("meeting_timer")
        modules, pins, pwms = self.make_runtime(fail_pwm=1)
        with (
            patch.dict(sys.modules, modules),
            patch.multiple(
                config,
                WIRING_CONFIRMED=True,
                RGB_COMMON_ANODE=False,
                LIGHT_SLEEP_ENABLED=False,
            ),
        ):
            with self.assertRaisesRegex(OSError, "Injected PWM"):
                entry.run()
        self.assertNotIn(44, pins)
        self.assertTrue(all(pins[p].value() == 1 for p in config.MOTOR_GPIOS))
        self.assertEqual(len(pwms), 1)
        self.assertTrue(pwms[0].closed)

    def test_commissioning_guard_runs_before_any_gpio_initialization(self):
        entry = importlib.import_module("meeting_timer")
        modules, pins, pwms = self.make_runtime()
        with patch.dict(sys.modules, modules), patch.object(config, "WIRING_CONFIRMED", False):
            with self.assertRaisesRegex(ValueError, "WIRING_CONFIRMED"):
                entry.run()
        self.assertFalse(pins)
        self.assertFalse(pwms)


if __name__ == "__main__":
    unittest.main()
