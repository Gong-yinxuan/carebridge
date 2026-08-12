# frontend/

A static, 5-page interactive prototype of the CareBridge app — built to
demo the product story, not as a production frontend.

## What's in here

**`carebridge_prototype.html`** — single file, no build step, no server.
Open it directly in a browser.

| Page | Who uses it | What it shows |
|---|---|---|
| **Family view** | David (family member) | Status overview, one-tap call, next scheduled visit + on-demand check-in request, weekly timeline (routine check-ins *and* social/companionship visits, each attributed to the CHA who did it), location/geofence status, AI chat summary |
| **Patient profile** | David (family member) | One-time setup of daily routine, medication schedule, and mobility/preference notes — the info CHAs and the AI assistant draw on, instead of the family repeating it every visit |
| **CHA check-in** | Community Health Assistant | Care-team panel (primary CHA vs. whoever is covering), visit checklist, on-site notes, interaction/activity log — each attributed to the specific CHA who logged it — plus hospital and police escalation |
| **CHA caseload** | Community Health Assistant | A CHA's full patient list (one CHA supports several patients), an AI-generated "patient prep" briefing for a covering CHA, and a request-backup action when a CHA is running behind |
| **Escalation summary** | David + CHA | Human-readable summary card with elder photo, location, and named CHA attribution; the full report is available via an expandable "View full report" section — deliberately not shown as raw JSON/code, to keep the page feeling like a real app throughout |

Every page carries a small **Built / Planned** legend: green items are
backed by real logic in `backend/backend_logic.py` (e.g. CHA fallback
matching, escalation dedup); amber items are shown for the pitch but not
yet wired to a backend.

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
- Named CHA attribution (e.g. "Rachel — covering for Chen") reflects the
  backend's primary-first, dynamic-fallback CHA matching — the family and
  hospital always know exactly who attended, even on a covered visit.
