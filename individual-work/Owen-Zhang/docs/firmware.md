# Firmware and verification notes

The working program is **[code/meeting_timer.py](../code/meeting_timer.py)**.
It is a standalone MicroPython file for the current XIAO ESP32-S3 breadboard.
Save that program as `main.py` on the device for startup. It needs no supporting
Python files. The superseded modular implementation is preserved in Git history.

Read the [operating instructions](operating-instructions.md),
[state chart](state-chart.md), [wiring reference](../electrical/wiring-reference.md),
and [sources](references.md) alongside these notes.

## Current configuration

| Setting | Value or behavior |
| --- | --- |
| Timing | `QUICK_TEST = False`: 15, 20, 25, 30 minutes |
| Dial | Fixed 30-minute revolution; nominal 2048 wave steps per revolution |
| Motor GPIOs | `(1, 2, 3, 4)` = XIAO D0-D3 |
| Phase order | `(0, 2, 1, 3)` = test sequence A; selected phase LOW |
| Motor direction | `-1`: reversed for the mounted dial; physical recheck pending |
| Motor step interval | At least 25 ms while positioning; no catch-up bursts |
| Final phase dwell | 100 ms before removing the active phase command |
| Driver enables | Fixed HIGH; `MOTOR_ENABLE_GPIO = None`; D7 unused |
| Buttons | SET D4/GPIO5; RUN D5/GPIO6; active-low with internal pull-ups |
| RGB | Red GPIO8, green GPIO9, blue GPIO7; common cathode to GND |
| LED timing | 1 kHz PWM, brightness pulse period 1000 ms |
| Warning | Red at five minutes remaining and after completion |
| Low power | Wi-Fi/Bluetooth disabled; `LIGHT_SLEEP_ENABLED = False` |

The L293D's logic supply (pin 16), motor supply (pin 8), and motor red common
use USB-powered 5V. Logic pin 16 was corrected from 3V3 during commissioning.
The enable pins stay tied HIGH; confirm their actual fixed rail for the final
schematic. Their driver outputs do not become high impedance when phase
commands stop. Refer to the [wiring reference](../electrical/wiring-reference.md)
for pin numbers, remaining trace checks, and datasheet sources.

The countdown uses elapsed `ticks_ms()` time with `ticks_diff()`, independently
of motor pulse counting. These APIs are described in the
[MicroPython time reference](https://docs.micropython.org/en/latest/library/time.html).
With the nominal dial calibration, real-time countdown stepping averages
1800/2048 = approximately **0.879 seconds per step**, regardless of the preset.
The 25 ms minimum interval is for faster positioning moves. The motor has no
position sensor, so `hand: ready` reports the commanded position, not a measured
shaft position or proof that no steps were missed.

## Recorded verification

| Evidence | What it establishes |
| --- | --- |
| Team-reported button diagnostic | GPIO5 and GPIO6 each registered press and release |
| Team-reported RGB diagnostic | Red/green/blue GPIO mapping corrected; smooth fading confirmed |
| Team-reported motor test | Sequence A at 25 ms gave relatively smooth approximate 180-degree outward/return travel |
| Team-reported combined test | The team reported that the combined timer was working well; a detailed per-control result sheet was not recorded |
| Thonny inspection | `QUICK_TEST = False` visible; running status decreased 438 → 433 → 428 seconds; no error visible in that inspected log |
| Prior software checks | 31 modular regression tests and four additional local standalone checks passed; standalone MicroPython cross-compilation passed |

The earlier local standalone checks covered duration selection, runtime cleanup,
and accelerated preset/pause/expiry behavior using fake hardware. The repository
now also includes `tests/test_meeting_timer.py` for the standalone entry point:
direction commands for the 20-minute dial position/countdown, all real preset
durations, the exact five-minute LED boundary, state colors, and runtime cleanup.
These are software checks, not physical timing measurements.

Both `tests/test_firmware.py` and `tests/test_meeting_timer.py` now exercise the
final standalone program. All 37 desktop tests passed during final preparation;
MicroPython cross-compilation also passed. Run the suite from the repository
root with `python3 -m unittest discover -s tests -v`.
No complete real-duration timing measurement, calibrated angular error, or
measured power result is recorded.

## Mounted dial correction (2026-09-15)

The team reported that selecting 20 minutes put the hand at 10 and the hand
counted clockwise. The standalone program now reverses `MOTOR_DIRECTION` to
`-1`, preserving the phase order and elapsed-time countdown. **TODO: run this
revision, establish zero again, and verify 20 positions at 20 and counts
counterclockwise toward zero on the physical dial.**

The team also reported red immediately after starting, including above five
minutes remaining. Software still commands green above five minutes and red
at or below five. Thonny now prints the firmware revision and `LED command`
alongside the remaining seconds. The final pin check was reported as
**GPIO7 blue, GPIO8 red, GPIO9 green**. The team suspected touching resistor
leads caused the earlier anomalous colors; that cause was not independently
measured. The original RGB order `(8, 9, 7)` and five-minute threshold remain
unchanged. **TODO: confirm the full countdown after separating the leads.**

## Remaining acceptance and submission items

- **TODO:** confirm the mounted hand's marks, rotation direction,
  clearance, and return to zero. A popsicle stick is allowed; this team has no
  MechEs, so enclosure CAD and printing are optional.
- **TODO:** record final checks for all presets, pause/resume, cancel, expiry,
  recalibration, and a reset during use. Compare at least one complete real-time
  run with a reference timer and report the observed error; the handout does
  not specify a numerical accuracy tolerance.
- **TODO:** demonstrate and document the handout's low-power outcome. Radios
  are off, but current has not been measured, driver enables remain HIGH, and
  light sleep is disabled. Do not report demonstrated coil-off sleep.
- The team has supplied the [schematic PDF and KiCad source](../electrical/schematic/README.md).
  **TODO:** complete any physical trace checks still noted in the wiring reference
  and schematic changelog; file availability is not a new circuit verification.
- A [wiring photo](https://github.com/Spencer1701/Miniproject_1/blob/f6587380df12e8161d03274974bbdce6dfd4fb5e/wiring/wiring.jpg) is available. **TODO:** add a final
  assembled-device photo with the printed face and hand to [media/photos/](../media/photos/),
  and a shareable link in [media/README.md](../media/README.md) to a demo shorter
  than 10 seconds stored in the team Google Drive `/video` folder.
- **TODO:** confirm the team task board, each member's contributions and
  demonstration of uploading final code from their own laptop, both individual
  and team Blackboard repo-link submissions, and the next IDR demonstration.

The selected print job is the [compact clock face and three hand fits](../mechanical/stl/mini_clock_face_and_hands.stl).
The team reports printing that design; the selected hand fit, actual slicer
settings, and measured print time have not been recorded. The earlier full
enclosure STL files remain optional prototypes with unverified fit. Project requirements and technical sources are listed
in [references](references.md).
