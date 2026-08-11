# iot-integration/

The "senses" layer — simulates the smartwatch signal stream that
`backend/` reacts to. No real hardware for this sprint, so this module
generates a plausible stream of signals instead of a single hand-fed data
point, to demo "the system continuously receiving and reacting to device
data."

## What's in here

**`iot_simulator.py`** — fires a sequence of randomised smartwatch signals
(SOS, geofence exit, abnormal vitals, device tamper, no-movement) across a
small simulated fleet of elders, and runs each one through the real
backend pipeline (`detect_anomaly → match_cha → notify`).

Signal types are weighted so a run produces a realistic mix — SOS and
tamper are rare, movement/vitals checks are frequent — and low-risk
signals are correctly filtered out (logged, not dispatched), same as a
real deployment would.

## In a real deployment

This module would instead receive telemetry from the smartwatch vendor's
cloud (via webhook or MQTT) and translate it into the same `WatchEvent`
format the simulator builds here — the backend pipeline itself wouldn't
need to change.

## Run it

Run from the **repo root**, not from inside this folder — it imports
`backend/backend_logic.py` as a sibling module:

```bash
python3 iot-integration/iot_simulator.py
```
