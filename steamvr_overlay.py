import logging
import asyncio
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("steamvr_overlay")

class SteamVROverlay:
    """Stub for OVR Toolkit WebSocket approach or native IVROverlay.
    Default disabled in config. Implement if overlay_enabled=True.
    For OVR Toolkit: connect to its WS and push battery gauges.
    """

    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self._task: Optional[asyncio.Task] = None

    async def start(self, state_getter):
        if not self.enabled:
            return
        logger.info("SteamVR overlay stub started (no-op). Implement real rendering here.")
        # Example: if using OVR Toolkit WS, connect and send JSON gauges periodically
        # async with websockets.connect("ws://localhost:XXXX") as ws:
        #     ...
        self._task = asyncio.create_task(self._run_stub(state_getter))

    async def _run_stub(self, state_getter):
        while True:
            s = await state_getter()
            # logger.debug(f"Overlay would render: {s}")
            await asyncio.sleep(5)

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("SteamVR overlay stopped")
