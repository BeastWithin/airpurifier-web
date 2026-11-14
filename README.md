# Philips Air Purifier web control

A small web server and kiosk page for Philips AirPerformer purifiers
(tested on AMF870/15) that talk over local CoAP. No cloud account needed.

## Requirements

- Python 3.10 or newer
- The purifier on the same network, with its IP address fixed (DHCP reservation)

## Setup

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run

```
AIRPURIFIER_HOST=192.168.1.50 .venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000
```

Replace `192.168.1.50` with your purifier's IP. Open `http://<this-machine>:8000`
on any device on the same network.

There is no authentication. Keep it on your LAN.

## API

- `GET /api/summary`: all settings in one response
- `GET /api/status`: raw device status
- `GET /api/mode`: power, mode, fan level
- `POST /api/power/{on|off}`
- `POST /api/mode/{auto|sleep|turbo}`
- `POST /api/fan/{1..10}`
- `POST /api/swing/{0..350}`
- `POST /api/brightness/{0..100}`
- `POST /api/timer/{code}` (0 off, 1 = 30 min, 13 = 12 h)
- `POST /api/childlock/{on|off}`
- `POST /api/beep/{on|off}`
- `POST /api/standby/{on|off}`
- `POST /api/smart/{on|off}` (auto+)
- `POST /api/reference-index/{allergen|pm25|gas}`

The meaning of each status code is in [PROTOCOL.md](PROTOCOL.md).

## Tools

`tools/snapshot.py` saves a status snapshot to JSON, or diffs two snapshots.
Use it to map new settings: take a snapshot, change one setting in the app,
take another, and diff. It needs `AIRPURIFIER_HOST` set.

## Status

Verified on one AMF870/15. Timer values 2–12 and fan levels are not all checked.
Other models may use different codes.
