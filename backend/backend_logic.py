"""
CareBridge — Core Logic Demo v2
Adds three features on top of v1:
1. Trend detection: escalates a low-risk single signal if the elder has had
   frequent recent anomalies (guards against false negatives / missed alerts)
2. Deduplication: merges a new IoT signal into an already-active case for the
   same elder instead of dispatching a duplicate task
3. Escalation summary: generates a structured report when a CHA or family
   member triggers an upgrade, ready to be handed off to the hospital

Uses simulated data and console output for demo purposes — this is a proof
of concept, not a production system.
"""

import random
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
    block: str
    primary_cha: str
    emergency_contact: str


@dataclass
class IoTEvent:
    elder_name: str
    signal_type: str
    minutes_overdue: int
    timestamp: datetime = field(default_factory=datetime.now)


# ---------- Global state (in-memory for the demo; a real system would use a DB) ----------

# Per-elder history of past signals, used for trend detection
event_history: dict[str, list[dict]] = {}

# Cases currently being handled, used for deduplication. key = elder name
active_cases: dict[str, dict] = {}


# ---------- 1. Anomaly detection (rule-based tiers + trend check) ----------

def detect_anomaly(event: IoTEvent) -> dict:
    """
    First pass: classify severity based on signal type and how overdue it is.
    Second pass (trend detection): even if this single event looks low-risk,
    escalate it if the elder has already had multiple recent anomalies —
    this guards against the case where each individual signal looks fine,
    but the pattern over time actually indicates a problem.
    """
    thresholds = {
        "pillbox_not_opened": {"low": 15, "medium": 30, "high": 60},
        "no_motion_detected": {"low": 20, "medium": 45, "high": 90},
    }
    t = thresholds.get(event.signal_type, {"low": 15, "medium": 30, "high": 60})
    minutes = event.minutes_overdue

    if minutes < t["low"]:
        level, priority = "ignore", 0
    elif minutes < t["medium"]:
        level, priority = "low", 1
    elif minutes < t["high"]:
        level, priority = "medium", 2
    else:
        level, priority = "high", 3

    # --- Trend detection ---
    history = event_history.setdefault(event.elder_name, [])
    history.append({"level": level, "priority": priority, "timestamp": event.timestamp})

    recent_window = event.timestamp - timedelta(days=3)
    recent_events = [h for h in history if h["timestamp"] >= recent_window]
    recent_flagged = [h for h in recent_events if h["priority"] >= 1]  # low or above counts as flagged

    escalated_by_trend = False
    if level == "ignore" and len(recent_flagged) >= 0:
        pass  # "ignore"-level events don't count toward the trend, to avoid noise

    if level in ("low", "medium") and len(recent_flagged) >= 2:
        # 2+ low/medium anomalies in the past 3 days -> bump this one up a tier
        original_priority = priority
        priority = min(priority + 1, 3)
        level = {1: "low", 2: "medium", 3: "high"}[priority]
        escalated_by_trend = priority != original_priority

    return {
        "level": level,
        "priority": priority,
        "minutes_overdue": minutes,
        "escalated_by_trend": escalated_by_trend,
        "recent_flagged_count": len(recent_flagged),
    }


# ---------- 2. CHA matching (primary CHA first, dynamic fallback, dedup) ----------

def score_cha(cha: CHA, elder: Elder) -> float:
    distance_score = 1.0 if cha.block == elder.block else 0.3
    load_score = max(0, 1 - cha.current_load / 10)
    speed_score = max(0, 1 - cha.avg_response_min / 20)
    return round(0.4 * distance_score + 0.3 * load_score + 0.3 * speed_score, 3)


def match_cha(elder: Elder, chas: list[CHA], anomaly: dict, now: datetime) -> dict:
    """
    First check whether there's already an active case for this elder (dedup).
    If not, run the normal matching flow: try the primary CHA first, and only
    fall back to dynamic scoring if the primary is unavailable.
    """
    # --- Dedup check ---
    existing = active_cases.get(elder.name)
    if existing and (now - existing["created_at"]) < timedelta(minutes=10):
        existing["event_count"] += 1
        existing["max_priority"] = max(existing["max_priority"], anomaly["priority"])
        return {
            "assigned_to": existing["assigned_to"],
            "method": "merged_into_existing_case",
            "reason": f"An active case already exists within the last 10 min "
                      f"(signal #{existing['event_count']} for this case) — merged, no new dispatch",
        }

    # --- Normal matching flow ---
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
            "all_scores": [(c.name, s) for c, s in scored],
        }

    # Record this as an active case for future dedup checks
    active_cases[elder.name] = {
        "assigned_to": result["assigned_to"],
        "created_at": now,
        "event_count": 1,
        "max_priority": anomaly["priority"],
    }
    return result


# ---------- 3. Escalation summary (CHA/family trigger -> structured report) ----------

def escalate(elder: Elder, anomaly: dict, cha_description: str = "") -> dict:
    """
    Called when a CHA or family member presses the escalate button.
    Builds a structured summary using a fixed template (sufficient for the demo).
    If an LLM is wired in, cha_description + recent history can be passed to the
    model to produce a more natural triage summary — the integration point is
    marked with a comment below.
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    report = {
        "elder_name": elder.name,
        "block": elder.block,
        "anomaly_level": anomaly["level"],
        "minutes_overdue": anomaly["minutes_overdue"],
        "recent_flagged_count": anomaly.get("recent_flagged_count", 0),
        "cha_description": cha_description or "(no on-site description provided)",
        "timestamp": ts,
    }

    # ---- AI integration point ----
    # If an LLM API is wired in, the fields in `report` plus `cha_description`
    # can be passed as context to generate a more natural triage summary, e.g.:
    #
    # summary_text = call_llm_api(
    #     f"Generate a concise hospital triage summary from this information: {report}"
    # )
    #
    # For the demo, a fixed template is used instead:
    summary_text = (
        f"[CareBridge Triage Summary] {ts}\n"
        f"Elder: {elder.name} (Block {elder.block})\n"
        f"Anomaly level: {anomaly['level']} (overdue by {anomaly['minutes_overdue']} min; "
        f"{anomaly.get('recent_flagged_count', 0)} related anomalies in the past 3 days)\n"
        f"CHA on-site description: {cha_description or '(none provided)'}\n"
        f"Recommendation: hospital telehealth / home-visit triage team to assess promptly"
    )

    report["summary_text"] = summary_text
    return report


# ---------- Notification ----------

def notify(elder: Elder, anomaly: dict, match_result: dict):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] Notification sent:")
    print(f"  -> CHA \"{match_result['assigned_to']}\": please check on {elder.name}")
    if anomaly["level"] == "high" or anomaly.get("escalated_by_trend"):
        print(f"  -> Emergency contact \"{elder.emergency_contact}\": anomaly level {anomaly['level']}, please be aware")
        if anomaly.get("escalated_by_trend"):
            print(f"     (Note: escalated due to a recent pattern, not a single one-off signal)")
    print()


# ---------- Demo main flow ----------

def run_demo():
    print("=" * 60)
    print("CareBridge Core Logic Demo v2 — trend detection / dedup / escalation summary")
    print("=" * 60)
    print()

    chas = [
        CHA(name="Chen (CHA)", block="123A", current_load=2, avg_response_min=4.0),
        CHA(name="Lee (CHA)", block="123A", current_load=7, avg_response_min=6.0, is_available=False),
        CHA(name="Wong (CHA)", block="125B", current_load=1, avg_response_min=3.5),
    ]

    elder = Elder(
        name="Mdm Lim",
        block="123A",
        primary_cha="Lee (CHA)",
        emergency_contact="David (son)",
    )

    now = datetime.now()

    # --- Scenario A: pre-populate history with 2 low-risk anomalies over the past 3 days ---
    event_history[elder.name] = [
        {"level": "low", "priority": 1, "timestamp": now - timedelta(days=2)},
        {"level": "low", "priority": 1, "timestamp": now - timedelta(hours=20)},
    ]

    # --- Scenario B: new signal that looks low-risk on its own, but gets escalated by trend ---
    event = IoTEvent(elder_name="Mdm Lim", signal_type="pillbox_not_opened", minutes_overdue=18, timestamp=now)

    print(f"[1] IoT signal: {event.signal_type}, overdue by {event.minutes_overdue} min")
    anomaly = detect_anomaly(event)
    print(f"    -> Base classification would be low-tier, but {anomaly['recent_flagged_count']} "
          f"related anomalies occurred in the past 3 days")
    print(f"    -> Final level: {anomaly['level']} (priority={anomaly['priority']}, "
          f"escalated by trend: {anomaly['escalated_by_trend']})\n")

    print("[2] CHA matching:")
    match_result = match_cha(elder, chas, anomaly, now)
    print(f"    -> Dispatch method: {match_result['method']}")
    print(f"    -> {match_result['reason']}\n")

    print("[3] Notification:")
    notify(elder, anomaly, match_result)

    # --- Scenario C: another signal 5 minutes later — should be deduplicated ---
    event2 = IoTEvent(elder_name="Mdm Lim", signal_type="pillbox_not_opened", minutes_overdue=25,
                       timestamp=now + timedelta(minutes=5))
    print(f"[4] Another signal arrives 5 minutes later (simulating a duplicate trigger):")
    anomaly2 = detect_anomaly(event2)
    match_result2 = match_cha(elder, chas, anomaly2, event2.timestamp)
    print(f"    -> Dispatch method: {match_result2['method']}")
    print(f"    -> {match_result2['reason']}\n")

    # --- Scenario D: CHA arrives on-site and presses the escalate button ---
    print("[5] CHA arrives on-site, notices something is off, and presses escalate:")
    report = escalate(elder, anomaly, cha_description="Elder is conscious but slower to respond than usual; "
                                                        "blood pressure not yet measured — recommend clinical review")
    print(report["summary_text"])
    print()

    print("=" * 60)
    print("Demo complete")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
