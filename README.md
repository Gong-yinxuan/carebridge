# CareBridge

**A community-based micro-visit network for elderly residents living with dementia — backed by a wearable safety net and a hospital-linked escalation path.**

BU2001 Design Sprint · TR2 Design Challenge — *Healthcare Beyond Hospitals*

---

## The problem

Singapore's healthcare system is shifting from hospital-centric care to
prevention and community-based support. For families of elderly residents
with early/mid-stage dementia, the gap isn't acute medical care — it's the
hundred small things that happen between hospital visits: missed
medication, skipped meals, disorientation, wandering risk — and the risk
that comes from being *only* monitored, not engaged.

**David Tan, 45**, works full-time in the CBD and cannot check on his
mother, **Mdm Lim Ah Kim, 78** (Toa Payoh, 3-room flat, early/mid-stage
dementia), during the day. Hiring round-the-clock professional care isn't
affordable or realistic — but "just watching her" isn't the answer either.

## The solution

CareBridge combines:

- **A wearable smartwatch** (GPS + geofence, SOS button, vital-sign
  monitoring, tamper detection) — the safety net, not the core product.
- **Community Health Assistants (CHAs)** — trained, certified residents of
  the same estate who do short, non-clinical "micro-visits": confirming
  medication, checking in, and — just as importantly — spending time with
  the elder (a chat, a short walk, a game of chess).
- **A hospital-linked escalation path** — any real concern routes straight
  to the hospital's existing telehealth/triage team. CHAs observe and
  report; they never diagnose, dose, or alter treatment.

## Repo structure

```
carebridge/
├── backend/              Core logic: anomaly detection, CHA matching, escalation
├── iot-integration/       Simulated smartwatch signal stream (no real hardware for this sprint)
├── frontend/              3-page interactive prototype (family view, CHA check-in, escalation summary)
├── security/              PDPA compliance, access control design, security diagrams
└── README.md
```

## How it works

```
Smartwatch signal → Anomaly detection → CHA matching → Notification → (if needed) Escalation → Hospital
```

1. **`backend/backend_logic.py`** — the core logic. Detects anomalies from
   smartwatch signals (SOS, geofence exit, abnormal vitals, device tamper),
   with trend detection so recurring low-risk signals still get escalated.
   Matches tasks to a primary CHA first, falling back to dynamic matching
   (proximity + workload + response time) only when needed. Deduplicates
   both routine signals and escalations so the hospital never receives
   redundant reports. Applies role-based data filtering (`get_role_view`)
   so CHAs, family, and hospital staff each see only what they need.

   Run it directly to see the full pipeline in action:
   ```bash
   python3 backend/backend_logic.py
   ```

2. **`iot-integration/iot_simulator.py`** — simulates a stream of
   smartwatch signals across multiple elders, feeding each one through the
   backend pipeline. Run from the repo root:
   ```bash
   python3 iot-integration/iot_simulator.py
   ```

3. **`frontend/carebridge_prototype.html`** — a static, mock-data
   prototype of the three core screens. Open directly in a browser (no
   server needed):
   - **Family view** — status overview, one-tap call, weekly activity
     timeline (including social/companionship visits), AI chat summary
   - **CHA check-in** — visit checklist, on-site notes, interaction log,
     escalate button
   - **Escalation summary** — human-readable report; full data sent to
     the hospital is available via an expandable section (not shown as
     raw code)

4. **`security/`** — `SECURITY.md` documents the security and PDPA design,
   grounded in the actual access-control code in `backend/`. The
   `CareBridge_Safety_Access_Design_EN.svg` diagrams (data classification,
   access matrix, secure data flow, Q&A defence) were produced separately
   and are kept consistent with the code — the access matrix covers the
   three roles implemented in `backend_logic.py` (family, CHA, hospital).

## Scope of this sprint

This is a 2.5-day design sprint prototype — it demonstrates the *logic and
design decisions*, not a production system:

- Backend and IoT layers run as local scripts with simulated data — no
  real hardware, database, or network layer.
- Frontend uses static mock data matching the backend's output structure —
  not live-connected via an API.
- Security design (encryption, MFA, audit logging) is documented as
  intended architecture; not implemented in the prototype code. See
  `security/SECURITY.md` §8 for an explicit list of what's in vs. out of
  scope.

## Team

- **Frontend & backend logic** — Yinxuan
- **Storyboard, business case & security design** — [teammate]
  


