# Quest Pro Battery Monitor - Prototype

> **Auto-trigger test commit** — pushed to verify `branches: [main]` workflow activation

Lightweight PC bridge: Virtual Desktop → OSC/OSCQuery → VRChat avatar parameters.

## Setup

1. Install deps (in venv recommended):
   ```
   cd quest-battery-osc
   python -m venv .venv
   source .venv/bin/activate   # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. Ensure Virtual Desktop Streamer is running (starts the ws://localhost:19999 server).

3. (Optional) In VRChat, create avatar parameters:
   - BatteryLeft (float)
   - BatteryRight (float)
   - BatteryLowWarning (bool)

   Map them in your avatar descriptor / animator as needed (e.g. to blendshapes or material floats for battery HUD).

4. Run the bridge:
   ```
   python main.py
   ```

5. Start VRChat. It should auto-discover via mDNS/OSCQuery on port 9001.
   No manual OSC port setup needed.

## Config

Edit `config.yaml`:
- `vd_reconnect_backoff_s`: exponential backoff for VD reconnect
- `poll_interval_s`: how often to push current battery values via OSC (default 3s)
- `low_battery_threshold`: fraction, default 0.15
- `overlay_enabled`: set true to enable (stub only)

## OSC Parameters sent to VRChat

| Path                              | Type  | Notes                     |
|-----------------------------------|-------|---------------------------|
| /avatar/parameters/BatteryLeft    | float | 0.0–1.0 or null if unavailable |
| /avatar/parameters/BatteryRight   | float | same                      |
| /avatar/parameters/BatteryLowWarning | bool | true if either < threshold |

## OSCQuery

- HTTP: http://127.0.0.1:9001
- mDNS: QuestBatteryMonitor._oscjson._tcp.local.
- VRChat will query the parameter tree and map automatically.

## Troubleshooting

- No battery data: Confirm Virtual Desktop Streamer running and Quest Pro connected via VD (not native SteamVR).
- VRChat not discovering: Check firewall on port 9001 UDP/TCP? mDNS uses UDP 5353 usually.
- Check logs for "Connected to Virtual Desktop Streamer" and mDNS advertised.
- Controllers off: battery reported as None, OSC send skipped for that param, LowWarning uses last known or false.

## Next steps (prototype complete)

- Test with actual Quest Pro + VD + VRChat
- Implement real SteamVR overlay via OVR Toolkit WS if desired
- Add more robust tree walking / full OSCQuery spec compliance if VRChat complains
- Package as exe with PyInstaller if needed

Prototype is fully async, reconnects automatically, and follows the specified architecture.
