# Meeting timer wiring reference

Prepared 2026-09-13 for the teammate drawing the electrical schematic.
Firmware reference: [code/meeting_timer.py at commit 376af36](https://github.com/Spencer1701/Miniproject_1/blob/376af36/code/meeting_timer.py).

This is a drawing reference, not a fully traced as-built schematic. The team
reported working buttons, RGB fading, motor movement, and a combined timer
test. Those observations establish functionality but do not identify every
physical wire endpoint. Resolve the TODOs below before marking the drawing final.

The working firmware uses **fixed HIGH driver enables and no D7 connection**.
The retained modular firmware uses a different D7-controlled enable
arrangement. The current build is described in
[firmware notes](../docs/firmware.md); use this reference for its wiring.

Suggested component references: U1 = XIAO ESP32-S3, U2 = L293D, M1 = five-wire
28BYJ-48 stepper, SW1 = SET, SW2 = RUN, D1 = common-cathode RGB LED,
R1/R2/R3 = red/green/blue series resistors.

**XIAO connections**

| Function | U1 board label | MicroPython GPIO | Connect to |
| --- | --- | ---: | --- |
| Motor input 1 | D0 | 1 | U2 pin 2, 1A † |
| Motor input 2 | D1 | 2 | U2 pin 7, 2A † |
| Motor input 3 | D2 | 3 | U2 pin 10, 3A † |
| Motor input 4 | D3 | 4 | U2 pin 15, 4A † |
| SET | D4 | 5 | SW1 contact; its other contact goes to GND |
| RUN | D5 | 6 | SW2 contact; its other contact goes to GND |
| RGB red | D9 | 8 | R1, then D1 red anode |
| RGB green | D10 | 9 | R2, then D1 green anode |
| RGB blue | D8 | 7 | R3, then D1 blue anode |
| Unused control pins | D6, D7 | 43, 44 | No external control connection in this build |

The D-label/GPIO translation is from the [Seeed pin map](https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/).
GPIO numbers are not the XIAO module's physical pad numbers. The assignments
above match the tested firmware. **† The four driver-side input endpoints and
output wire colours below are the intended mapping in the code comments;
trace them on the breadboard to confirm the as-built drawing.** Sequence A
working does not by itself uniquely identify motor wire colours.

Both switches are normally open. The software enables internal pull-ups, so
an unpressed switch reads HIGH and pressing it connects the input to GND.
In the original XIAO-on-the-left layout, the earlier press order identified
the closer switch as SET and the farther switch as RUN. Use GPIO labels on
the schematic so the drawing remains clear if components are repositioned.

R1, R2 and R3 are nominally **220 ohms each** in the project notes.
**TODO: read the fitted resistor values before assigning final schematic values.**
Each colour has its own resistor. D1's common cathode connects directly to GND.
The active-high colour mapping was identified in the RGB test; the physical
left-to-right order of the four LED legs has not been established here.

**L293D connections — physical DIP pin numbers**

| U2 pin | Function | Connection in the drawing |
| ---: | --- | --- |
| 1 | 1,2EN | Existing fixed HIGH supply connection; TODO identify its rail |
| 2 | 1A | U1 D0 / GPIO1 † |
| 3 | 1Y | M1 orange wire † |
| 4 | GND | Common GND |
| 5 | GND | Common GND |
| 6 | 2Y | M1 pink wire † |
| 7 | 2A | U1 D1 / GPIO2 † |
| 8 | VCC2 | USB-powered +5V motor supply |
| 9 | 3,4EN | Existing fixed HIGH supply connection; TODO identify its rail |
| 10 | 3A | U1 D2 / GPIO3 † |
| 11 | 3Y | M1 yellow wire † |
| 12 | GND | Common GND |
| 13 | GND | Common GND |
| 14 | 4Y | M1 blue wire † |
| 15 | 4A | U1 D3 / GPIO4 † |
| 16 | VCC1 | USB-powered +5V logic supply |

Pin functions follow the [TI L293D datasheet, page 3](https://www.ti.com/lit/ds/symlink/l293.pdf#page=3).
**M1's fifth wire, red/common, connects to +5V**, not an L293D output.
All GND symbols denote one shared net connected to U1 GND.

U1 receives power through USB. Its **5V** pin supplies the breadboard's +5V
net; **3V3 is a different net**. See [Seeed's power-pin documentation](https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/#power-pins).
The pin-16 connection was corrected from 3V3 to 5V during troubleshooting.
The driver supply must be drawn at 5V, even if an enable input uses 3V3.

**TODO — enable rail:** Trace U2 pins 1 and 9 to determine whether their
existing fixed HIGH connection is +5V or 3V3. Either can satisfy the enable
input's HIGH threshold with 5V logic power, but the final schematic must show
the rail actually connected. Do not join the 5V and 3V3 rails. The working code
sets `MOTOR_ENABLE_GPIO = None`; there is no software-controlled enable wire.
The supply and logic limits are in the [TI datasheet, page 4](https://www.ti.com/lit/ds/symlink/l293.pdf#page=4).

**L293D orientation in the team's reported view**

Top view of the chip, notch facing RIGHT:

```text
         8   7   6   5   4   3   2   1
       +-------------------------------+
       |            L293D              )  notch
       +-------------------------------+
         9  10  11  12  13  14  15  16
```

This is a pin-location guide, not a circuit schematic. The numbered pin
functions remain the same regardless of how the chip is rotated on paper.

**Notes for the final drawing**

- Use electrical symbols and labelled connections; the course excludes Fritzing.
- Represent the RGB package as three LED junctions sharing one cathode, with
  one series resistor per anode. **TODO:** confirm its package leg order before
  assigning physical LED pin numbers or choosing a PCB footprint.
- Represent M1 as a five-wire unipolar motor, including its common connection.
  The selected driver input goes LOW to sink current from the +5V common.
- Annotate the actual enable rail after tracing it. Fixed enables do not provide
  high-impedance coil release; this build does not demonstrate coil-off sleep.
- TI recommends supply bypass capacitors of at least 0.1 microfarad at each
  driver supply pin. **TODO:** check whether capacitors are fitted. If absent,
  show them only as proposed additions until installed, not as existing parts.
  See [TI power-supply guidance, page 13](https://www.ti.com/lit/ds/symlink/l293.pdf#page=13).
- Export the schematic to PDF and save its editable source in
  `electrical/schematic/`. Keep the short folder README as the directory guide.

Use this table to prepare the final schematic in [schematic/](schematic/).
See the [operating instructions](../docs/operating-instructions.md) for button use.
