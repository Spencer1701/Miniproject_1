# Owen Zhang — ECE 463 Miniproject 1

My work focused on the MicroPython meeting-timer software, hardware integration
and testing, and the clock-face/hand and enclosure design iterations.

| Work | Files |
| --- | --- |
| Final MicroPython program | [meeting_timer.py](code/meeting_timer.py): timer presets, button controls, hand calibration, stepper motion, and RGB PWM |
| Printed compact design | [Clock face and hand set](3d-printing/mini_clock_face_and_hands.stl): square dial, LED opening, and three alternative hand fits |
| Earlier enclosure designs | [Flat lid](3d-printing/timer_lid_flat_v2.stl) and [base with small parts](3d-printing/timer_base_and_parts_v2.stl): prototype designs, not the selected print job |

I ran the physical button, RGB, and motor checks and reported the observations
used to refine the final configuration. The code uses real 15/20/25/30-minute
presets, motor direction `-1`, and RGB GPIO order `(8, 9, 7)`.

Supporting material stays in the shared repository: [software tests](../../tests/README.md),
[state chart](../../docs/state-chart.md), [operating instructions](../../docs/operating-instructions.md),
and [verification notes](../../docs/firmware.md). The final KiCad schematic and
circuit photo were supplied by teammates.
