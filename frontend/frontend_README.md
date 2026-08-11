# frontend/

A static, 3-page interactive prototype of the CareBridge app — built to
demo the product story, not as a production frontend.

## What's in here

**`carebridge_prototype.html`** — single file, no build step, no server.
Open it directly in a browser.

| Page | Who uses it | What it shows |
|---|---|---|
| **Family view** | David (family member) | Status overview, one-tap call, weekly timeline (routine check-ins *and* social/companionship visits — not just anomaly checks), AI chat summary |
| **CHA check-in** | Community Health Assistant | Visit checklist, on-site notes, interaction/activity log, escalate button |
| **Escalation summary** | David + CHA | Human-readable summary card; the full report is available via an expandable "View full report" section — deliberately not shown as raw JSON/code, to keep the page feeling like a real app throughout |

## Data

All content is **mock data**, hand-written to match the exact field
structure `backend/backend_logic.py` actually produces (see the
`[DATA FORMAT]` sections when you run the backend script). It's not
live-connected via an API — that trade-off was made deliberately for a
2.5-day sprint (see root `README.md`, "Scope of this sprint").

## Design notes

- Palette and type match the storyboard/security diagrams (navy `#14213D`
  + teal `#0E7C66`) for a consistent look across all sprint deliverables.
- The "Social visit" timeline entry (blue dot) is intentional — it makes
  the "active engagement, not just passive monitoring" requirement visible
  in the UI, not just in the backend's `interaction_note` field.
