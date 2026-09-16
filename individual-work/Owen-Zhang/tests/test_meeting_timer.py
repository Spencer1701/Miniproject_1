"""Regression checks for the standalone program actually run in Thonny.

Run from the repository root: python3 -m unittest discover -s tests -v
Fake I/O verifies software commands, not physical wiring or angular accuracy.
"""

import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "code"))
import meeting_timer as fw
import test_firmware as fakes


def make_timer(selected=0):
    cfg = fw.config
    timer = fw.MeetingTimer(
        tuple(m * cfg.MINUTE_MS for m in cfg.PRESET_MINUTES),
        cfg.DIAL_MINUTES * cfg.MINUTE_MS,
        cfg.STEPS_PER_REVOLUTION,
        fakes.ticks_diff,
        0,
    )
    timer.selected = selected
    timer.reset()
    return timer


class StandaloneTimerTests(unittest.TestCase):
    def test_real_durations_and_fixed_enable_profile(self):
        cfg = fw.config
        cfg.validate()
        self.assertFalse(fw.QUICK_TEST)
        self.assertEqual(make_timer().presets, (900000, 1200000, 1500000, 1800000))
        self.assertEqual(cfg.WARNING_REMAINING_MS, 300000)
        self.assertIsNone(cfg.MOTOR_ENABLE_GPIO)
        self.assertFalse(cfg.LIGHT_SLEEP_ENABLED)

    def test_twenty_minute_position_and_countdown_reverse_original_phase_motion(self):
        """Model the mounted direction reported by the user, not a measurement.

        The original negative phase sequence turned clockwise. Its inverse
        must place 20 at the dial's 20 mark and count counterclockwise to zero.
        """
        cfg = fw.config
        coils = [fakes.Pin() for _ in range(4)]
        motor = fw.WaveStepper(
            coils, None, cfg.MOTOR_PHASE_ORDER, cfg.MOTOR_ACTIVE_LEVEL,
            cfg.MOTOR_DIRECTION, cfg.STEPS_PER_REVOLUTION,
            cfg.STEP_INTERVAL_MS, cfg.COIL_SETTLE_MS, fakes.ticks_diff, 0,
        )
        motor.align(0)
        now, previous_phase, physical_angle = 0, 0, 0

        def move_to(target):
            nonlocal now, previous_phase, physical_angle
            motor.set_target(target)
            for _ in range(cfg.STEPS_PER_REVOLUTION + 10):
                if motor.is_settled():
                    return
                previous_position = motor.position
                now += cfg.STEP_INTERVAL_MS
                motor.update(now)
                if motor.position != previous_position:
                    active = [i for i, pin in enumerate(coils) if pin.value() == 0]
                    self.assertEqual(len(active), 1)
                    phase = cfg.MOTOR_PHASE_ORDER.index(active[0])
                    self.assertEqual((phase - previous_phase) % 4, 1)
                    physical_angle = (physical_angle - 1) % cfg.STEPS_PER_REVOLUTION
                    previous_phase = phase
            self.fail("Motor did not settle within one revolution plus dwell")

        timer = make_timer(selected=1)
        move_to(timer.target_steps())
        self.assertEqual(physical_angle, 1365)  # 20/30 revolution, not 10/30.
        timer.run_button(motor.is_settled())
        for elapsed in range(1000, 1200001, 1000):
            timer.update(elapsed)
            move_to(timer.target_steps())
            self.assertEqual(physical_angle, timer.target_steps())
        self.assertEqual(timer.state, fw.FINISHED)
        self.assertEqual(physical_angle, 0)

    def test_every_preset_stays_green_until_final_five_minutes(self):
        for selected in range(4):
            timer = make_timer(selected)
            timer.run_button(True)
            duration = timer.remaining_ms
            with self.subTest(preset=fw.config.PRESET_MINUTES[selected]):
                for elapsed in range(0, duration + 1, 1000):
                    timer.update(elapsed)
                    expected = "green" if timer.remaining_ms > 300000 else "red"
                    self.assertEqual(fw.indicator_color(timer, 300000), expected)

    def test_warning_boundary_and_pwm_command_agree(self):
        timer = make_timer(selected=1)
        timer.run_button(True)
        timer.state_elapsed_ms = 500  # Peak of the one-second fade.
        for remaining, color, rgb in (
            (1200000, "green", (0, 32768, 0)),
            (540000, "green", (0, 32768, 0)),
            (300001, "green", (0, 32768, 0)),
            (300000, "red", (32768, 0, 0)),
            (0, "red", (32768, 0, 0)),
        ):
            with self.subTest(remaining=remaining):
                timer.remaining_ms = remaining
                self.assertEqual(fw.indicator_color(timer, 300000), color)
                self.assertEqual(fw.indicator(timer, 1000, 32768, 300000), rgb)

    def test_calibration_selection_and_pause_keep_their_colors(self):
        timer = make_timer()
        timer.remaining_ms = 1000
        for state, color, rgb in (
            (fw.CALIBRATING, "purple", (32768, 0, 32768)),
            (fw.SELECTING, "blue", (0, 0, 32768)),
            (fw.PAUSED, "blue", (0, 0, 32768)),
        ):
            timer.transition(state)
            timer.state_elapsed_ms = 500
            self.assertEqual(fw.indicator_color(timer, 300000), color)
            self.assertEqual(fw.indicator(timer, 1000, 32768, 300000), rgb)
        timer.transition(fw.SELECTING)
        timer.state_elapsed_ms = 1500  # Gap after the default preset's one pulse.
        self.assertEqual(fw.indicator(timer, 1000, 32768, 300000), (0, 0, 0))
        self.assertEqual(fw.indicator_color(timer, 300000), "blue")

    def test_runtime_reports_revision_and_cleans_up_without_d7(self):
        modules, pins, pwms = fakes.RuntimeTests().make_runtime()
        with patch.dict(sys.modules, modules), patch("builtins.print") as printed:
            with self.assertRaises(KeyboardInterrupt):
                fw.run()
        printed.assert_any_call("Firmware:", fw.FIRMWARE_REVISION)
        self.assertNotIn(44, pins)
        self.assertTrue(all(pins[p].value() == 1 for p in fw.config.MOTOR_GPIOS))
        self.assertTrue(all(pins[p].value() == 0 for p in fw.config.RGB_GPIOS))
        self.assertEqual(len(pwms), 3)
        self.assertTrue(all(pwm.closed for pwm in pwms))


if __name__ == "__main__":
    unittest.main()
