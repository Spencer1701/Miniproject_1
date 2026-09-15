# Schematic Changelog — Meeting Timer Mini-Project

Documents changes made to `Mini-project.kicad_sch` after the initial (v1) version, and why each was made.

## v1 → v2 Corrections

### 1. RGB LED representation — switched to a single common-cathode symbol
- **Before:** The schematic modeled the RGB LED as three separate Device:LED symbols (D1/D2/D3), requiring their cathodes to be manually netted together. D2's cathode originally had no connection at all — that color channel's circuit was open as drawn.
- **After:** Replaced with a single Device:LED_KRGB symbol (one designator, matching the team's "D1" convention) — a standard common-cathode RGB LED part with three anode pins (one per color) and one shared cathode pin built directly into the part.
- **Why:** wiring-reference.md identifies this as one physical common-cathode RGB LED package, not three independent LEDs. Using the dedicated library symbol represents that accurately, removes the need to manually tie three separate cathode nets together, and resolves the earlier D1/D2/D3-vs-single-"D1" designator mismatch.

### 2. Button 1 (SW1) ground connection
- **Before:** SW1 pin 2 was tied to the LED cathode net instead of ground.
- **After:** SW1 pin 2 now connects to GND, matching how SW2 (Button 2) was already wired.
- **Why:** `wiring-reference.md`: *"an unpressed switch reads HIGH and pressing it connects the input to GND"* — both switches need their own dedicated GND return.

### 3. Red/Blue LED GPIO assignment swap
- **Before:** R3 (Red LED resistor) → GPIO7 (D8); R2 (Blue LED resistor) → GPIO8 (D9) — matched the generic course example table.
- **After:** Swapped so Red → GPIO8 (D9), Blue → GPIO7 (D8).
- **Why:** `wiring-reference.md`'s hookup table is sourced from the team's actual tested, working firmware [commit 376af36], which uses the opposite assignment from the course's generic example. The tested build takes precedence over the generic reference.


## Documentation additions (not circuit changes)

- Added net labels (GPIO, SET, RUN, U1, U2 , J1 etc) for schematic readability.

## Still open
- Noted 0.1µF bypass capacitors at VCC1/VCC2 as **proposed, not yet installed** — pending physical confirmation, per TI's datasheet guidance (p.13) and `wiring-reference.md`'s TODO.



