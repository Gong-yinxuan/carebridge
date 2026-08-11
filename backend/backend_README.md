# backend/

Core logic for CareBridge: turns a raw smartwatch signal into a
classified anomaly, matches it to a Community Health Assistant (CHA), and
generates a structured escalation report for the hospital when needed.

## What's in here

**`backend_logic.py`** — the whole pipeline in one file:

| Function | What it does |
|---|---|
| `detect_anomaly()` | Classifies a signal (SOS, geofence exit, abnormal vitals, device tamper) into ignore/low/medium/high. SOS and tamper bypass tiering — they're treated as immediate emergencies. Trend detection escalates a low-risk signal if the elder has had multiple recent anomalies, to avoid missing a pattern that looks fine one signal at a time. |
| `match_cha()` | Assigns the task to the elder's primary CHA if available; falls back to a scored match (proximity, current workload, response history) if not. Deduplicates repeat signals for the same case within a 10-minute window. |
| `escalate()` | Builds a structured report when a CHA or family member triggers an upgrade. Deduplicates CHA- and family-triggered escalations for the same incident so the hospital isn't sent duplicate reports. |
| `get_role_view()` | Filters a report down to only the fields a given role (`cha` / `family` / `hospital`) is allowed to see — least-privilege access, documented in `security/SECURITY.md`. |
| `family_chat_assistant()` | Answers a family member's plain-language question about the elder's week, grounded in visit history. |

## AI integration

`escalate()` and `family_chat_assistant()` are both wired to call a real
LLM (`call_llm_api()`, using the Anthropic API) for natural-language
summaries. This is **plug-and-play, not required to run the demo**:

- No `ANTHROPIC_API_KEY` set → falls back to a fixed template automatically,
  no errors, no crash.
- Set the key and `pip install anthropic` → the same code path calls the
  real model instead.
- Every AI-generated report includes a `summary_source` field
  (`"ai"` or `"template_fallback"`) so it's always clear which path ran.

## Run it

```bash
python3 backend/backend_logic.py
```

Runs a full simulated scenario end-to-end (SOS press, geofence exit, a
trending vital-sign anomaly, an escalation, and a family chat question)
and prints each stage's output, including the raw JSON structures that
`frontend/` and `iot-integration/` are built to match.
