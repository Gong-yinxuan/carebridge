"""
CareBridge — IoT Integration Layer (Smartwatch Signal Simulator)

This is the "senses" layer: in a real deployment, this module would receive
raw telemetry from smartwatches (via MQTT/HTTP webhook from the device
vendor's cloud) and translate it into the WatchEvent format backend/
expects. Since there's no real hardware for this sprint, it instead
simulates a stream of signals across multiple elders over time, so the demo
can show "the system continuously receiving and reacting to device data"
rather than a single hand-fed data point.

Run this from the repo root so the import path resolves:
    python3 iot-integration/iot_simulator.py

Folder layout assumed:
    carebridge/
      backend/backend_logic.py   <- detect_anomaly / match_cha / escalate / notify live here
      iot-integration/iot_simulator.py   <- this file
"""

import os
import random
import sys
import time
from datetime import datetime, timedelta

# ---- Make backend/ importable from a sibling folder ----
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))
from backend_logic import (  # noqa: E402
    CHA, Elder, WatchEvent, detect_anomaly, match_cha, notify,
)


# ---------- Simulated fleet: elders + their watches ----------

ELDERS = [
    Elder(name="Mdm Lim", block="123A", primary_cha="Lee (CHA)", emergency_contact="David (son)"),
    Elder(name="Mr Tan", block="125B", primary_cha="Wong (CHA)", emergency_contact="Grace (daughter)"),
]

CHAS = [
    CHA(name="Chen (CHA)", block="123A", current_load=2, avg_response_min=4.0),
    CHA(name="Lee (CHA)", block="123A", current_load=7, avg_response_min=6.0, is_available=False),
    CHA(name="Wong (CHA)", block="125B", current_load=1, avg_response_min=3.5),
]

# Weighted signal types — SOS/tamper are rare, movement/vitals checks are frequent,
# roughly reflecting how often each would realistically fire in a real deployment
SIGNAL_WEIGHTS = {
    "no_movement": 0.35,
    "vital_abnormal": 0.25,
    "geofence_exit": 0.25,
    "device_tampered": 0.05,
    "sos_pressed": 0.10,
}


def generate_random_event(elder_name: str, timestamp: datetime) -> WatchEvent:
    """
    Builds one plausible simulated signal. Payload ranges are chosen to
    produce a mix of ignore/low/medium/high outcomes across a run, so a demo
    session shows the full range of the anomaly-detection logic, not just
    one branch.
    """
    signal_type = random.choices(
        list(SIGNAL_WEIGHTS.keys()), weights=list(SIGNAL_WEIGHTS.values())
    )[0]

    payload = {}
    if signal_type == "no_movement":
        payload = {"minutes_stationary": random.choice([20, 45, 70, 130])}
    elif signal_type == "vital_abnormal":
        payload = {
            "vital": random.choice(["heart_rate", "blood_pressure"]),
            "value": random.randint(90, 160),
            "deviation_pct": random.choice([8, 18, 35]),
        }
    elif signal_type == "geofence_exit":
        payload = {
            "minutes_outside": random.choice([3, 12, 22, 40]),
            "distance_m": random.randint(100, 600),
        }
    # sos_pressed / device_tampered carry no payload — the event itself is the signal

    return WatchEvent(elder_name=elder_name, signal_type=signal_type, payload=payload, timestamp=timestamp)


# ---------- Simulation loop ----------

def run_simulation(num_events: int = 8, seed: int | None = 42):
    """
    Fires `num_events` simulated signals spaced a few minutes apart across
    the simulated elder fleet, and runs each one through the full backend
    pipeline: detect_anomaly -> match_cha -> notify. Deliberately skips
    events classified as "ignore" going any further, same as a real system
    would — not every signal needs a human response.
    """
    if seed is not None:
        random.seed(seed)

    print("=" * 65)
    print("CareBridge IoT Integration — Simulated Smartwatch Signal Stream")
    print("=" * 65)
    print()

    now = datetime.now()
    for i in range(num_events):
        elder = random.choice(ELDERS)
        ts = now + timedelta(minutes=i * 4)
        event = generate_random_event(elder.name, ts)

        print(f"--- Signal {i + 1}/{num_events} @ {ts.strftime('%H:%M')} ---")
        print(f"[Device] {elder.name}'s watch -> signal_type={event.signal_type}, payload={event.payload}")

        anomaly = detect_anomaly(event)
        print(f"[Backend] level={anomaly['level']} priority={anomaly['priority']}"
              f"{' (bypassed tiering)' if anomaly.get('bypassed_tiering') else ''}")

        if anomaly["level"] == "ignore":
            print("[Backend] Below threshold — logged only, no dispatch.\n")
            continue

        match_result = match_cha(elder, CHAS, anomaly, ts)
        notify(elder, anomaly, match_result)

    print("=" * 65)
    print("Simulation complete —", num_events, "signals processed")
    print("=" * 65)


if __name__ == "__main__":
    run_simulation()
