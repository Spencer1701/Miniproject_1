# References and design sources

This list distinguishes assignment requirements, manufacturer/API references,
and observations from the team's own build. Documentation was reviewed against
`code/meeting_timer.py` in commit `376af36` on 2026-09-13.

## Course requirements

- **Mini-Project Instructions - Google Docs.pdf**, supplied course handout:
  page 1 gives outcomes and timer features; page 3 lists documentation and
  submission requirements; page 4 requires each student to demonstrate
  uploading final MicroPython code from their laptop; pages 5-6 discuss the
  kit; page 7 makes enclosure work conditional on MechEs being on the team.
  The current team has no MechEs, so a housing is not required. A mechanical
  clock hand is still required, and page 5 allows a popsicle stick.
- **02. Miniproject.pdf** (downloaded as `02.%20Miniproject.pdf`), course slides:
  slides 7-10 cover functionality, workflow, and deliverables; slide 16 gives
  the team and individual grading criteria. The slide deck's conditional
  enclosure requirement agrees with the detailed handout.

The course PDFs are supplied class materials, not currently included in this
repository. **TODO:** add course-accessible source links if available. The team
chose the button gestures, colour meanings, pause behavior, and fixed 30-minute
dial; these are explained in the operating instructions rather than presented
as additional course requirements.

## Hardware references

| Source | Used for |
| --- | --- |
| [Seeed Studio XIAO ESP32-S3 documentation](https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/) | D-label/GPIO translation and USB 5V versus regulated 3V3 power pins |
| [Texas Instruments L293/L293D datasheet](https://www.ti.com/lit/ds/symlink/l293.pdf) | Physical pin functions, supplies, logic levels, enable behavior, and bypass guidance; see pages 3-4, 7-8, and 13 |
| [28BYJ-48 reference drawing distributed by SparkFun](https://cdn.sparkfun.com/assets/8/e/0/8/e/step-motor-5v-28byj48-datasheet.pdf) | Nominal motor dimensions used in the optional enclosure work; not identification or fit certification of the team's motor |

The SparkFun-hosted motor PDF was consulted during CAD preparation; it could
not be retrieved again during the latest online link check. Its local copy
and earlier optional CAD work are not required for the no-housing submission.

The handout's hookup notes need corrections for this build: XIAO D0-D3 mean
GPIO1-GPIO4; L293D logic pin 16 uses 5V; and a motor common at +5V requires
active-LOW winding selection. The current build retains fixed HIGH enables
instead of the earlier proposed D7 control wire. These choices are documented
in the [wiring reference](../electrical/wiring-reference.md). The driver's
supply and noninverting output behavior follow the TI reference above.

## MicroPython references

| Official source | Used for |
| --- | --- |
| [XIAO ESP32-S3 firmware downloads](https://micropython.org/download/SEEED_XIAO_ESP32S3/) | Board-specific MicroPython firmware selection |
| [Pin API](https://docs.micropython.org/en/latest/library/machine.Pin.html) | GPIO input/output and button pull-ups |
| [PWM API](https://docs.micropython.org/en/latest/library/machine.PWM.html) | RGB duty-cycle control |
| [Time API](https://docs.micropython.org/en/latest/library/time.html) | `ticks_ms()`, wrap-safe `ticks_diff()`, and loop delays |
| [Reset and boot sequence](https://docs.micropython.org/en/latest/reference/reset_boot.html) | Running the saved `main.py` program after startup |
| [Machine power APIs](https://docs.micropython.org/en/latest/library/machine.html) and [ESP32 APIs](https://docs.micropython.org/en/latest/library/esp32.html) | Background for the retained sleep/wake implementation; sleep is disabled in the current build |

The `/latest/` API pages describe MicroPython's development documentation;
select the matching release documentation when checking firmware-specific
behavior. **TODO:** record the exact installed board firmware version in the
final test notes. The compiler version used locally does not identify the
firmware installed by the team.

## Team observations and assistance

The RGB GPIO colour assignment and preferred motor phase order came from the
team's bench observations, not from a generic LED or motor package drawing.
Photo review alone did not establish every driver wire endpoint, LED package
leg number, or the fixed enable rail. The [wiring reference](../electrical/wiring-reference.md)
marks these trace checks; [firmware notes](firmware.md) separate recorded
observations from outstanding measurements.

The code, documentation, and optional enclosure prototypes were prepared with
AI assistance. The team ran the physical tests described in the notes and is
responsible for final review and demonstration. No source above establishes
an unmeasured timing, power, or mechanical-fit result for this device.
