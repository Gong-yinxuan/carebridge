"""
CareBridge — Core Logic Demo v3 (Smartwatch Edition)
Pivot from pillbox-sensor signals to a smartwatch worn by the elder:
GPS geofence exit (wandering risk), SOS button press, abnormal vitals,
and device-tamper detection. Built for the dementia-care persona (Mdm Lim),
where the core risk is wandering / getting lost, missed self-care, and
medical emergencies — not just "did they open a pillbox".

Kept from v2: trend detection, case dedup, primary-CHA + dynamic-fallback
matching, escalation dedup across CHA/family triggers, role-based permission
view. New in v3: signal types matched to a wearable device, an "interaction
log" field so CHA visits capture companionship/activity (not just anomaly
checks), and SOS/tamper events that bypass tiered classification entirely
since they are unambiguous emergencies.

Simulated data + console output — proof of concept, not a production system.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta


# ---------- Data models ----------

@dataclass
class CHA:
    name: str
    block: str
    is_available: bool = True
    current_load: int = 0
    avg_response_min: float = 5.0


@dataclass
class Elder:
    name: str
    block: str  # internal — used for CHA proximity matching only, not shown to the user
    primary_cha: str
    emergency_contact: str
    address: str = ""  # human-readable, e.g. "Toa Payoh, 3-room flat" — shown in reports/UI
    age: int | None = None
    condition: str = "early/mid-stage dementia"
    safe_zone_radius_m: int = 300  # how far from home counts as "still safe"


@dataclass
class WatchEvent:
    """
    A signal coming from the elder's smartwatch. `signal_type` determines
    which fields in `payload` are relevant:
      - "sos_pressed"      : payload = {} (button press is unambiguous on its own)
      - "geofence_exit"     : payload = {"minutes_outside": int, "distance_m": int}
      - "vital_abnormal"    : payload = {"vital": "heart_rate"/"blood_pressure", "value": ..., "normal_range": ...}
      - "device_tampered"   : payload = {} (strap removed/broken)
      - "no_movement"       : payload = {"minutes_stationary": int}
    """
    elder_name: str
    signal_type: str
    payload: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


# ---------- Global state (in-memory for the demo; a real system would use a DB) ----------

event_history: dict[str, list[dict]] = {}
active_cases: dict[str, dict] = {}
active_escalations: dict[str, dict] = {}


# ---------- 1. Anomaly detection (signal-specific rules + trend check) ----------

def detect_anomaly(event: WatchEvent) -> dict:
    """
    SOS and tamper events are unambiguous emergencies — they bypass tiered
    classification and go straight to "high" priority with no trend logic
    needed. Geofence exits and vital-sign anomalies are still tiered, since
    those genuinely benefit from a graded response (a 3-minute step outside
    the safe zone is not the same as being missing for 40 minutes).
    """
    level, priority, detail = "low", 1, {}

    if event.signal_type == "sos_pressed":
        level, priority = "high", 3
        detail = {"reason": "SOS button pressed — treat as emergency regardless of context"}

    elif event.signal_type == "device_tampered":
        level, priority = "high", 3
        detail = {"reason": "Watch strap removed or broken — safety device offline, "
                             "wandering/emergency signals no longer being received"}

    elif event.signal_type == "geofence_exit":
        minutes = event.payload.get("minutes_outside", 0)
        distance = event.payload.get("distance_m", 0)
        if minutes < 5:
            level, priority = "ignore", 0
        elif minutes < 15:
            level, priority = "low", 1
        elif minutes < 30:
            level, priority = "medium", 2
        else:
            level, priority = "high", 3
        detail = {"minutes_outside": minutes, "distance_m": distance}

    elif event.signal_type == "vital_abnormal":
        vital = event.payload.get("vital")
        value = event.payload.get("value")
        deviation = event.payload.get("deviation_pct", 0)  # % outside normal range
        if deviation < 15:
            level, priority = "low", 1
        elif deviation < 30:
            level, priority = "medium", 2
        else:
            level, priority = "high", 3
        detail = {"vital": vital, "value": value, "deviation_pct": deviation}

    elif event.signal_type == "no_movement":
        minutes = event.payload.get("minutes_stationary", 0)
        if minutes < 30:
            level, priority = "ignore", 0
        elif minutes < 60:
            level, priority = "low", 1
        elif minutes < 120:
            level, priority = "medium", 2
        else:
            level, priority = "high", 3
        detail = {"minutes_stationary": minutes}

    else:
        detail = {"reason": f"unrecognised signal_type: {event.signal_type}"}

    result = {
        "signal_type": event.signal_type,
        "level": level,
        "priority": priority,
        "detail": detail,
        "escalated_by_trend": False,
        "recent_flagged_count": 0,
        "bypassed_tiering": event.signal_type in ("sos_pressed", "device_tampered"),
    }

    # --- Trend detection (skipped for SOS/tamper — already at max priority) ---
    if not result["bypassed_tiering"]:
        history = event_history.setdefault(event.elder_name, [])
        history.append({"level": level, "priority": priority, "timestamp": event.timestamp})
        recent_window = event.timestamp - timedelta(days=3)
        recent_events = [h for h in history if h["timestamp"] >= recent_window]
        recent_flagged = [h for h in recent_events if h["priority"] >= 1]
        result["recent_flagged_count"] = len(recent_flagged)

        if level in ("low", "medium") and len(recent_flagged) >= 2:
            original_priority = priority
            priority = min(priority + 1, 3)
            level = {1: "low", 2: "medium", 3: "high"}[priority]
            result["level"] = level
            result["priority"] = priority
            result["escalated_by_trend"] = priority != original_priority

    return result


# ---------- 2. CHA matching (primary-first + dynamic fallback + dedup) ----------

def score_cha(cha: CHA, elder: Elder) -> float:
    distance_score = 1.0 if cha.block == elder.block else 0.3
    load_score = max(0, 1 - cha.current_load / 10)
    speed_score = max(0, 1 - cha.avg_response_min / 20)
    return round(0.4 * distance_score + 0.3 * load_score + 0.3 * speed_score, 3)


def match_cha(elder: Elder, chas: list[CHA], anomaly: dict, now: datetime) -> dict:
    existing = active_cases.get(elder.name)
    if existing and (now - existing["created_at"]) < timedelta(minutes=10):
        existing["event_count"] += 1
        existing["max_priority"] = max(existing["max_priority"], anomaly["priority"])
        return {
            "assigned_to": existing["assigned_to"],
            "method": "merged_into_existing_case",
            "reason": f"Active case already open within the last 10 min "
                      f"(signal #{existing['event_count']}) — merged, no new dispatch",
        }

    primary = next((c for c in chas if c.name == elder.primary_cha), None)
    if primary and primary.is_available and primary.current_load < 8:
        result = {
            "assigned_to": primary.name,
            "method": "primary_fixed",
            "reason": f"{primary.name} is {elder.name}'s primary CHA and is currently available",
        }
    else:
        candidates = [c for c in chas if c.is_available and c.name != elder.primary_cha]
        if not candidates:
            return {"assigned_to": None, "method": "none", "reason": "No available CHA — needs manual intervention"}
        scored = sorted(((c, score_cha(c, elder)) for c in candidates), key=lambda x: x[1], reverse=True)
        best_cha, best_score = scored[0]
        result = {
            "assigned_to": best_cha.name,
            "method": "dynamic_fallback",
            "reason": f"Primary CHA unavailable — dynamic matching selected {best_cha.name} "
                      f"(composite score {best_score})",
        }

    active_cases[elder.name] = {
        "assigned_to": result["assigned_to"],
        "created_at": now,
        "event_count": 1,
        "max_priority": anomaly["priority"],
    }
    return result


# ---------- 3. Escalation (with dedup across triggers + interaction log) ----------

def escalate(elder: Elder, anomaly: dict, triggered_by: str, cha_description: str = "",
             interaction_note: str = "", now: datetime | None = None) -> dict:
    """
    `interaction_note` is new in v3: separate from the emergency description,
    it captures what companionship/activity the CHA did during the visit
    (chat, short walk, simple task) — this is how the "community engagement,
    not just passive monitoring" requirement shows up in the data model.
    """
    now = now or datetime.now()

    existing = active_escalations.get(elder.name)
    if existing and (now - existing["created_at"]) < timedelta(minutes=15):
        existing["triggered_by"].add(triggered_by)
        if cha_description:
            existing["cha_description"] = cha_description
        return {
            "merged": True,
            "elder_name": elder.name,
            "reason": f"An escalation for {elder.name} is already open "
                      f"(originally triggered by {sorted(existing['triggered_by'] - {triggered_by})}, "
                      f"now also confirmed by {triggered_by}) — merged, not sent twice",
        }

    ts = now.strftime("%Y-%m-%d %H:%M")
    report = {
        "elder_name": elder.name,
        "address": elder.address or elder.block,
        "age": elder.age,
        "condition": elder.condition,
        "signal_type": anomaly["signal_type"],
        "anomaly_level": anomaly["level"],
        "detail": anomaly["detail"],
        "recent_flagged_count": anomaly.get("recent_flagged_count", 0),
        "cha_description": cha_description or "(no on-site description provided)",
        "interaction_note": interaction_note or "(no interaction logged)",
        "timestamp": ts,
        "triggered_by": [triggered_by],
    }

    # ---- AI integration point ----
    # summary_text = call_llm_api(f"Generate a concise hospital triage summary: {report}")
    summary_text = (
        f"[CareBridge Triage Summary] {ts}\n"
        f"Elder: {elder.name}, age {elder.age} ({elder.address or elder.block}) — {elder.condition}\n"
        f"Signal: {anomaly['signal_type']} — level {anomaly['level']}\n"
        f"Detail: {anomaly['detail']}\n"
        f"CHA on-site description: {cha_description or '(none provided)'}\n"
        f"Recommendation: hospital telehealth / home-visit triage team to assess promptly"
    )

    report["summary_text"] = summary_text
    report["merged"] = False

    active_escalations[elder.name] = {
        "created_at": now,
        "triggered_by": {triggered_by},
        "cha_description": cha_description,
        "report": report,
    }
    return report


# ---------- Permission-tiered view ----------

ROLE_FIELD_ACCESS = {
    "cha": {
        "elder_name", "address", "signal_type", "anomaly_level", "detail",
        "cha_description", "interaction_note",
    },
    "family": {
        "elder_name", "signal_type", "anomaly_level", "recent_flagged_count",
        "cha_description", "interaction_note", "summary_text", "timestamp",
    },
    "hospital": "*",
}


def get_role_view(report: dict, role: str) -> dict:
    allowed = ROLE_FIELD_ACCESS.get(role)
    if allowed is None:
        raise ValueError(f"Unknown role: {role}")
    if allowed == "*":
        return dict(report)
    return {k: v for k, v in report.items() if k in allowed}


# ---------- Notification ----------

def notify(elder: Elder, anomaly: dict, match_result: dict):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] Notification sent:")
    print(f"  -> CHA \"{match_result['assigned_to']}\": please check on {elder.name} "
          f"({anomaly['signal_type']}, level={anomaly['level']})")
    if anomaly["level"] == "high" or anomaly.get("escalated_by_trend"):
        print(f"  -> Emergency contact \"{elder.emergency_contact}\": anomaly level {anomaly['level']}, please be aware")
    print()


# ---------- Demo main flow ----------

def run_demo():
    print("=" * 65)
    print("CareBridge Core Logic Demo v3 — Smartwatch signals (dementia care)")
    print("=" * 65)
    print()

    chas = [
        CHA(name="Chen (CHA)", block="123A", current_load=2, avg_response_min=4.0),
        CHA(name="Lee (CHA)", block="123A", current_load=7, avg_response_min=6.0, is_available=False),
        CHA(name="Wong (CHA)", block="125B", current_load=1, avg_response_min=3.5),
    ]

    elder = Elder(
        name="Mdm Lim Ah Kim",
        block="123A",  # internal matching key only
        primary_cha="Lee (CHA)",
        emergency_contact="David Tan (son)",
        address="Toa Payoh, 3-room flat",
        age=78,
    )

    now = datetime.now()

    # --- Scenario A: SOS pressed — bypasses tiering entirely, immediate high priority ---
    print("[1] SOS button pressed:")
    sos_event = WatchEvent(elder_name="Mdm Lim", signal_type="sos_pressed", timestamp=now)
    anomaly = detect_anomaly(sos_event)
    print(f"    -> Level: {anomaly['level']} (bypassed tiering: {anomaly['bypassed_tiering']})")
    match_result = match_cha(elder, chas, anomaly, now)
    print(f"    -> Dispatch: {match_result['method']} -> {match_result['assigned_to']}")
    notify(elder, anomaly, match_result)

    # --- Scenario B: geofence exit, graded by how long outside the safe zone ---
    print("[2] Geofence exit — Mdm Lim has been outside the safe zone for 35 minutes:")
    geo_event = WatchEvent(
        elder_name="Mdm Lim", signal_type="geofence_exit",
        payload={"minutes_outside": 35, "distance_m": 420},
        timestamp=now + timedelta(minutes=10),
    )
    anomaly2 = detect_anomaly(geo_event)
    print(f"    -> Level: {anomaly2['level']}, detail: {anomaly2['detail']}\n")

    # --- Scenario C: vital sign anomaly, mild deviation, gets escalated by trend ---
    print("[3] Heart rate reading mildly abnormal (simulating a 3rd occurrence this week):")
    event_history["Mdm Lim"] = [
        {"level": "low", "priority": 1, "timestamp": now - timedelta(days=2)},
        {"level": "low", "priority": 1, "timestamp": now - timedelta(hours=20)},
    ]
    vital_event = WatchEvent(
        elder_name="Mdm Lim", signal_type="vital_abnormal",
        payload={"vital": "heart_rate", "value": 105, "deviation_pct": 12},
        timestamp=now + timedelta(minutes=20),
    )
    anomaly3 = detect_anomaly(vital_event)
    print(f"    -> Base tier would be low, but {anomaly3['recent_flagged_count']} recent anomalies on file")
    print(f"    -> Final level: {anomaly3['level']} (escalated by trend: {anomaly3['escalated_by_trend']})\n")

    # --- Scenario D: CHA visit includes both an anomaly check AND a companionship activity ---
    print("[4] CHA visits in person — logs both the check and a companionship activity:")
    report = escalate(
        elder, anomaly3, triggered_by="cha",
        cha_description="Checked on Mdm Lim after the heart rate alert — she seems fine, slightly tired.",
        interaction_note="Had a 15-minute chat and short walk around the void deck together.",
        now=now + timedelta(minutes=25),
    )
    print(report["summary_text"])
    print()

    print("[DATA FORMAT] escalation report (JSON):")
    print(json.dumps(report, default=str, indent=2))
    print()

    print("[5] Role-based views of the same report:")
    print("    CHA view:", json.dumps(get_role_view(report, "cha"), default=str))
    print("    Family view:", json.dumps(get_role_view(report, "family"), default=str))
    print()

    print("=" * 65)
    print("Demo complete")
    print("=" * 65)


if __name__ == "__main__":
    run_demo()