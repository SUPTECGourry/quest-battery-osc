import asyncio
 import json
 import logging
 import socket
 from typing import Optional, Callable, Any

 from aiohttp import web
 from zeroconf import ServiceInfo, Zeroconf

 logging.basicConfig(level=logging.INFO)
 logger = logging.getLogger("oscquery_server")

 OSCQUERY_TYPE = "_oscjson._tcp.local."

 def _make_node(full_path: str, access: int, type_: Optional[str] = None, value: Optional[Any] = None, contents: Optional[dict] = None) -> dict:
     node = {
         "FULL_PATH": full_path,
         "ACCESS": access,
     }
     if type_:
         node["TYPE"] = type_
     if value is not None:
         node["VALUE"] = [value] if not isinstance(value, list) else value
     if contents:
         node["CONTENTS"] = contents
     return node

 class OSCQueryServer:
     def __init__(self, http_port: int, service_name: str, osc_port: int, state_getter: Callable[[], dict]):
         self.http_port = http_port
         self.service_name = service_name
         self.osc_port = osc_port
         self.state_getter = state_getter  # returns {"left": float|None, "right": float|None, "low": bool}
         self.app = web.Application()
         self.app.router.add_get("/{tail:.*}", self._handle_get)
         self.runner: Optional[web.AppRunner] = None
         self.site: Optional[web.TCPSite] = None
         self.zeroconf: Optional[Zeroconf] = None
         self.info: Optional[ServiceInfo] = None

     async def _build_tree(self) -> dict:
         state = await self.state_getter()
         left = state.get("left")
         right = state.get("right")
         low = state.get("low", False)

         # Build nested CONTENTS
         params_contents = {
             "BatteryLeft": _make_node(
                 "/avatar/parameters/BatteryLeft", 2, "f", float(left) if left is not None else None
             ),
             "BatteryRight": _make_node(
                 "/avatar/parameters/BatteryRight", 2, "f", float(right) if right is not None else None
             ),
             "BatteryLowWarning": _make_node(
                 "/avatar/parameters/BatteryLowWarning", 2, "T", bool(low)
             ),
         }

         parameters_node = _make_node(
             "/avatar/parameters", 0, contents=params_contents
         )

         avatar_node = _make_node(
             "/avatar", 0, contents={"parameters": parameters_node}
         )

         root = _make_node(
             "/", 0,
             contents={"avatar": avatar_node},
             # Add DESCRIPTION at root level
         )
         root["DESCRIPTION"] = "Quest Pro Battery Monitor"
         return root

     async def _get_node_for_path(self, path: str) -> Optional[dict]:
         if not path or path == "/":
             return await self._build_tree()

         # Simple path handling for known paths. For prototype, support exact known leaves and parents.
         tree = await self._build_tree()
         # Strip leading /
         parts = [p for p in path.strip("/").split("/") if p]
         current = tree
         for part in parts:
             if "CONTENTS" not in current or part not in current["CONTENTS"]:
                 return None
             current = current["CONTENTS"][part]
         return current

     async def _handle_get(self, request: web.Request) -> web.Response:
         path = request.path
         node = await self._get_node_for_path(path)
         if node is None:
             logger.debug(f"OSCQuery 404 for {path}")
             return web.json_response({"error": "not found"}, status=404)
         # Ensure DESCRIPTION only at root, but _build_tree puts it
         return web.json_response(node)

     async def start(self):
         self.runner = web.AppRunner(self.app)
         await self.runner.setup()
         self.site = web.TCPSite(self.runner, "127.0.0.1", self.http_port)
         await self.site.start()
         logger.info(f"OSCQuery HTTP server started on http://127.0.0.1:{self.http_port}")

         # mDNS advertisement
         self.zeroconf = Zeroconf()
         properties = {
             b"OSC_PORT": str(self.osc_port).encode("utf-8"),
             b"OSC_TRANSPORT": b"UDP",
         }
         self.info = ServiceInfo(
             OSCQUERY_TYPE,
             f"{self.service_name}.{OSCQUERY_TYPE}",
             addresses=[socket.inet_aton("127.0.0.1")],
             port=self.http_port,
             properties=properties,
             server=f"{self.service_name}.local.",
         )
         self.zeroconf.register_service(self.info)
         logger.info(f"mDNS advertised as {self.service_name}._oscjson._tcp.local. (HTTP {self.http_port}, OSC {self.osc_port})")

     async def stop(self):
         if self.info and self.zeroconf:
             self.zeroconf.unregister_service(self.info)
             self.zeroconf.close()
             logger.info("mDNS unregistered")
         if self.site:
             await self.site.stop()
         if self.runner:
             await self.runner.cleanup()
             logger.info("OSCQuery HTTP server stopped")
