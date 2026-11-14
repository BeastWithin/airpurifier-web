"""Save a device status snapshot to JSON, or diff two snapshots. Read-only."""
import asyncio, json, sys
import aioairctrl

import os
HOST = os.environ["AIRPURIFIER_HOST"]

async def take(path):
    c = await aioairctrl.CoAPClient.create(HOST)
    try:
        status, _ = await c.get_status()
    finally:
        await c.shutdown()
    with open(path, "w") as f:
        json.dump(status, f, indent=1, sort_keys=True)
    print("saved", path, len(status), "keys")

if __name__ == "__main__":
    if sys.argv[1] == "take":
        asyncio.run(take(sys.argv[2]))
    else:  # diff a b
        a = json.load(open(sys.argv[2])); b = json.load(open(sys.argv[3]))
        for k in sorted(set(a) | set(b)):
            if a.get(k) != b.get(k):
                print(f"{k}: {a.get(k)!r} -> {b.get(k)!r}")
