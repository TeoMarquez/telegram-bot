import asyncio
from state import heartbeat

async def heartbeat_loop():
    while True:
        try:
            heartbeat.tick()
        except Exception as e:
            print(f"[HEARTBEAT] error crítico: {e}")
            raise SystemExit(1)

        await asyncio.sleep(5)