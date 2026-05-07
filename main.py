from __future__ import annotations

 import asyncio
 import logging
 import signal
 import sys
 from pathlib import Path

 import yaml

 from vd_client import VDClient
 from osc_sender import OSCSender
 from oscquery_server import OSCQueryServer
 from steamvr_overlay import SteamVROverlay

 logging.basicConfig(
     level=logging.INFO,
     format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
 )
 logger = logging.getLogger("main")

 CONFIG_PATH = Path(__file__).parent / "config.yaml"

 class BatteryState:
     def __init__(self, low_threshold: float):
         self.left: float | None = None
         self.right: float | None = None
         self.low_threshold = low_threshold
         self._lock = asyncio.Lock()

     async def update(self, left: float | None, right: float | None):
         async with self._lock:
             self.left = left
             self.right = right

     async def get(self) -> dict:
         async with self._lock:
             low = False
             if self.left is not None and self.left < self.low_threshold:
                 low = True
             if self.right is not None and self.right < self.low_threshold:
                 low = True
             return {
                 "left": self.left,
                 "right": self.right,
                 "low": low
             }

 async def poll_sender(state: BatteryState, sender: OSCSender, interval: float):
     while True:
         try:
             s = await state.get()
             sender.send_battery(s["left"], s["right"], s["low"])
         except Exception as e:
             logger.error(f"Poll sender error: {e}")
         await asyncio.sleep(interval)

 async def main():
     # Load config
     with open(CONFIG_PATH, "r") as f:
         cfg = yaml.safe_load(f)

     vd_url = cfg["vd_ws_url"]
     backoff = cfg["vd_reconnect_backoff_s"]
     osc_ip = cfg["osc_target_ip"]
     osc_port = cfg["osc_target_port"]
     http_port = cfg["oscquery_http_port"]
     service_name = cfg["oscquery_service_name"]
     poll_interval = cfg["poll_interval_s"]
     low_thresh = cfg["low_battery_threshold"]
     overlay_enabled = cfg.get("overlay_enabled", False)

     logger.info("Starting Quest Pro Battery Monitor prototype")

     state = BatteryState(low_thresh)
     sender = OSCSender(osc_ip, osc_port)

     def on_battery(left: float | None, right: float | None):
         asyncio.create_task(state.update(left, right))

     vd = VDClient(vd_url, backoff, on_battery)
     oscq = OSCQueryServer(http_port, service_name, osc_port, state.get)
     overlay = SteamVROverlay(overlay_enabled)

     # Start components
     await vd.start()
     await oscq.start()
     await overlay.start(state.get)

     poll_task = asyncio.create_task(poll_sender(state, sender, poll_interval))

     logger.info("Bridge running. Press Ctrl+C to stop.")

     # Graceful shutdown
     stop_event = asyncio.Event()

     def _signal_handler():
         logger.info("Shutdown signal received")
         stop_event.set()

     loop = asyncio.get_running_loop()
     for sig in (signal.SIGINT, signal.SIGTERM):
         try:
             loop.add_signal_handler(sig, _signal_handler)
         except NotImplementedError:
             # Windows
             pass

     await stop_event.wait()

     # Cleanup
     poll_task.cancel()
     try:
         await poll_task
     except asyncio.CancelledError:
         pass
     await vd.stop()
     await oscq.stop()
     await overlay.stop()
     logger.info("Shutdown complete")

 if __name__ == "__main__":
     try:
         asyncio.run(main())
     except KeyboardInterrupt:
         pass
