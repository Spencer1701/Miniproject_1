"""Hardware and timing configuration for the XIAO ESP32-S3 meeting timer.

GPIO numbers below are ESP32 numbers, not the D-labels printed on the XIAO.
Read docs/firmware.md before changing WIRING_CONFIRMED. The course hookup
table needs corrections; the actual assembled circuit has not been verified.
"""

# Set True only after checking the pin map, driver supply, and enable wiring.
WIRING_CONFIRMED = False
# Active-high RGB operation confirmed by the team's two-cycle bench test.
# False = common cathode to GND; True = common anode to 3V3.
RGB_COMMON_ANODE = False

# L293D inputs 1A/2A/3A/4A: pins 2/7/10/15; XIAO D0/D1/D2/D3.
# Output wires respectively: orange/pink/yellow/blue; motor red common to 5V.
MOTOR_GPIOS = (1, 2, 3, 4)
# A cyclic order for the nominal 28BYJ-48: orange, yellow, pink, blue.
# TODO: verify smooth rotation on your motor; wire colours can vary by supplier.
MOTOR_PHASE_ORDER = (0, 2, 1, 3)
MOTOR_ACTIVE_LEVEL = 0  # Common at +5V: the selected output must sink current.
# Connect BOTH enable pins (L293D 1 and 9) to D7; remove their supply jumper.
# D7 avoids the UART TX boot messages that could toggle D6 before main.py runs.
MOTOR_ENABLE_GPIO = 44
SET_GPIO = 5  # D4, normally-open switch to GND; internal pull-up.
RUN_GPIO = 6  # D5, normally-open switch to GND; also the light-sleep wake pin.
# Bench test: GPIO7 lit blue, GPIO9 green, and GPIO8 red.
RGB_GPIOS = (8, 9, 7)  # R/G/B = D9/D10/D8, each through its own 220-ohm resistor.

PRESET_MINUTES = (15, 20, 25, 30)
DIAL_MINUTES = 30  # Matches the printed face: 0/30 at the top, 15 at the bottom.
WARNING_REMAINING_MS = 5 * 60 * 1000
# Nominal full/wave steps, NOT the 4096 half-step convention.
# TODO: measure an output revolution and adjust for your motor's gear ratio.
STEPS_PER_REVOLUTION = 2048
MOTOR_DIRECTION = 1  # Change to -1 if a positive jog goes counterclockwise.
STEP_INTERVAL_MS = 10  # Conservative starting rate; no blocking motor loops.
COIL_SETTLE_MS = 30  # Release the enable pin between slow countdown steps.
CALIBRATION_JOG_STEPS = 8
CALIBRATION_REPEAT_MS = 160

DEBOUNCE_MS = 30
LONG_PRESS_MS = 1500
PWM_FREQUENCY_HZ = 1000
PULSE_PERIOD_MS = 1000
MAX_LED_DUTY = 32768  # 16-bit duty limit; resistors still limit peak LED current.
LED_UPDATE_MS = 20
LOOP_SLEEP_MS = 2
LIGHT_SLEEP_ENABLED = True  # Set False while debugging USB/Thonny connections.
IDLE_SLEEP_MS = 60 * 1000


def validate():
    """Reject unsafe or inconsistent configuration before creating GPIOs."""
    if not WIRING_CONFIRMED:
        raise ValueError("Check docs/firmware.md, then set WIRING_CONFIRMED=True")
    if type(RGB_COMMON_ANODE) is not bool:
        raise ValueError("Set RGB_COMMON_ANODE to True or False after checking LED")
    pins = MOTOR_GPIOS + RGB_GPIOS + (SET_GPIO, RUN_GPIO, MOTOR_ENABLE_GPIO)
    exposed = (1, 2, 3, 4, 5, 6, 7, 8, 9, 43, 44)
    if len(set(pins)) != len(pins) or any(pin not in exposed for pin in pins):
        raise ValueError("Use unique exposed XIAO GPIOs; D0 is GPIO1, not GPIO0")
    if len(MOTOR_GPIOS) != 4 or len(RGB_GPIOS) != 3:
        raise ValueError("Exactly four motor inputs and three RGB channels required")
    if tuple(sorted(MOTOR_PHASE_ORDER)) != (0, 1, 2, 3):
        raise ValueError("MOTOR_PHASE_ORDER must be a permutation of 0,1,2,3")
    if MOTOR_ACTIVE_LEVEL not in (0, 1) or MOTOR_DIRECTION not in (-1, 1):
        raise ValueError("Invalid motor polarity or direction")
    if not isinstance(STEPS_PER_REVOLUTION, int) or STEPS_PER_REVOLUTION < 4:
        raise ValueError("STEPS_PER_REVOLUTION must be a positive calibrated count")
    if PRESET_MINUTES != (15, 20, 25, 30) or DIAL_MINUTES != 30:
        raise ValueError("Keep the course presets and the 30-minute printed dial")
    intervals = (
        STEP_INTERVAL_MS,
        COIL_SETTLE_MS,
        DEBOUNCE_MS,
        LONG_PRESS_MS,
        CALIBRATION_REPEAT_MS,
        PWM_FREQUENCY_HZ,
        PULSE_PERIOD_MS,
        LED_UPDATE_MS,
        LOOP_SLEEP_MS,
        IDLE_SLEEP_MS,
    )
    if any(value <= 0 for value in intervals):
        raise ValueError("Timing constants must be positive")
    if LONG_PRESS_MS <= DEBOUNCE_MS or not 0 < MAX_LED_DUTY <= 65535:
        raise ValueError("Invalid button timing or LED duty limit")
    if not 0 < CALIBRATION_JOG_STEPS < STEPS_PER_REVOLUTION // 2:
        raise ValueError("Calibration jog must be less than half a revolution")
    if LIGHT_SLEEP_ENABLED and RUN_GPIO not in (1, 2, 3, 4, 5, 6, 7, 8, 9):
        raise ValueError("Light-sleep wake must use an exposed RTC-capable GPIO")
