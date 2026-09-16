# Owen Zhang — ECE 463 Miniproject 1

This page collects my contribution files for the meeting timer project. My main
responsibility was software and hardware integration. The folder includes the
final program, software tests, project documentation, wiring-reference table,
and the mechanical designs developed during my work.

## Contribution files

| Area | Files and contribution |
| --- | --- |
| MicroPython firmware | [meeting_timer.py](code/meeting_timer.py): 15/20/25/30-minute presets, two-button controls, calibration, stepper positioning, and RGB PWM indication |
| Verification | [Tests](tests/README.md): automated checks of timer states, buttons, motor commands, LED behavior, and runtime cleanup |
| Device documentation | [Operating instructions](docs/operating-instructions.md), [one-page user guide](docs/meeting-timer-user-guide.pdf), [state chart](docs/state-chart.md), [firmware notes](docs/firmware.md), and [references](docs/references.md) |
| Electrical integration | [Wiring-reference table](electrical/wiring-reference.md) prepared to support the teammate drawing the final schematic |
| Printed design | [Compact clock face and three hand fits](mechanical/stl/mini_clock_face_and_hands.stl): the combined STL selected and printed for the project |
| Earlier mechanical iterations | [Flat lid](mechanical/stl/timer_lid_flat_v2.stl) and [base with small parts](mechanical/stl/timer_base_and_parts_v2.stl): optional enclosure prototypes retained as design history |
| Repository documentation | [Project summary](project-summary.md) and the short README files in each project folder |

## Integration work

I ran the physical button, RGB, and motor diagnostics and reported the results
used to refine the configuration. I identified the L293D logic-supply connection
to 3V3 and reported motor movement after the correction to USB 5V. I compared
motor phase sequences and reported the preferred sequence. With the printed
face fitted, I reported the reversed hand direction and investigated the RGB
color mismatch; the final pin check was blue, red, green for GPIO7, GPIO8, GPIO9.
Touching resistor leads were suspected as the cause of the earlier color issue.

The final software uses motor direction `-1`, RGB order `(8, 9, 7)`, and real-minute
timing. The software checks do not establish physical timing accuracy, power
consumption, or complete hardware acceptance. Outstanding measurements and
checks remain identified in the [firmware notes](docs/firmware.md).

## Team work and submission snapshot

The final KiCad schematic and the circuit photo were supplied by teammates.
They are referenced from these documents but are not included as my individual
work. The personal engineering logbook remains separate.

These files are a submission snapshot of the project at
[commit f658738](https://github.com/Spencer1701/Miniproject_1/commit/f658738).
The working team program remains in the repository's main `code/` folder;
maintain that version for future changes. Earlier modular code is available in
[commit 376af36](https://github.com/Spencer1701/Miniproject_1/tree/376af36/code).

To run this snapshot's software checks, open a terminal in this folder and run
`python3 -m unittest discover -s tests -v`. To run the device, open
`code/meeting_timer.py` in Thonny and press F5, or save it on the MicroPython
board as `main.py`.
