# PRD Gap Register

This register tracks remaining items between the PRD and the current baseline implementation.

## High Priority

- Complete all API endpoints listed in PRD Section 12 with standardized pagination envelopes.
- Implement strict rate-limiting classes per endpoint category.
- Implement full immutable DB-level enforcement for audit table update/delete prohibition.
- Add examiner scoped access controls and temporary access expiry workflow.

## Medium Priority

- Implement full setup wizard and historical import wizard UX.
- Add full report generation pipeline (PDF/ZIP artifacts).
- Add comprehensive activity feed and trend analytics charts.
- Implement richer framework visual builder and mapping editor interactions.

## Low Priority

- Add SSE auto-reconnect fallback and offline queue replay semantics.
- Expand AI provider routing and data classification policy enforcement.
- Add archival/cold-storage lifecycle automation and retrieval API for long-term evidence.
