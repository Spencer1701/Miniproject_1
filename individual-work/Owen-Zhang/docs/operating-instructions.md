# Operating instructions

The meeting timer offers 15, 20, 25, and 30 minute presets. A motor-driven hand
shows the remaining time, and an RGB LED indicates the operating state. It
uses USB power and operates with two buttons. The printed compact face has a
0/30 mark at the top and clockwise-increasing minute labels. Install one of
the printed hand fits on the motor; a full enclosure is not needed.

## Identify the buttons

In the team's current breadboard layout, viewed with the XIAO on the left:

- **SET** is closer to the XIAO (D4/GPIO5).
- **RUN** is farther from the XIAO (D5/GPIO6).

Label the buttons if the layout changes. A tap is a short press and release.
A hold lasts about **1.5 seconds**. Long presses do not also count as taps.

## Start a meeting

1. Connect USB power. The LED pulses **purple**, meaning the hand needs its
   zero position set. Keep both buttons released during startup.
2. Tap **SET** to jog the hand forward, or hold SET to keep jogging. Tap
   **RUN** to jog it back. Use these controls to align the hand with **0/30**;
   do not force the motor shaft by hand.
3. Once the hand stops at zero, hold **RUN for 1.5 seconds**, then release it.
   Blue pulses indicate preset selection. The first preset is **15 minutes**.
4. Tap **SET** to cycle 15 → 20 → 25 → 30 → 15 minutes. Count the blue pulses
   in each repeating group: one, two, three, or four respectively. Each group
   is followed by a two-second gap.
5. Wait for the hand to finish moving to the selected preset. The initial
   move to 15 minutes takes approximately 27 seconds. Then tap **RUN** to
   start the countdown. A RUN tap made before positioning finishes is ignored;
   wait and tap again.

The scale represents 30 minutes per full revolution, so 15 minutes is opposite
zero. The 30-minute and zero positions share the same angle; use the LED state
to distinguish selecting/running from finished. The hand moves from the preset
counterclockwise toward zero with the final motor-direction setting. Establish
zero again after changing motor direction or repositioning the hand.

## Preset press counts

The current program offers **15, 20, 25, and 30 minutes; there is no 10-minute preset**.
After a fresh power-up and zero calibration, 15 minutes is already selected:

| Duration | Additional SET taps from the initial 15-minute selection | Blue pulses per group | Start |
| --- | --- | --- | --- |
| 15 minutes | 0 | 1 | Tap RUN once after the hand stops |
| 20 minutes | 1 | 2 | Tap RUN once after the hand stops |
| 25 minutes | 2 | 3 | Tap RUN once after the hand stops |
| 30 minutes | 3 | 4 | Tap RUN once after the hand stops |

Each SET tap advances one preset, wrapping from 30 back to 15. After canceling
or recalibrating during use, the current preset is retained; count the blue
pulses to identify it rather than assuming it has returned to 15 minutes.

## Pause, cancel, or start another meeting

| Action | Control |
| --- | --- |
| Pause a running countdown | Tap RUN; the LED pulses blue |
| Resume | Once the hand settles, tap RUN again |
| Cancel and reload the selected preset | Hold RUN for 1.5 seconds; wait for positioning, then tap RUN to restart |
| Choose a different preset | While selecting or finished, tap SET |
| Set the hand zero again | Hold SET for 1.5 seconds to enter purple calibration mode |
| Acknowledge a finished countdown | Tap RUN to reload the same preset, or tap SET to select the next one |

During calibration, holding SET continues jogging instead of changing modes.
SET taps do nothing during a running or paused countdown. Holding both buttons
together suppresses their actions until both are released; it does not pause
a running countdown.

## Read the LED

| LED indication | Meaning |
| --- | --- |
| Purple pulse | Calibrate the hand zero |
| Groups of 1/2/3/4 blue pulses | Select 15/20/25/30 minutes |
| Green pulse | Running with more than five minutes left |
| Red pulse while the hand counts down | Five minutes or less remain |
| Repeating blue pulse | Paused |
| Red pulse with the hand at zero | Finished; acknowledge or select another preset |

The brightness rises and falls once per second. Red continues pulsing after
completion; there is no buzzer. Disconnect USB to turn the device off. Every
power-up or board reset requires hand calibration again; a previous countdown
is not recovered. Holding RUN to cancel a meeting keeps the existing zero.

## Install or run the program with Thonny

Use [code/meeting_timer.py](../code/meeting_timer.py), the standalone program
for this breadboard. In Thonny, select the connected ESP32 MicroPython device,
open that file and press **F5**. It needs no additional project Python files
on the board. To run at power-up, save this program to the MicroPython device's
filesystem root under the name **main.py**, then reset the board. This uses
MicroPython's [startup script behavior](https://docs.micropython.org/en/latest/reference/reset_boot.html).

Keep `QUICK_TEST = False` for real 15/20/25/30-minute operation. Setting it to
`True` is an explicitly accelerated test: those four labels instead run for
30/40/50/60 seconds, with the red warning starting at 10 seconds remaining.
The console announces which mode is active.

When Thonny is connected, status lines appear about every five seconds.
`hand: ready` means the hand has reached its current target between steps;
it does not mean the meeting is over. Small motor ticks about once per second
are expected in real-minute mode. Ctrl+C stops the program; disconnect USB
after testing because the fixed-enable motor driver remains powered.

See the [state chart](state-chart.md) for the complete control model and
[firmware notes](firmware.md) for verification status and remaining checks.
