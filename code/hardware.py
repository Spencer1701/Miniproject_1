"""Small, nonblocking drivers; pin/PWM objects are injected for desktop tests."""


class WaveStepper:
    """Drive a four-phase unipolar motor through a noninverting L293D.

    Both enable pins share a GPIO so release() makes all outputs high impedance.
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
        """Disable the driver before changing its inputs; preserve step count."""
        self.enable.value(0)
        for pin in self.pins:
            pin.value(1 - self.active)
        self.energized = False

    def _energize(self, now):
        # Break before make prevents a transient two-coil phase during updates.
        self.enable.value(0)
        for pin in self.pins:
            pin.value(1 - self.active)
        self.pins[self.order[self.phase]].value(self.active)
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
