# Philips AirPerformer (AMF870/15) control map

Local CoAP on UDP 5683, encrypted with the key handshake in `aioairctrl`.
Status values use Philips' internal codes. The map below comes from diffing
status snapshots while changing one setting at a time in the Air+ app.

Writes are sent with `aioairctrl`'s `set_control_values()`. The device
accepts a write even when it doesn't apply it, so always read status back.

## Status keys

| Key | Meaning | Values | Confidence |
|---|---|---|---|
| `D03102` | Power | 0 off, 1 on | verified (write + app) |
| `D0310C` | Fan / mode | 0 Auto, 1–10 manual fan level, 17 Sleep, 18 Turbo | verified (write + app) |
| `D0310D` | Current fan level (read-only echo) | follows `D0310C` | observed |
| `D03120` | Mode, unreliable | 1 Sleep, 2 Auto (in some reads only) | not used |
| `D0320F` | Swing angle | 0 off, up to 350 | verified (write + app) |
| `D0312F` | Display brightness | 0–100 % | verified (write + app) |
| `D03110` | Timer | 0 off, 1 = 30 min, 13 = 12 h | 0, 1, 13 verified; 2–12 not |
| `D03103` | Child lock | 0 off, 1 on | verified (toggled both ways) |
| `D03130` | Beep sound | 0 off, 100 on | verified (toggled both ways) |
| `D03134` | Watch sensors on standby | 0 off, 1 on | verified (toggled both ways) |
| `D03180` | Auto+ smart service | 0 Auto, 1 Auto+ | verified (toggled both ways) |
| `D0312A` | Preferred reference index | 0 indoor allergen, 1 PM2.5, 2 gas | verified (all three in app) |
| `D01S03` | Device name (read-only) | text | observed |
| `D01S05` | Model (read-only) | e.g. `AMF870/15` | observed |
| `D03221`, `D03224`, `D03125`, `D03122`, `D03106` | Sensor readings / counters | change over time | not mapped |

## Mode writes

Sending the mode alone is not enough for Sleep and Auto. The app writes both keys:

- Sleep: `D03120=1`, `D0310C=17`
- Auto: `D03120=2`, `D0310C=0`
- Turbo: `D0310C=18`
- Manual fan level: `D0310C=1..10`

## Read-only data

`D05207`, `D05408`, `D0540E`, `D05102`, `D0520D` and `D01R22`/`D01R32`/`D01R42`
look like firmware and runtime counters. They are not mapped.
