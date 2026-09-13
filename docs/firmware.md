# Firmware and verification notes

The working program is **[code/meeting_timer.py](../code/meeting_timer.py)**.
It is a standalone MicroPython file for the current XIAO ESP32-S3 breadboard.
Save that program as `main.py` on the device for startup. The separate
`config.py`, `logic.py`, `hardware.py`, and repository `main.py` are retained
from the earlier modular implementation and are not dependencies of this file.

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

The local standalone checks covered duration selection, runtime cleanup, and
accelerated preset/pause/expiry behavior using fake hardware. They are not
physical timing measurements. The committed `tests/test_firmware.py` exercises
the retained modular version, not the standalone entry point; run those tests
from the repository root with `python3 -m unittest discover -s tests -v`.

**TODO: add standalone regression coverage to the repository.** Documentation
updates do not constitute a new hardware test. No complete real-duration timing
measurement, calibrated angular error, or measured power result is recorded.

## Remaining acceptance and submission items

- **TODO:** attach the clock hand and confirm its marks, rotation direction,
  clearance, and return to zero. A popsicle stick is allowed; this team has no
  MechEs, so enclosure CAD and printing are optional.
- **TODO:** record final checks for all presets, pause/resume, cancel, expiry,
  recalibration, and a reset during use. Compare at least one complete real-time
  run with a reference timer and report the observed error; the handout does
  not specify a numerical accuracy tolerance.
- **TODO:** demonstrate and document the handout's low-power outcome. Radios
  are off, but current has not been measured, driver enables remain HIGH, and
  light sleep is disabled. Do not report demonstrated coil-off sleep.
- **TODO:** finish the schematic PDF/editable source in
  [electrical/schematic/](../electrical/schematic/) after tracing the noted
  unknowns; the wiring table is not the finished schematic.
- **TODO:** add completed-device photos to [media/photos/](../media/photos/),
  and a shareable link in [media/README.md](../media/README.md) to a demo shorter
  than 10 seconds stored in the team Google Drive `/video` folder.
- **TODO:** confirm the team task board, each member's contributions and
  demonstration of uploading final code from their own laptop, both individual
  and team Blackboard repo-link submissions, and the next IDR demonstration.

The team has not adopted the optional prototype housing for submission.
Existing STL files remain available as optional design work; their physical
fit has not been tested. Project requirements and technical sources are listed
in [references](references.md).
