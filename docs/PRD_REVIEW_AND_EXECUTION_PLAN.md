# SAP v3 PRD Review and Execution Plan

This plan is derived from the full `PRD.md` and is organized as parallel workstreams (agent lanes) to deliver a production-quality SAP v3 implementation.

## Scope Confirmation (From PRD)

Locked requirements implemented for this delivery baseline:

- Hosting: Railway
- Topology: one web service + one PostgreSQL database
- Backend: FastAPI + SQLAlchemy
- Frontend: React + TypeScript + Tailwind
- Auth: email/password + invite code + RBAC
- Audit: hash-chained immutable event log with verification
- Deterministic analysis: rule-based findings generation
- Fedlink reference implementation: starter framework + application + template

## Multi-Agent Workstreams

1. Frontend UI Agent
- Deliver role-aware UI shell, dashboard, reviews workspace, frameworks/applications, reference data, audit log, settings, users.
- Enforce accessibility baseline (focus states, skip link, severity labels).
- Implement React Query data flows and protected routes.

2. Backend Workflow Agent
- Deliver review lifecycle APIs and state transitions.
- Implement document upload, extraction, confirmation, deterministic analysis, findings disposition, approval/rejection.
- Provide health/readiness and operational endpoints.

3. Security and Banking Controls Agent
- Enforce password policy and role-based authorization.
- Implement refresh token rotation and concurrent-session limits.
- Ensure immutable audit chain + verification endpoint.
- Ensure file upload constraints, hashing, and basic parser safeguards.

4. Framework/Rules Agent
- Implement rule execution engine for compound, role-match, threshold/date, and cross-reference checks.
- Keep analysis deterministic and checksum-backed.
- Seed Fedlink starter framework and mappings.

5. DevOps and Railway Agent
- Build Dockerized single-service runtime serving both API and frontend.
- Create CI workflows for backend tests and frontend build.
- Provide Railway deployment config and health checks.

6. QA and Validation Agent
- Add backend tests for security + audit chain + health.
- Validate local startup, API liveness, and frontend build.
- Produce implementation gap register for remaining PRD phases.

## Delivery Phases

1. Foundation (completed in this implementation)
- Monorepo scaffold, API/DB/frontend base, Docker, CI, Railway config.

2. Compliance Workflow MVP (completed in this implementation)
- Core UAR workflow from review creation through approval with deterministic findings.

3. Hardening and Expansion (next)
- Full pagination/rate limiting/error envelopes across all routes.
- Expanded parser support, richer low-confidence remediation UX, complete report generation.
- Advanced security controls (CSP, stricter session inactivity, deeper token revocation policies).

4. Production Readiness (next)
- Move from `create_all` startup to strict Alembic migration execution.
- Add E2E tests and load/performance tests.
- Add Sentry and externalized storage provider integration.

## PRD Coverage Snapshot

Implemented now:
- Core RBAC/auth/invite flow
- Review workflow core lifecycle
- Document upload and extraction (CSV/Excel)
- Deterministic analysis and findings disposition
- Audit hash chain logging and verification
- Key UI screens for operations
- Railway-compatible deployment artifacts

Planned next:
- Full FFIEC/OCC evidence packaging workflows
- Complete API surface in PRD sections 12.16+ with richer exports
- Enhanced async/background task orchestration and retry
- Advanced access review features (delegation/escalation/SLA automation)

## Acceptance Criteria for This Baseline

- User can register/login using invite code.
- Admin can create frameworks and applications.
- Reviewer can create review, upload document, extract, confirm, analyze.
- Reviewer can disposition findings and approve review.
- Auditor/examiner can view and verify audit chain.
- App builds and runs as a single Railway web service connected to one Postgres DB.
