# security

Security, privacy, and PDPA compliance design for CareBridge. Written for
a 2.5-day design sprint — scoped enough to demo and defend, not a
production security audit.

## What's in here

**`SECURITY.md`** — the main design doc. Covers data classification,
role-based access control (grounded in the actual `ROLE_FIELD_ACCESS` /
`get_role_view()` code in `backend/backend_logic.py`), escalation
deduplication as data minimisation, CHA identity/trust requirements, the
non-clinical boundary, and encryption/audit-logging design intent —
plus an explicit list of what's *not* implemented in this sprint's code
(§8), so nobody over-claims in front of the evaluators.

**`CareBridge_Safety_Access_Design_EN.svg`** — a 4-page visual companion,
covering:
1. PDPA compliance checklist + data classification
2. Access control matrix (Family / CHA / Hospital — matches the three
   roles implemented in code; no separate admin role, kept consistent
   with `backend/backend_logic.py`)
3. Secure data flow (device → gateway → validation → rules engine →
   encrypted store → notification/escalation)
4. Q&A defence — pre-written answers to the questions evaluators are
   most likely to ask (false alerts, CHA trustworthiness, medical error,
   LLM mistakes)

**`security_01_pdpa.png`, `security_02_access.png`,
`security_03_dataflow.png`** — the same 4 pages
split into individual images (the source SVG has all 4 side by side on
one large canvas, which is hard to read at a glance) — use these for
pitch slides or when presenting one page at a time.

## How this connects to the code

`SECURITY.md` and the diagrams both describe things two ways:

- **Implemented and runnable** — role-based field filtering, escalation
  dedup, the non-clinical CHA boundary. You can point at
  `backend/backend_logic.py` and show it running.
- **Design intent, not built this sprint** — encryption, MFA, audit
  logging, CHA background-check process. These are documented as the
  target architecture; be upfront in Q&A that they're design decisions,
  not implemented code, if asked.

Keeping these two categories straight is the main thing to get right when
presenting — see `SECURITY.md` §8 for the full scope statement.
