"""Hardware-independent timer, debouncing, and LED policy.

All durations are integer milliseconds. Callers supply ticks_diff so the same
logic runs under MicroPython's wrapping clock and deterministic desktop tests.
"""

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
