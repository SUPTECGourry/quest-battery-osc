import logging
from pythonosc.udp_client import SimpleUDPClient
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("osc_sender")

class OSCSender:
    def __init__(self, ip: str, port: int):
        self.client = SimpleUDPClient(ip, port)
        self.ip = ip
        self.port = port

    def send_battery(self, left: Optional[float], right: Optional[float], low_warning: bool):
        try:
            if left is not None:
                self.client.send_message("/avatar/parameters/BatteryLeft", float(left))
            if right is not None:
                self.client.send_message("/avatar/parameters/BatteryRight", float(right))
            self.client.send_message("/avatar/parameters/BatteryLowWarning", bool(low_warning))
            logger.debug(f"Sent OSC: L={left} R={right} Low={low_warning}")
        except Exception as e:
            logger.error(f"OSC send failed: {e}")
