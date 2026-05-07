from __future__ import annotations

 import asyncio
 import json
 import logging
 import websockets
 from typing import Optional, Callable

 logging.basicConfig(level=logging.INFO)
 logger = logging.getLogger("vd_client")

 class VDClient:
     def __init__(self, url: str, backoff: list[int], on_battery: Callable[[Optional[float], Optional[float]], None]):
         self.url = url
         self.backoff = backoff
         self.on_battery = on_battery
         self._task: Optional[asyncio.Task] = None
         self._stop = False

     async def start(self):
         self._stop = False
         self._task = asyncio.create_task(self._run())

     async def stop(self):
         self._stop = True
         if self._task:
             self._task.cancel()
             try:
                 await self._task
             except asyncio.CancelledError:
                 pass

     async def _run(self):
         attempt = 0
         while not self._stop:
             try:
                 logger.info(f"Connecting to Virtual Desktop at {self.url}")
                 async with websockets.connect(self.url, ping_interval=10, ping_timeout=5) as ws:
                     logger.info("Connected to Virtual Desktop Streamer")
                     attempt = 0
                     async for message in ws:
                         if self._stop:
                             break
                         try:
                             data = json.loads(message)
                             if data.get("type") == "controllers":
                                 left = data.get("leftBattery")
                                 right = data.get("rightBattery")
                                 # left/right can be None if controller off
                                 self.on_battery(left, right)
                         except (json.JSONDecodeError, KeyError, TypeError) as e:
                             logger.warning(f"Invalid controller message: {e}")
             except Exception as e:
                 logger.warning(f"VD WebSocket error: {e}")
             if self._stop:
                 break
             delay = self.backoff[min(attempt, len(self.backoff) - 1)]
             attempt += 1
             logger.info(f"Reconnecting in {delay}s (attempt {attempt})")
             await asyncio.sleep(delay)
