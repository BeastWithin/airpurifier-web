"""Minimal web server for a Philips AirPerformer (AMF870/15) over local CoAP.

Run:  AIRPURIFIER_HOST=<device-ip> uvicorn server:app --host 0.0.0.0 --port 8000
See README.md and PROTOCOL.md.
"""
import os

import aioairctrl
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

DEVICE_HOST = os.environ.get("AIRPURIFIER_HOST")
if not DEVICE_HOST:
    raise SystemExit("Set AIRPURIFIER_HOST to the purifier's IP address (see README.md)")

app = FastAPI(title="Philips Air Purifier")


async def read_status() -> dict:
    client = await aioairctrl.CoAPClient.create(DEVICE_HOST)
    try:
        status, _ = await client.get_status()
        return status
    except Exception as exc:  # network / handshake failure
        raise HTTPException(status_code=502, detail=f"device unreachable: {exc}")
    finally:
        await client.shutdown()


@app.get("/api/status")
async def status():
    """Raw device status (keys are Philips' internal codes)."""
    return await read_status()


@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "kiosk.html"))


# ---- control -------------------------------------------------------------
# Verified by diffing status while changing settings in the Air+ app:
#   D03102: power      (0 = off, 1 = on)
#   D03120: mode       (1 = sleep, 2 = auto)
#   D0310D: fan level  (1 in sleep, 3 in auto)
# Mode is written as a pair (the Air+ app sends both keys). Verified against the app:
#   sleep -> D03120=1, D0310C=17     auto -> D03120=2, D0310C=0
# Read the current mode from D0310C (0 = auto, 17 = sleep): D03120 is not reliable.
#   manual fan level: D0310C = 1..10 (device reports up to 10; verified 1, 2 and 10 in app)
MODES = {
    "sleep": {"D03120": 1, "D0310C": 17},
    "auto": {"D03120": 2, "D0310C": 0},
    "turbo": {"D0310C": 18},  # confirmed by write: app showed Turbo
}


async def write_control(data: dict) -> None:
    client = await aioairctrl.CoAPClient.create(DEVICE_HOST)
    try:
        ok = await client.set_control_values(data)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"write failed: {exc}")
    finally:
        await client.shutdown()
    if not ok:
        raise HTTPException(status_code=502, detail=f"device rejected {data}")


@app.get("/api/mode")
async def get_mode():
    s = await read_status()
    code = s["D0310C"]
    if code == 17:
        mode = "sleep"
    elif code == 18:
        mode = "turbo"
    elif code == 0:
        mode = "auto"
    else:
        mode = f"manual"
    return {
        "power": s["D03102"] == 1,
        "mode": mode,
        "fan_level": code if mode == "manual" else None,
    }


@app.get("/api/summary")
async def summary():
    """Decoded settings for the kiosk page (one device read)."""
    s = await read_status()
    code = s["D0310C"]
    if code == 17:
        mode = "sleep"
    elif code == 18:
        mode = "turbo"
    elif code == 0:
        mode = "auto"
    else:
        mode = "manual"
    return {
        "name": s.get("D01S03"),
        "model": s.get("D01S05"),
        "power": s["D03102"] == 1,
        "mode": mode,
        "fan_level": code if mode == "manual" else None,
        "swing_degrees": s["D0320F"],
        "brightness": s["D0312F"],
        "timer_code": s["D03110"],
        "child_lock": s["D03103"] == 1,
        "beep": s["D03130"] > 0,
        "standby_sensors": s["D03134"] == 1,
        "auto_plus": s["D03180"] == 1,
        "reference_index": {0: "allergen", 1: "pm25", 2: "gas"}.get(s["D0312A"], "unknown"),
    }


@app.post("/api/power/{state}")
async def power(state: str):
    if state not in ("on", "off"):
        raise HTTPException(status_code=400, detail="state must be on or off")
    await write_control({"D03102": 1 if state == "on" else 0})
    return {"power": state}


@app.post("/api/mode/{mode}")
async def mode(mode: str):
    if mode not in MODES:
        raise HTTPException(status_code=400, detail=f"mode must be one of {list(MODES)}")
    await write_control(MODES[mode])
    return {"mode": mode}


@app.post("/api/fan/{level}")
async def fan(level: int):
    if not 1 <= level <= 10:
        raise HTTPException(status_code=400, detail="level must be 1 to 10")
    await write_control({"D0310C": level})
    return {"fan_level": level}


@app.post("/api/swing/{degrees}")
async def swing(degrees: int):
    # D0320F = swing angle (0 when off; app allows up to 350)
    if not 0 <= degrees <= 350:
        raise HTTPException(status_code=400, detail="degrees must be 0 to 350")
    await write_control({"D0320F": degrees})
    return {"swing_degrees": degrees}


@app.post("/api/brightness/{percent}")
async def brightness(percent: int):
    # D0312F = display brightness in percent (verified 10 and 100 in app)
    if not 0 <= percent <= 100:
        raise HTTPException(status_code=400, detail="percent must be 0 to 100")
    await write_control({"D0312F": percent})
    return {"brightness": percent}


@app.post("/api/timer/{code}")
async def timer(code: int):
    # D03110 = timer option. Verified: 1 = 30 min, 13 = 12 h (from app).
    # 0 = off and 2..12 (1h..11h) are inferred, not yet verified.
    if not 0 <= code <= 13:
        raise HTTPException(status_code=400, detail="code must be 0 to 13")
    await write_control({"D03110": code})
    return {"timer_code": code}


@app.post("/api/childlock/{state}")
async def childlock(state: str):
    # D03103 = child lock (inferred from status diff; not yet confirmed by toggling off)
    if state not in ("on", "off"):
        raise HTTPException(status_code=400, detail="state must be on or off")
    await write_control({"D03103": 1 if state == "on" else 0})
    return {"child_lock": state}


@app.post("/api/smart/{state}")
async def smart(state: str):
    # D03180 = "auto+" smart service (fan by air quality, sleep at night).
    # Changed 0 -> 1 when the app went from "auto" to "auto+" (inferred, not toggled back yet).
    if state not in ("on", "off"):
        raise HTTPException(status_code=400, detail="state must be on or off")
    await write_control({"D03180": 1 if state == "on" else 0})
    return {"auto_plus": state}


@app.post("/api/beep/{state}")
async def beep(state: str):
    # D03130 = beep volume-style value: 100 = on, 0 = off (verified in app both ways)
    if state not in ("on", "off"):
        raise HTTPException(status_code=400, detail="state must be on or off")
    await write_control({"D03130": 100 if state == "on" else 0})
    return {"beep": state}


@app.post("/api/standby/{state}")
async def standby(state: str):
    # D03134 = watch sensors on standby (verified: off -> 0, back on -> 1)
    if state not in ("on", "off"):
        raise HTTPException(status_code=400, detail="state must be on or off")
    await write_control({"D03134": 1 if state == "on" else 0})
    return {"standby_sensors": state}


@app.post("/api/reference-index/{index}")
async def reference_index(index: str):
    # D0312A = preferred reference index: 0 = indoor allergen, 1 = PM2.5, 2 = gas
    # (inferred from the app changes; not yet confirmed by switching back to 0).
    codes = {"allergen": 0, "pm25": 1, "gas": 2}
    if index not in codes:
        raise HTTPException(status_code=400, detail=f"index must be one of {list(codes)}")
    await write_control({"D0312A": codes[index]})
    return {"reference_index": index}
