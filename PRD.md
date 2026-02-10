# Security Analyst Platform v2 (SAPv2)
## Product Requirements Document — Enhanced

**Version:** 3.0
**Author:** Josh Lopez / IT Director, First State Bank of the Florida Keys
**Date:** February 10, 2026
**Status:** Enhanced with Gap Analysis
**Based on:** PRD v2.0 (Feb 5, 2026) + Workflow Analysis + Backend Architecture Analysis + AI-Agnostic Design

---

## Implementation Decisions (Locked)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Deployment** | Railway (POC) | Fast deployment, easy scaling for proof of concept |
| **Backend Stack** | Python 3.11+ / FastAPI | Excellent for data processing (pandas), async support, JSON Logic native |
| **Frontend** | React 18+ / TypeScript / shadcn/ui / Tailwind CSS | Modern, maintainable, good component library, accessible by default |
| **Database** | PostgreSQL 15+ (hybrid schema) | Reliable, JSON support for flexible data, normalized for queryable fields |
| **AI Provider** | LLM-Agnostic (Azure OpenAI default) | Provider abstraction layer supporting OpenAI, Azure OpenAI, Anthropic Claude, Google Gemini, AWS Bedrock, Ollama (local), and any OpenAI-compatible endpoint. Per-function model routing with fallback chains. Data classification enforcement restricts providers based on compliance capabilities (BAA, SOC 2). Default for production: Azure OpenAI (enterprise compliance, BAA available). Default for development: mock provider (no external calls). |
| **Rule Engine** | JSON Logic (python: json-logic-qubit) | Deterministic, portable, serializable, no eval() |
| **Auth** | Email/password with invite codes (POC) | Simple for initial team of 2-5 users |
| **Audit Trail** | Regulatory-grade with hash chaining | Immutable logs, checksums, tamper detection, 7+ year retention |
| **MVP Focus** | User Access Review | Fedlink as reference implementation |
| **Critical Feature** | Cross-document correlation | Required for terminated employee detection |
| **PDF Extraction** | Camelot (primary) + pdfplumber (fallback) | Accuracy scoring for confidence-based validation |
| **Data Model** | Hybrid (normalized + JSONB) | Performance at scale, queryable fields indexed properly |
| **File Storage** | S3-compatible (Railway volumes or AWS S3) | Uploaded documents stored outside web root with UUID-based naming, server-side encryption at rest, TLS in transit. Lifecycle policies enforce retention and cleanup. |
| **Background Jobs** | FastAPI BackgroundTasks (POC) / Celery (production) | Start with FastAPI BackgroundTasks for POC simplicity (avoids separate worker process and Redis broker). Migrate to Celery when task reliability, scheduling, or retry complexity requires it. Reduces Railway service count from 4 to 3 for POC. |
| **Monitoring** | Structured logging + Sentry | All application logs in JSON format to stdout (for Railway log aggregation). Sentry for error tracking and alerting. Structured fields: timestamp, level, message, request_id, user_id, module, duration_ms. Sensitive data (passwords, tokens, PII) excluded from logs. |

---

## Executive Summary

SAPv2 is an AI-augmented security review platform designed to provide **consistent, auditable, and reproducible** analysis of security data across multiple review types including user access reviews, firewall rule reviews, and other periodic security assessments required by banking regulations.

The platform separates **deterministic data processing** from **AI-assisted interpretation** to ensure that the same input data always produces the same findings -- a critical requirement for regulatory compliance and audit defensibility. AI enrichment is powered by a **provider-agnostic abstraction layer** supporting multiple LLM backends (OpenAI, Azure OpenAI, Anthropic Claude, Google Gemini, AWS Bedrock, Ollama for local/air-gapped deployments, and any OpenAI-compatible endpoint), with per-function model routing, automatic fallback chains, and data classification enforcement to ensure compliance with institutional data handling requirements.

### Market Context

Community banks (~4,500 FDIC-insured institutions in the US, managing approximately $2.3 trillion in combined assets) face a massive gap between manual spreadsheet-based access reviews ($0 tooling cost but enormous labor and audit risk) and enterprise IAM/GRC platforms ($75K+ license plus $150K+ implementation with 6-18 month deployment timelines). Conservative estimates suggest community banks spend 200-400 analyst hours annually on access reviews alone, with 84% of IT-related MRAs citing insufficient internal controls. SAPv2 fills this gap with enterprise-grade compliance capabilities at community bank scale and price.

### Core Differentiators

1. **Deterministic AI**: "AI Never Counts, AI Never Decides Severity" -- addresses regulatory concerns about AI accountability
2. **Examination-Ready**: Pre-built FFIEC/OCC/GLBA/SOX alignment with examiner-ready reporting and one-click evidence package generation
3. **Deploy in Weeks**: Pre-built templates for common core banking systems (Jack Henry, FIS, Fiserv)
4. **Unified Platform**: Access reviews + firewall rule reviews in a single tool
5. **Spreadsheet-Friendly**: Familiar paradigms for users comfortable with Excel
6. **Multi-Provider AI**: LLM-agnostic architecture supports any AI provider with automatic failover, cost tracking, and compliance-aware provider selection

---

## Problem Statement

Financial institutions must perform regular security reviews (user access reviews, firewall reviews, etc.) across dozens of applications and systems. Current challenges include:

1. **Inconsistency**: Manual reviews produce varying results depending on the reviewer
2. **Time-intensive**: Each review requires significant analyst time to process exports and identify findings
3. **No institutional memory**: Lessons learned from previous reviews are not systematically applied
4. **Audit risk**: Inability to demonstrate consistent methodology across review periods
5. **AI unpredictability**: Direct AI analysis of documents produces different results on each run, making it unsuitable for compliance use cases
6. **Regulatory exposure**: 84% of IT-related MRAs (Matters Requiring Attention) cite insufficient internal controls as root cause -- common examination findings include excessive privileges, access not updated after job changes, dormant accounts, and missing documentation of review decisions

### The Core Technical Challenge

Large Language Models are inherently probabilistic. Asking an LLM to "analyze this user list and find inactive accounts" will produce different counts, different findings, and different recommendations each time. This is unacceptable for:

- Regulatory examinations where methodology must be defensible
- Audit trails that require reproducibility
- Trend analysis across review periods
- Quality assurance and peer review processes

AI hallucination rates for legal/regulatory information reach 6.4% compared to 0.8% for general knowledge. In compliance contexts, fabricated regulatory references could lead to examination failures. SAPv2 addresses this by confining AI to enrichment roles where hallucination risk is manageable and human-reviewable.

---

## Solution Architecture

SAPv2 addresses the consistency problem through a **three-layer architecture** that isolates non-deterministic AI functions from deterministic analysis, with a **provider abstraction layer** enabling any LLM backend and a **structured error handling layer** ensuring graceful recovery at every stage:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        LAYER 1: CONFIGURATION                          │
│                    (Human-defined, deterministic)                       │
├────────────────────────────────────────────────────────────────────────┤
│  • Frameworks: Define WHAT to check (rules, thresholds, severities)    │
│  • Applications: Define HOW to extract data (mappings, transforms)     │
│  • Review Templates: Define WHEN and WHO (schedules, assignments)      │
│                                                                        │
│  AI Role: ASSISTANT - helps create configurations, never executes      │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        LAYER 2: EXTRACTION                             │
│                    (Template-driven, deterministic)                     │
├────────────────────────────────────────────────────────────────────────┤
│  • Document ingestion and parsing with confidence scoring              │
│  • Column/field mapping per saved application template                 │
│  • Value transformation (date formats, status codes, etc.)             │
│  • Data normalization into canonical schemas                           │
│  • Validation and human confirmation checkpoint                        │
│                                                                        │
│  AI Role: FALLBACK ONLY - when no template exists, proposes mapping    │
│           Human must approve before any extraction is finalized         │
│           Confidence threshold: 95% — below requires human review      │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        LAYER 3: ANALYSIS                               │
│                    (Rule-based, deterministic)                          │
├────────────────────────────────────────────────────────────────────────┤
│  • Execute framework checks against normalized data (JSON Logic)       │
│  • Generate findings with consistent counts and categorization         │
│  • Apply severity ratings per framework definitions                    │
│  • Produce audit trail of exactly which rules triggered                │
│  • Generate plain-English rule explainability output                   │
│                                                                        │
│  AI Role: ENRICHMENT ONLY - after deterministic analysis complete:     │
│           • Generate human-readable finding descriptions               │
│           • Suggest contextual remediation steps                       │
│           • Identify patterns across findings                          │
│           • Draft executive summary language                           │
│           All AI output labeled, scored, and human-reviewable          │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                  AI PROVIDER ABSTRACTION LAYER                          │
│              (LLM-agnostic, configurable per function)                  │
├────────────────────────────────────────────────────────────────────────┤
│  • AIProviderBase: unified interface (complete, stream, health_check)  │
│  • AIProviderManager: per-function routing, fallback chains, retry     │
│  • Providers: OpenAI | Azure OpenAI | Anthropic | Gemini | Bedrock    │
│               | Ollama (local) | OpenAI-compatible | Mock (testing)    │
│  • Structured output: native where supported, schema-in-prompt fallback│
│  • Data classification enforcement (public/internal/confidential/      │
│    restricted) restricts which providers may handle institution data   │
│  • Cost tracking, token accounting, and invocation logging             │
└────────────────────────────────────────────────────────────────────────┘
```

### Key Principle: AI Never Counts, AI Never Decides Severity

The system enforces a strict boundary:

| Function | Handled By | Why |
|----------|------------|-----|
| Record counting | Code (deterministic) | Must be reproducible |
| Threshold comparison | Code (deterministic) | Must be reproducible |
| Severity assignment | Code (per framework rules) | Must be auditable |
| Pattern matching | Code (regex, exact match) | Must be reproducible |
| Cross-reference matching | Code (deterministic join) | Must be reproducible |
| Rule explainability | Code (template-driven) | Documents why each finding triggered |
| Finding descriptions | AI (enrichment) | Adds value, doesn't affect outcome |
| Remediation suggestions | AI (enrichment) | Adds value, human reviews anyway |
| Executive summaries | AI (enrichment) | Adds value, human reviews anyway |
| Compliance determinations | **PROHIBITED for AI** | Regulatory risk too high |

---

## Regulatory Alignment

### FFIEC Requirements Mapping

SAPv2 aligns with the FFIEC IT Examination Handbook, particularly the Information Security and Access Management booklets:

| FFIEC Requirement | SAPv2 Feature |
|-------------------|---------------|
| Periodic review of access rights | Configurable review schedules with risk-based defaults |
| Documented review methodology | Framework versioning with immutable audit trail |
| Evidence of review completion | Attestation workflow with digital signatures |
| Timely removal of terminated access | Cross-reference checks between HR and application data |
| Segregation of duties monitoring | Role combination checking with prohibited pairs |
| Privileged access management | Role-match checks for admin/elevated access |
| Audit trail of access changes | Regulatory-grade hash-chained audit log |

### OCC Heightened Standards Alignment (12 CFR Part 30, Appendix D)

While primarily applicable to banks with $50B+ in assets, OCC Heightened Standards set industry expectations that trickle down to community bank examinations as reference benchmarks:

| Heightened Standard | SAPv2 Feature |
|---------------------|---------------|
| Risk governance framework | Framework versioning with regulatory mappings and lifecycle management |
| Independent risk management | Separation of review creator and approver roles (enforced) |
| Comprehensive risk assessment | Configurable check types covering multiple risk categories with cross-reference correlation |
| Audit and reporting | Hash-chained audit trail with compliance reporting and evidence package generation |
| Talent management (competency) | Role-based access ensuring qualified reviewers with delegation support |

### SOX Considerations

For publicly traded institutions or subsidiaries of public holding companies, SAPv2's architecture aligns with Sarbanes-Oxley requirements:

| SOX Requirement | SAPv2 Alignment |
|-----------------|-----------------|
| Section 404: Internal control assessment | Framework checks document and enforce control testing methodology |
| Control evidence retention | 7+ year audit trail with immutable logging and hash-chain verification |
| Management attestation | Review approval workflow with digital signatures and separation of duties |
| IT General Controls (ITGCs) | User access review serves as primary ITGC evidence |
| Control testing documentation | Explainability templates document methodology; evidence packages bundle all artifacts |

Note: Application data classification field supports marking systems as "SOX-relevant" for additional control requirements and audit attention.

### Risk-Based Review Schedule Defaults

| System Classification | Default Frequency | Regulatory Basis |
|----------------------|-------------------|------------------|
| Privileged/Administrative accounts | Quarterly (monthly recommended) | FFIEC elevated risk |
| Financial systems / Customer PII | Quarterly | GLBA Safeguards Rule |
| Standard business applications | Semi-annually | Risk-based approach |
| Low-risk systems | Annually (minimum) | FFIEC baseline |

These defaults are configurable per application. The system shall enforce that no application goes beyond its maximum review interval without generating an alert.

### NIST CSF Alignment

Framework checks shall support mapping to NIST Cybersecurity Framework categories:

- **Identify (ID)**: Asset management, risk assessment
- **Protect (PR)**: Access control, awareness training, data security
- **Detect (DE)**: Anomalies and events, security monitoring
- **Respond (RS)**: Response planning, communications
- **Recover (RC)**: Recovery planning, improvements

### Data Retention Policy

All data generated or ingested by SAPv2 is subject to regulatory retention requirements. The following retention schedule applies:

| Data Category | Retention Period | Storage Tier | Archive Method |
|---------------|-----------------|--------------|----------------|
| Audit log entries | 7 years minimum | Hot (2 years) / Cold (5+ years) | Monthly partition archival to S3 (Parquet, encrypted) |
| Review records (metadata) | 7 years minimum | Hot (2 years) / Cold (5+ years) | Post-review archival |
| Source documents (originals) | 7 years minimum | Cold storage after review closes | S3 lifecycle policy with server-side encryption |
| Extracted data | 7 years minimum | Cold storage after review closes | Database archival |
| Findings with dispositions | 7 years minimum | Hot (indefinite) | Always queryable |
| AI enrichment outputs | 5 years minimum | Cold storage after review closes | Database archival |
| Framework versions | Indefinite | Hot | Never purged (required for historical review context) |
| User accounts | Duration of employment + 3 years | Hot | Deactivated, not deleted |

The system shall support **legal hold** that prevents automatic archival or deletion of specified review data during examinations or litigation. Archived records shall be retrievable within 4 business hours of request.

### Examiner Access Mode

Regulatory examiners (OCC, state banking departments, external auditors) increasingly require direct system access during examinations rather than relying solely on exported reports.

The system shall support an **Examiner** user role with:

- Read-only access to all reviews, findings, frameworks, and audit logs
- Ability to verify hash chain integrity directly within the platform
- Ability to export any data in JSON/CSV format for independent analysis
- No ability to create, modify, or delete any records
- Session logging with enhanced detail (all data accessed is recorded)
- Temporary access with configurable expiration (default 90 days)
- No count against regular user license limits

Examiner access shall be provisioned by an admin with specific scope (all reviews, specific applications, or date ranges), automatic expiration, full audit trail of examiner activity, and notification to bank admin of all examiner sessions.

### Regulatory Change Management

When regulatory frameworks are updated (e.g., FFIEC IT Examination Handbook revisions, NIST CSF updates), the system shall support a structured change management process:

- Regulatory reference frameworks shall have their own version tracking (e.g., FFIEC Handbook v2024.1)
- When a regulatory framework is updated, the system shall identify all SAPv2 frameworks that reference it
- The system shall generate a "regulatory change impact assessment" showing which checks may need updating
- Administrators can create framework update tasks from regulatory change notifications
- The system shall maintain a regulatory reference library with imported regulatory control frameworks, version tracking, and mappings between regulatory controls and SAPv2 framework checks
- A dashboard widget shall display regulatory framework currency status (up-to-date, update available, review needed)

### Evidence Package Generation

During regulatory examinations, institutions typically have 2-4 weeks to produce evidence. Manual assembly of individual reports, audit logs, framework definitions, and methodology documentation is time-consuming and error-prone.

The system shall generate an **Examination Evidence Package** containing:

1. Methodology documentation (framework version, check definitions in plain English)
2. Review summary with all findings and dispositions
3. Complete audit trail for the review with hash verification status
4. Source document hashes for integrity verification
5. Extraction validation details with confidence scores
6. AI enrichment log (what was AI-generated, what was human-written)
7. Attestation records with signatures and timestamps
8. Exception documentation with compensating controls
9. Trend analysis vs. prior periods
10. Table of contents with page references

Format: ZIP archive containing organized PDF reports + raw JSON data files. Naming convention: `{BankName}_{ApplicationName}_{ReviewPeriod}_{GeneratedDate}`. Evidence package generation shall be available for individual reviews or for all reviews within a date range.

### Common Examination Deficiencies Addressed

| Examination Finding | SAPv2 Prevention |
|--------------------|------------------|
| Accounts with excessive privileges | Privileged access review check |
| Access not updated after job changes | Cross-reference with HR data |
| Dormant accounts remaining active | Inactive account detection with configurable thresholds |
| Terminated employee access not removed | Cross-document correlation (critical severity) |
| Missing documentation of review decisions | Immutable audit trail with attestation |
| Inconsistent review methodology | Framework versioning ensures same rules every time |
| No evidence of periodic review | Review lifecycle tracking with compliance calendar |
| Segregation of duties violations | Role combination checking |
| Insufficient evidence for examiners | One-click evidence package generation with hash verification |
| No documented compensating controls | Structured exception documentation with expiration tracking |

---
## Functional Requirements

### 1. Framework Management

A Framework defines the methodology for a type of security review. Frameworks contain executable rules stored as JSON Logic, not prose descriptions. Frameworks follow a formal lifecycle from draft through publication to eventual archival, with version control and approval gates ensuring rule quality.

#### 1.1 Framework Structure

```yaml
framework:
  id: uuid
  name: "User Access Review - Standard"
  description: "Quarterly review of user access for compliance with access management policy"
  version: "1.0.0"  # Semantic versioning: MAJOR.MINOR.PATCH
  lifecycle_state: "published"  # draft | published | deprecated | archived
  effective_date: "2026-01-01"
  expiration_date: null  # null = no expiration
  review_type: "user_access"
  superseded_by: null  # UUID of replacement framework (set when deprecated)
  regulatory_mappings:
    - framework: "FFIEC"
      category: "Access Management"
      controls: ["AC-1", "AC-2", "AC-6"]
    - framework: "NIST_CSF"
      category: "Protect"
      subcategory: "PR.AC"

  # Global settings for this framework
  settings:
    inactive_threshold_days: 90
    review_period_months: 3
    require_manager_attestation: true
    high_limit_threshold: 1000000

  # Executable check definitions stored as JSON Logic
  checks:
    - id: "inactive_accounts"
      name: "Inactive User Accounts"
      description: "Accounts with no login activity beyond threshold"
      enabled: true

      # Severity is ALWAYS defined explicitly, never inferred
      severity_rules:
        - condition: { ">": [{"var": "days_inactive"}, 180] }
          severity: "high"
        - condition: { ">": [{"var": "days_inactive"}, 90] }
          severity: "medium"
      default_severity: "medium"

      # The actual logic as JSON Logic -- deterministic
      condition:
        type: "compound"
        operator: "AND"
        conditions:
          - type: "date_comparison"
            field: "last_activity"
            operator: "older_than_days"
            value: "${settings.inactive_threshold_days}"
          - type: "value_equals"
            field: "status"
            operator: "equals"
            value: "active"

      # What to include in the finding
      output_fields:
        - identifier
        - display_name
        - last_activity
        - department
        - roles

      # Plain-English explainability template
      explainability_template: |
        This check flags active accounts where the last login date is more
        than ${settings.inactive_threshold_days} days ago. Found ${record_count}
        accounts matching this condition out of ${total_filtered} active accounts.

      # Guidance for AI enrichment (AI reads this, doesn't execute it)
      remediation_guidance: |
        Accounts inactive for extended periods should be reviewed with
        the user's manager. If the user no longer requires access,
        disable or remove the account.

    - id: "segregation_of_duties"
      name: "Segregation of Duties Violation"
      description: "Users with conflicting role combinations"
      severity_rules:
        - condition: { "in": [{"var": "violation_type"}, ["wire", "ach"]] }
          severity: "critical"
        - condition: true
          severity: "high"
      default_severity: "high"
      enabled: true

      condition:
        type: "role_combination"
        mode: "any_prohibited_pair"
        prohibited_pairs:
          - ["AP Clerk", "AP Approver"]
          - ["Wire Initiator", "Wire Approver"]
          - ["ACH Originator", "ACH Approver"]
          - ["User Administrator", "Security Administrator"]

      output_fields:
        - identifier
        - display_name
        - roles
        - department

      explainability_template: |
        This check identifies users who hold two roles that should not be
        combined per segregation of duties policy. Found ${record_count}
        users with prohibited role combinations.

      remediation_guidance: |
        Segregation of duties violations must be remediated by removing
        one of the conflicting roles, or documented as an approved
        exception with compensating controls.

    - id: "terminated_with_access"
      name: "Terminated Employee with Active Access"
      description: "Cross-reference with HR termination data"
      severity_rules:
        - condition: { ">": [{"var": "days_since_termination"}, 30] }
          severity: "critical"
        - condition: { ">": [{"var": "days_since_termination"}, 7] }
          severity: "high"
        - condition: { ">=": [{"var": "days_since_termination"}, 0] }
          severity: "medium"
      default_severity: "critical"
      enabled: true

      condition:
        type: "cross_reference"
        mode: "present_in_primary_absent_in_secondary"
        primary_dataset: "application_users"
        secondary_dataset: "hr_active_employees"
        match_field: "identifier"

      filter:
        field: "account_type"
        operator: "equals"
        value: "human"

      output_fields:
        - identifier
        - display_name
        - status
        - roles

      explainability_template: |
        This check cross-references application user accounts against the
        HR active employee list. Users found in the application but NOT in
        the HR active list may be terminated employees with lingering access.
        Found ${record_count} accounts requiring investigation.

      remediation_guidance: |
        Access for terminated employees must be removed immediately.
        Investigate any activity since termination date.

    - id: "privileged_access"
      name: "Privileged Access Review"
      description: "Accounts with administrative or elevated privileges"
      default_severity: "info"
      enabled: true

      condition:
        type: "role_match"
        mode: "any"
        patterns:
          - "*Admin*"
          - "*Administrator*"
          - "*Supervisor*"
          - "Security*"
          - "System*"

      output_fields:
        - identifier
        - display_name
        - roles
        - department
        - manager

      explainability_template: |
        This check identifies accounts with administrative or elevated
        privilege roles that require manager attestation. Found ${record_count}
        privileged accounts for review.

      remediation_guidance: |
        Privileged accounts require manager attestation that access
        is still required for job function.
```

#### 1.2 Framework Lifecycle

Frameworks progress through a formal lifecycle that ensures quality, prevents accidental use of untested rules, and supports graceful retirement of outdated frameworks.

```
                          ┌────────────────────┐
                          │       DRAFT        │
                          │  (in development)  │
                          └─────────┬──────────┘
                                    │ publish (requires approval)
                                    ▼
                          ┌────────────────────┐
                          │     PUBLISHED      │
                          │  (active, usable)  │
                          └────┬──────────┬────┘
                               │          │
                   deprecate   │          │ new version published
                               ▼          │ (auto-deprecates this one)
                  ┌────────────────────┐   │
                  │    DEPRECATED      │◀──┘
                  │  (warning shown)   │
                  └─────────┬──────────┘
                            │ archive
                            ▼
                  ┌────────────────────┐
                  │     ARCHIVED       │
                  │   (read-only)      │
                  └────────────────────┘
```

**Lifecycle State Definitions:**

| State | Description | Allowed Actions | Transition To |
|-------|-------------|-----------------|---------------|
| **DRAFT** | Framework is under development, not usable for reviews | Edit checks, edit settings, run dry-run tests, clone, delete, submit for approval | PUBLISHED (via approval) |
| **PUBLISHED** | Active framework, can be selected for new reviews | Clone, deprecate, view; editing creates a new DRAFT version | DEPRECATED (manual or automatic when newer version published) |
| **DEPRECATED** | Still usable but displays warning; no longer recommended for new reviews | Archive, view; existing reviews using it continue unaffected | ARCHIVED |
| **ARCHIVED** | Preserved for audit trail, cannot be selected for new reviews | View only; historical reviews referencing it remain intact | (terminal state) |

#### 1.3 Framework Approval and Publishing Workflow

Publishing a framework from DRAFT to PUBLISHED requires validation and approval to prevent misconfigured rules from affecting production reviews.

**Publishing Prerequisites:**
1. All checks pass syntax validation (JSON Logic expressions are well-formed)
2. At least one successful dry-run test against sample data has been executed
3. A change summary is provided documenting what changed from the previous version (for version 1.0.0, a description of the framework's purpose)
4. An effective date is set (cannot be in the past)

**Approval Workflow:**
1. Analyst marks framework as "Ready for Review"
2. System validates all publishing prerequisites are met
3. User with `admin` or `framework_publisher` role receives notification
4. Approver reviews the framework: check definitions, test results, and change summary
5. Approver can:
   - **Approve**: framework transitions to PUBLISHED, `is_immutable` is set to true
   - **Reject**: framework returns to DRAFT with reviewer comments
   - **Request Changes**: framework stays in DRAFT, analyst is notified with specific feedback
6. Published frameworks cannot be modified; any change requires creating a new version in DRAFT state

#### 1.4 Framework Testing and Validation

Before a framework can be published, it must pass validation to ensure rule correctness and prevent false positives or false negatives in production reviews.

**Mandatory Validation (blocks publishing):**
- **Syntax validation**: All JSON Logic expressions are parseable and well-formed
- **Severity rule coverage**: Every check has at least one severity rule or a `default_severity`
- **Output field validation**: All `output_fields` reference valid canonical schema fields for the framework's `review_type`
- **Cross-reference check validation**: Cross-reference checks reference valid dataset types
- **Explainability template validation**: Template variables reference valid context fields

**Recommended Validation (warning, does not block):**
- **Positive test**: Each check has been tested with data that triggers it (at least one finding produced)
- **Negative test**: Each check has been tested with data that does NOT trigger it (zero findings for that check)
- **Conditional severity test**: Severity rules have been evaluated across multiple conditions
- **Performance benchmark**: Analysis completes within acceptable thresholds for a sample dataset of at least 1,000 records

**Test Dataset Library:**
- System shall maintain a library of test datasets per review type that can be used for framework validation
- Test datasets are uploaded and managed independently of review data
- Test datasets can be shared across framework development efforts
- Dry-run results are stored and associated with the framework version for audit purposes

#### 1.5 Framework Import and Export

Frameworks can be exported for sharing and imported from external sources, enabling distribution of pre-built templates and collaboration between institutions.

**Export:**
- System shall support framework export as a portable JSON package including: framework definition, check definitions, settings, regulatory mappings, and sample test data (with PII removed)
- Export format includes a schema version identifier for compatibility checking
- Export excludes institution-specific data (review history, user assignments)

**Import:**
- System shall support framework import from JSON package with:
  - Validation against the current schema version
  - Conflict detection with existing frameworks (name and version collision check)
  - Import always creates a DRAFT framework (never directly as PUBLISHED)
  - Attribution to original author and source institution
  - Imported checks are re-validated against current JSON Logic engine rules

**Starter Framework Library:**
- System shall include a built-in library of pre-built frameworks for common review types that can be imported and customized:
  - User Access Review -- Standard (FFIEC aligned)
  - User Access Review -- Privileged (enhanced checks for admin accounts)
  - Firewall Rule Review -- Standard (Phase 4)
- Starter frameworks are maintained as version-controlled JSON files within the application

#### 1.6 Framework Requirements

- **FR-1.1**: System shall allow creation, editing, versioning (semantic: MAJOR.MINOR.PATCH), and cloning of frameworks
- **FR-1.2**: Framework checks shall be defined using JSON Logic stored as structured rule definitions, not natural language
- **FR-1.3**: System shall support the following condition types:
  - Date comparison (older_than, newer_than, between)
  - Value comparison (equals, not_equals, contains, matches_pattern)
  - Value in list (value matches any item in a set)
  - Role/permission matching (exact, wildcard, regex)
  - Role combination checking (prohibited pairs, required pairs)
  - Cross-reference between datasets
  - Numeric thresholds (greater_than, less_than, between)
  - Null/empty field checking
  - **Compound conditions** (AND, OR, NOT) for combining multiple conditions
- **FR-1.4**: Each check shall have explicit severity rules -- severity is NEVER inferred or AI-determined. Severity rules support conditional severity based on finding attributes (e.g., days since termination)
- **FR-1.5**: Checks shall support enable/disable toggle without deletion
- **FR-1.6**: Framework changes shall create new immutable versions. Old versions are preserved for audit trail reconstruction. Versions include effective_date and expiration_date
- **FR-1.7**: System shall prevent modification of frameworks while reviews are in progress using that framework version
- **FR-1.8**: Each check shall include an explainability_template that generates plain-English explanation of why findings were triggered, including record counts and threshold values
- **FR-1.9**: Frameworks shall support regulatory_mappings linking checks to FFIEC, NIST CSF, and other regulatory control identifiers
- **FR-1.10**: System shall support rule dependency management -- checks that depend on other checks' outputs shall be topologically sorted for execution order
- **FR-1.11**: System shall provide "dry run" capability to test framework checks against sample data before publishing
- **FR-1.12**: Frameworks shall follow a formal lifecycle with states: DRAFT, PUBLISHED, DEPRECATED, ARCHIVED. Only PUBLISHED frameworks can be selected for new reviews. DEPRECATED frameworks display a warning with a link to the replacement framework. ARCHIVED frameworks are preserved for historical review reference but cannot be used for new reviews
- **FR-1.13**: Framework publishing shall require syntax validation, at least one successful dry-run test, approval by an authorized user (admin or framework_publisher role), a change summary, and an effective date
- **FR-1.14**: System shall enforce an approval workflow for framework publishing: analyst submits for review, approver can approve, reject, or request changes, with full audit trail of the approval decision
- **FR-1.15**: Before publishing, framework must pass mandatory validation: JSON Logic syntax, severity rule coverage, output field validity, cross-reference dataset type validity, and explainability template variable validity
- **FR-1.16**: System shall maintain a library of test datasets per review type for framework validation, and store dry-run results associated with the framework version
- **FR-1.17**: System shall support framework export as a portable JSON package and import from JSON package, with imported frameworks always entering DRAFT state
- **FR-1.18**: System shall include a starter framework library with pre-built frameworks for common review types
- **FR-1.19**: When a new framework version is published, existing active reviews continue using the version locked at review creation. The system shall display a notification that a newer version is available and allow re-analysis with the new version (see FR-3.18)
- **FR-1.20**: Framework version history shall include a changelog showing: checks added, removed, or modified; threshold changes; severity rule changes; and settings changes
- **FR-1.21**: System shall support regulatory mapping versioning. When a regulatory framework is updated, the system identifies all SAPv2 frameworks that reference it and generates a regulatory change impact assessment

---

### 2. Application Management

An Application represents a system being reviewed. Applications define the context of the system, who uses it, its criticality, and how data is extracted from that system's exports.

#### 2.1 Application Structure

```yaml
application:
  id: uuid
  name: "Jack Henry Silverlake Core"
  description: "Core banking system for deposit and loan accounts"
  owner: "Operations Department"
  owner_email: "ops-manager@keysbank.com"
  review_type: "user_access"
  criticality: "high"
  data_classification: "confidential"  # public, internal, confidential, restricted

  # Risk-based review schedule
  review_schedule:
    frequency: "quarterly"
    next_review_date: "2026-04-01"
    reminder_days_before: [30, 14, 7]
    escalation_after_days: 14  # Days past due before escalation

  # Context for AI-generated recommendations and examiner documentation
  context: |
    This is the bank's core banking platform handling all deposit
    and loan transactions. Access to this system is highly sensitive.
    The system contains PII and financial data subject to GLBA.
    Approximately 85 users across 6 branch locations.

  # Regulatory context
  regulatory_scope:
    - "GLBA"
    - "FFIEC"
    - "BSA/AML"

  # Role descriptions for context-aware analysis
  role_definitions:
    - role: "Teller"
      description: "Front-line staff processing customer transactions"
      risk_level: "medium"
      typical_count: 45
    - role: "Supervisor"
      description: "Branch supervisors with override capabilities"
      risk_level: "high"
      typical_count: 12
    - role: "System Administrator"
      description: "IT staff with full system access"
      risk_level: "critical"
      typical_count: 3

  # Document templates -- how to extract data from this app's exports
  document_templates:
    - id: "user_security_report"
      name: "User Security Report"
      description: "Standard user listing from JH Silverlake"
      format: "csv"

      # How to detect this document type
      detection:
        method: "column_presence"
        required_columns:
          - "USER_ID"
          - "USER_NAME"
          - "SECURITY_PROFILE"
        confidence_threshold: 0.95  # Minimum match confidence

      # Mapping to canonical user_access schema
      mapping:
        identifier:
          source: "USER_ID"
          transform: "lowercase"
        display_name:
          source: "USER_NAME"
        status:
          source: "USER_STATUS"
          transform: "value_map"
          value_map:
            "A": "active"
            "I": "inactive"
            "D": "disabled"
            "L": "locked"
        last_activity:
          source: "LAST_LOGON_DT"
          transform: "parse_date"
          date_format: "MM/DD/YYYY HH:mm:ss"
        roles:
          source: "SECURITY_PROFILE"
          transform: "split"
          delimiter: ";"
        department:
          source: "BRANCH_NAME"
        account_type:
          source: "USER_TYPE"
          transform: "value_map"
          value_map:
            "E": "human"
            "S": "service"
            "B": "system"
          default: "human"

      # Validation rules
      validation:
        - field: "identifier"
          rule: "required"
        - field: "identifier"
          rule: "unique"
        - field: "last_activity"
          rule: "valid_date"

    - id: "audit_log_export"
      name: "Daily Audit Log"
      description: "Activity log for supplemental analysis"
      format: "csv"
      detection:
        method: "column_presence"
        required_columns:
          - "AUDIT_TIMESTAMP"
          - "USER_ID"
          - "ACTION_CODE"
      mapping:
        timestamp:
          source: "AUDIT_TIMESTAMP"
          transform: "parse_date"
          date_format: "YYYY-MM-DD HH:mm:ss"
        user_id:
          source: "USER_ID"
          transform: "lowercase"
        action:
          source: "ACTION_CODE"
        details:
          source: "ACTION_DESC"
```

#### 2.2 Multi-Schema Support

The extracted records storage must support multiple review types with different canonical schemas. Phase 1 implements user access review; Phase 4 adds firewall rule review.

**Strategy:** Use a single `extracted_records` table with:
- Common fields shared across all review types (id, extraction_id, record_index, identifier, display_name, validation_status)
- A `record_type` discriminator column (`user_access`, `firewall_rule`)
- A `data` JSONB column for schema-specific fields
- Normalized fields needed for cross-reference matching (identifier, email)

Phase 1 implements `record_type = 'user_access'` only. Phase 4 adds `record_type = 'firewall_rule'` without schema migration, using the JSONB `data` column for firewall-specific fields (rule_id, rule_name, source, destination, port, protocol, action).

#### 2.3 Application Import and Export

Applications and their associated document templates can be exported and imported to support sharing configurations between environments and institutions.

**Export Package Contents:**
- Application definition (name, description, owner, criticality, context, role definitions, review schedule)
- All associated document templates with detection rules and field mappings
- Excludes review history and institution-specific data

**Import Behavior:**
- Imported applications are created in an editable state
- Conflict detection on application name (warn if duplicate)
- Templates are imported with full mapping definitions
- Validation of template field references against the canonical schema for the application's review type

#### 2.4 Application Requirements

- **FR-2.1**: System shall allow creation and management of application definitions including owner, criticality, data classification, and regulatory scope
- **FR-2.2**: Each application shall be associated with a review type (user_access, firewall, etc.)
- **FR-2.3**: Applications shall support multiple document templates for different export types
- **FR-2.4**: Document templates shall include automatic detection rules with confidence scoring
- **FR-2.5**: Mappings shall support the following transformations:
  - Direct copy
  - Lowercase/uppercase
  - Value mapping (lookup table with default value)
  - Date parsing with format specification
  - String splitting (for multi-value fields)
  - Concatenation of multiple source fields
  - Regex extraction
  - Default values for missing data
  - Numeric parsing
  - Boolean conversion
- **FR-2.6**: System shall validate extracted data against defined rules before proceeding
- **FR-2.7**: System shall display extraction summary for human confirmation:
  - Total records extracted
  - Valid records count
  - Records with warnings (expandable details)
  - Sample preview (first 10 records in tabular format)
  - Extraction confidence score (prominent display)
  - Comparison to previous review period (if available): record count delta, new accounts, removed accounts
- **FR-2.8**: Applications shall have configurable review schedules with reminder notifications and escalation rules
- **FR-2.9**: Application context and role definitions shall be available to AI enrichment functions for generating contextually relevant recommendations
- **FR-2.10**: System shall track application review history showing all past reviews, findings trends, and remediation effectiveness
- **FR-2.11**: System shall support bulk operations on applications: bulk status change (activate/deactivate), bulk assignment of review schedules, and bulk export of application configurations
- **FR-2.12**: Extracted records storage shall use a multi-schema strategy with a `record_type` discriminator and a JSONB `data` column for schema-specific fields, enabling support for multiple review types (user_access, firewall_rule) without schema migration
- **FR-2.13**: System shall support application import and export as portable JSON packages including all associated document templates and field mappings

---

### 3. Review Workflow

A Review is an instance of applying a Framework to an Application for a specific review period. The review workflow is the core operational flow of SAPv2. It supports error recovery, rejection and rework, multi-reviewer collaboration, and SLA enforcement.

#### 3.1 Review Lifecycle

```
                         ┌─────────────────────────┐
                         │        CREATED           │
                         │  (framework + app set)   │
                         └───────────┬──────────────┘
                                     │ upload docs
                                     ▼
                    ┌───────────────────────────────────┐
                    │       DOCUMENTS_UPLOADED           │
                    │                                   │◄──── re-upload from
                    └──────────┬──────────┬─────────────┘      EXTRACTION_FAILED
                               │          │                    or REJECTED
                      extract  │          │ extract fails
                      success  │          │
                               ▼          ▼
            ┌──────────────────┐    ┌────────────────────┐
            │    EXTRACTED     │    │ EXTRACTION_FAILED   │
            │ (awaiting        │    │ (show error, allow  │
            │  confirmation)   │    │  re-upload/retry)   │
            └────────┬─────────┘    └────────────────────┘
                     │ confirm extraction
                     ▼
            ┌──────────────────┐
            │    ANALYZED      │◄──── retry from ANALYSIS_FAILED
            │                  │◄──── re-analyze with updated framework
            └────────┬────┬────┘
                     │    │
            success  │    │ error
                     ▼    ▼
  ┌──────────────────┐  ┌────────────────────┐
  │ FINDINGS_GEN'D   │  │  ANALYSIS_FAILED   │
  │                  │  │  (diagnostics)     │
  └────────┬─────────┘  └────────────────────┘
           │ assign reviewers
           ▼
  ┌──────────────────┐
  │  PENDING_REVIEW  │◄──── rework from RETURNED
  │                  │
  └──┬─────┬─────┬───┘
     │     │     │
     │     │     │ reject (full review)
     │     │     ▼
     │     │  ┌────────────────┐
     │     │  │    REJECTED    │──── back to DOCUMENTS_UPLOADED
     │     │  │  (full redo)   │     or CREATED
     │     │  └────────────────┘
     │     │
     │     │ return specific findings
     │     ▼
     │  ┌────────────────┐
     │  │    RETURNED    │──── creator addresses, back to PENDING_REVIEW
     │  │  (partial fix) │
     │  └────────────────┘
     │
     │ all dispositions complete
     ▼
  ┌──────────────────┐
  │    APPROVED      │
  │  (final sign-off)│
  └────────┬─────────┘
           │ close
           ▼
  ┌──────────────────┐
  │     CLOSED       │
  │  (archived)      │
  └──────────────────┘

  *** CANCELLED can be reached from any non-terminal state ***
```

**State Definitions:**

| State | Description | Allowed Actions | Next States |
|-------|-------------|-----------------|-------------|
| **CREATED** | Review initiated, framework and application assigned | Upload documents, edit review metadata, cancel | DOCUMENTS_UPLOADED, CANCELLED |
| **DOCUMENTS_UPLOADED** | Source documents attached | Run extraction, upload more documents, remove documents, cancel | EXTRACTED, EXTRACTION_FAILED, CANCELLED |
| **EXTRACTION_FAILED** | Extraction process encountered an error (parser failure, corrupt file, timeout) | Re-upload document, retry extraction with different settings, view error diagnostics, cancel | DOCUMENTS_UPLOADED (re-upload), CANCELLED |
| **EXTRACTED** | Data normalized, extraction summary displayed for human review | Confirm extraction, reject and re-upload, view sample data, cancel | ANALYZED (after confirmation), DOCUMENTS_UPLOADED (rejection), CANCELLED |
| **ANALYZED** | Framework checks executed, deterministic findings generated | Run AI enrichment, review findings, add notes, re-analyze with different framework version, cancel | FINDINGS_GENERATED, ANALYSIS_FAILED, CANCELLED |
| **ANALYSIS_FAILED** | Analysis engine encountered an error (bad data, rule evaluation failure) | View diagnostic information, fix data issues, retry analysis, cancel | ANALYZED (retry), CANCELLED |
| **FINDINGS_GENERATED** | AI enrichment complete (or skipped), findings ready for review | Edit AI content, regenerate AI content, assign reviewers, cancel | PENDING_REVIEW, CANCELLED |
| **PENDING_REVIEW** | Assigned to reviewer(s) for attestation and disposition | Approve/revoke/abstain per finding, add notes, request changes, bulk disposition, reject review, return findings, cancel | APPROVED, REJECTED, RETURNED, CANCELLED |
| **RETURNED** | Specific findings sent back for rework by reviewer | Creator addresses returned findings, re-submit | PENDING_REVIEW, CANCELLED |
| **REJECTED** | Reviewer rejected entire review (stale data, wrong framework, quality issues) | Re-upload documents, restart from creation | DOCUMENTS_UPLOADED, CREATED, CANCELLED |
| **APPROVED** | Review complete, all findings dispositioned with attestation | Generate reports, close review, cancel (admin only) | CLOSED, CANCELLED (admin only) |
| **CLOSED** | Review archived, locked from modification | View only, generate reports, export data | (terminal state) |
| **CANCELLED** | Review terminated before completion | View only, audit trail preserved | (terminal state) |

#### 3.2 Review Roles and Separation of Duties

Reviews support multiple roles to enforce separation of duties, a key regulatory requirement for banking compliance workflows.

| Role | Responsibilities | Assignment Rules |
|------|-----------------|------------------|
| **Creator** | Initiates review, uploads documents, confirms extraction | Any analyst or admin |
| **Analyst** | Runs analysis, manages AI enrichment, addresses returned findings | Defaults to creator; can be reassigned |
| **Reviewer** | Dispositions findings (approve/revoke/abstain), can return or reject | One or more per review; assigned by creator or admin |
| **Approver** | Final sign-off on completed review | Must be different from creator (separation of duties enforced) |

- Multiple reviewers can be assigned to a single review, each responsible for a subset of findings
- Finding assignments are tracked per-reviewer (by check type, severity, department, or manual assignment)
- Dashboard shows per-reviewer completion status within a review
- All assigned reviewers must complete their portions before the review can advance to APPROVED

#### 3.3 Rejection and Send-Back Workflow

**Full Review Rejection (REJECTED state):**
When a reviewer determines that the review data is fundamentally inadequate (stale data, wrong framework, poor extraction quality), they can reject the entire review:
- Required: rejection reason (text, minimum 50 characters)
- Review transitions to REJECTED state
- Allowed next transitions: DOCUMENTS_UPLOADED (re-upload data) or CREATED (start over)
- Original review creator is notified
- All existing dispositions are cleared (findings reset to undispositioned)
- Audit trail records rejection with full justification

**Partial Return (RETURNED state):**
When a reviewer identifies specific findings that need rework without rejecting the entire review:
- Individual findings can be marked "NEEDS_REWORK" with comments explaining the issue
- Review transitions to RETURNED state and cannot advance to APPROVED
- Creator/analyst must address each returned finding (update notes, provide additional justification, or request re-analysis)
- Once all returned findings are addressed, the review returns to PENDING_REVIEW
- Previously completed dispositions on non-returned findings are preserved

#### 3.4 Re-Analysis Workflow

When a framework is updated, threshold values change, or data quality issues are discovered, the system supports re-analysis without losing existing disposition work.

**Re-Analysis Process:**
1. Analyst selects "Re-analyze" (with current or updated framework version)
2. System creates a snapshot of current findings and dispositions
3. System re-runs analysis with the selected framework version
4. System produces a comparison view: old findings vs. new findings
5. Dispositions from old findings carry forward where finding identifiers match (same check, same affected records)
6. New findings are undispositioned
7. Removed findings are archived with "superseded" status
8. Audit trail records the re-analysis with both framework versions and the disposition carry-forward mapping

**Comparison View:**
- Findings categorized as: **Unchanged** (same check, same results), **Modified** (same check, different severity or record count), **New** (not in previous analysis), **Removed** (in previous but not in new analysis)
- Side-by-side diff for modified findings showing what changed
- Clear indication of which dispositions were carried forward and which require new review

#### 3.5 Cancellation and Abandonment

Reviews can be cancelled from any non-terminal state. Cancellation preserves all data for audit purposes while removing the review from active workflows.

- Available from any state except CLOSED and CANCELLED
- Requires cancellation reason (text, minimum 50 characters)
- Reviews in ANALYZED state or later require admin approval to cancel (significant work has been performed)
- Cancelled reviews transition to CANCELLED state (distinct from CLOSED)
- CANCELLED is a terminal state with full audit trail preservation
- Cancelled reviews are excluded from compliance calendar calculations and SLA tracking
- Cancelled reviews remain queryable for audit purposes and appear with a "Cancelled" indicator in review lists

#### 3.6 Concurrent Review Handling

The system manages situations where multiple reviews target the same application for overlapping periods.

- When creating a review, system shall warn if the application already has an active (non-terminal) review for an overlapping period
- Warning includes a link to the existing review and a prompt to acknowledge before proceeding
- User must explicitly acknowledge the warning to create the review (not blocked, but warned)
- System shall prevent two active reviews for the same application from being in PENDING_REVIEW state simultaneously to avoid conflicting attestation work
- If both reviews complete, the later one is annotated as "supplementary"

#### 3.7 Delegation and Reassignment

Reviewers can be reassigned and individual findings can be delegated to handle reviewer unavailability and workload distribution.

- Review assignments can be changed by the review creator or an admin
- Reassignment notifies both the old and new reviewer
- In-progress dispositions by the old reviewer are preserved and attributed correctly
- Individual findings or finding groups can be delegated to specific reviewers
- Each finding tracks its assigned reviewer independently
- Delegation includes notification to the delegatee with finding context
- Audit trail records all reassignment and delegation actions with reason

#### 3.8 Attestation and Disposition

Each finding requires a disposition before the review can be completed. The three-action model ensures clear accountability.

**Disposition Actions:**

| Action | Meaning | Requirements |
|--------|---------|--------------|
| **Approve** | Access is appropriate for the user's job function | Business justification required (text); for Medium+ severity findings, structured exception documentation may be required (see FR-3.32) |
| **Revoke** | Access should be removed or modified | Remediation notes required; optional target remediation date |
| **Abstain** | Reviewer cannot make a determination | Escalation target required; triggers escalation workflow (see FR-3.28) |

**Bulk Disposition:**
Reviewers can disposition multiple findings at once to handle large finding sets efficiently:
1. Select multiple findings using checkbox selection, "select all in current filter," or "select all matching criteria"
2. Choose a disposition (Approve/Revoke/Abstain)
3. Enter a single justification that applies to all selected findings
4. System applies the disposition to all selected findings atomically
5. Audit trail records the bulk operation with a list of affected finding IDs
6. Each individual finding retains its own audit entry referencing the bulk operation ID

**Finding Grouping:**
System supports grouping findings to facilitate bulk review:
- Group by check type (e.g., all inactive account findings together)
- Group by severity level
- Group by department
- Group by assigned reviewer
- Custom filter-based grouping

#### 3.9 Escalation Workflow

When a finding is marked Abstain, a structured escalation process ensures resolution.

1. Reviewer selects Abstain and provides justification
2. Reviewer selects an escalation target (user with reviewer or admin role)
3. Escalation target receives notification with finding details and original justification
4. System starts an escalation SLA timer (configurable per framework, default 5 business days)
5. Escalation target can:
   - Re-assign to a subject matter expert
   - Disposition as Approve or Revoke with their own justification
   - Document as "Exception -- Compensating Control" (see FR-3.32)
6. If SLA expires without resolution, system auto-escalates to admin with a critical alert
7. Escalation history is tracked per finding: escalation timestamp, reason, resolution timestamp, resolver identity, resolution action, and justification

#### 3.10 Exception and Compensating Control Documentation

For findings with a disposition of Approve where the finding severity is Medium or higher, structured exception documentation captures the risk acceptance for regulatory examination purposes.

**Exception Record Structure:**
- **Exception type**: Risk Accepted, Compensating Control, Business Justification
- **Approving authority**: User with authority to accept the risk (may differ from the reviewer performing the disposition)
- **Compensating controls**: Structured description of mitigating controls in place
- **Exception expiration date**: When the exception must be re-evaluated (required)
- **Follow-up action items**: Optional, with assignee and due date per item
- **Regulatory mapping**: Which regulatory control this exception relates to

**Exception Lifecycle:**
- System tracks exception expirations and generates alerts at 30 days before expiration
- Expired exceptions are flagged on the dashboard and in compliance reports
- Exception reports include all active exceptions with compensating controls, expiration dates, and approval authority
- Exceptions carry forward to subsequent review periods for continuity tracking

#### 3.11 SLA and Time-Boxing

Configurable SLA timers ensure reviews progress through the workflow within acceptable timeframes.

**Default SLA Thresholds (configurable per framework):**

| State Transition | SLA Default | Purpose |
|-----------------|-------------|---------|
| DOCUMENTS_UPLOADED to EXTRACTED | 5 business days | Extraction is semi-automated; should be quick |
| EXTRACTED to ANALYZED | 2 business days | Analysis is fully automated |
| ANALYZED to FINDINGS_GENERATED | 3 business days | AI enrichment plus initial review |
| PENDING_REVIEW to APPROVED | 10 business days | Main reviewer disposition work |
| APPROVED to CLOSED | 5 business days | Final wrap-up and report generation |
| Overall review completion | 30 business days from creation | End-to-end deadline |

**Escalation Alerts:**
- **50% elapsed**: Warning notification to assigned reviewer/analyst
- **75% elapsed**: Warning notification to reviewer/analyst AND admin
- **100% elapsed (SLA breach)**: Critical alert to admin; review marked with "SLA Breached" indicator
- SLA breach status is visible on the dashboard, in review lists, and in compliance reports
- SLA breach does not block workflow progression but is permanently recorded

#### 3.12 Disposition Change Audit

Every disposition change creates an immutable audit record to demonstrate review integrity to examiners.

- Every disposition action (initial or change) creates a new audit entry; existing entries are never updated
- Disposition history per finding includes: previous disposition, new disposition, change reason, timestamp, and actor
- Finding detail view displays a disposition history timeline
- Compliance reports include disposition change counts per review
- Findings with changed dispositions are flagged for approver attention during final sign-off
- Bulk disposition operations create individual audit entries for each affected finding, all referencing the same bulk operation ID

#### 3.13 Review-Level Comments

A review-level comment thread supports communication between participants and documents methodology decisions.

- Any participant (creator, analyst, reviewer, approver) can add comments to the review
- Comments are timestamped and attributed to the author
- Comments are immutable (no editing or deleting after creation)
- Comments are included in the audit trail
- Comments are searchable and filterable
- Comments can be tagged for categorization (e.g., methodology, examiner-question, follow-up, data-quality)
- Comments appear in compliance reports under "Review Documentation"

#### 3.14 Concurrent Editing Prevention

Optimistic concurrency control prevents data corruption when multiple users interact with the same review.

- Review entities include a version field (incrementing integer)
- Update operations check that the version matches the expected value
- Concurrent edit conflicts return HTTP 409 Conflict with details of the conflicting change
- UI displays a notification: "This item was modified by [user] at [time]. Please refresh."
- Framework editing acquires an advisory lock: only one user can edit a framework at a time, with lock expiration after 30 minutes of inactivity

#### 3.15 Zero-Findings Scenario

When all framework checks pass and no findings are generated, the review follows a streamlined completion path.

- Review transitions to FINDINGS_GENERATED even with zero findings
- System displays a "Clean Review" summary: "All N checks passed. No findings requiring disposition."
- Review can advance to APPROVED without any disposition actions
- Compliance reports document clean reviews as positive evidence of control effectiveness
- Dashboard and trend reports track clean review count as a metric
- Audit trail records the "zero findings" result with full analysis execution details

#### 3.16 Reference Dataset Management

Reference datasets (like HR employee lists) are used across multiple reviews for cross-reference checks. They require special handling for versioning and freshness.

```yaml
reference_dataset:
  id: uuid
  name: "HR Active Employees"
  description: "Current active employee list from HRIS"
  source_system: "Paylocity"
  data_type: "hr_employees"
  freshness_threshold_days: 30  # Warn if data older than this

  template:
    format: "xlsx"
    detection:
      method: "column_presence"
      required_columns: ["Employee ID", "Name", "Status", "Department"]
    mapping:
      identifier:
        source: "Employee ID"
        transform: "lowercase"
      display_name:
        source: "Name"
      email:
        source: "Email"
        transform: "lowercase"
      employment_status:
        source: "Status"
        transform: "value_map"
        value_map:
          "Active": "active"
          "Terminated": "terminated"
          "Leave": "leave"
      department:
        source: "Department"
      termination_date:
        source: "Term Date"
        transform: "parse_date"
        date_format: "MM/DD/YYYY"
```

**Reference Dataset Version Locking:**
- When a reference dataset is attached to a review, the current version is snapshotted
- Updates to the reference dataset do not affect active reviews
- System warns if the reference dataset has been updated since the review started (e.g., "HR Employee List was updated on Feb 8. Your review is using the Feb 1 version.")
- Analyst can choose to re-analyze with updated reference data, which creates a new analysis run
- When a reference dataset is updated, system shows a delta: new records, removed records, changed records

#### 3.17 Review Requirements

- **FR-3.1**: System shall track review state and enforce valid state transitions -- no skipping states
- **FR-3.2**: System shall require human confirmation after extraction before analysis begins
- **FR-3.3**: System shall lock source documents and extraction data once analysis begins -- no modification after confirmation
- **FR-3.4**: System shall generate complete audit trail of all actions and state changes with hash-chained entries
- **FR-3.5**: System shall support multiple document uploads per review (primary application export + supplementary datasets)
- **FR-3.6**: System shall support **supplementary/reference datasets** (e.g., HR active employee list) with the following characteristics:
  - Reference datasets can be shared across reviews (upload once, use in multiple reviews)
  - Reference datasets have their own templates and extraction validation
  - Cross-reference checks specify which reference dataset to compare against
  - Reference dataset freshness is tracked (warn if data is older than configurable threshold)
- **FR-3.7**: System shall allow comparison with previous review periods showing: finding count deltas, new findings, resolved findings, recurring findings
- **FR-3.8**: System shall support review assignments and attestation workflow with three-action model: **Approve** (access is appropriate), **Revoke** (access should be removed), **Abstain** (reviewer cannot make determination, escalation required)
- **FR-3.9**: System shall enforce that all findings have a disposition (approve/revoke/abstain) before review can move to APPROVED state
- **FR-3.10**: System shall require a business justification for Approve and Abstain decisions
- **FR-3.11**: System shall display a review summary/sign-off screen before final approval showing all decisions made
- **FR-3.12**: System shall maintain a reference dataset library where datasets can be uploaded, versioned, and reused
- **FR-3.13**: When a review uses a reference dataset, the system shall record and lock the version used for that review
- **FR-3.14**: System shall warn when a reference dataset is older than its freshness_threshold_days
- **FR-3.15**: Reference datasets shall have the same extraction, validation, and human confirmation requirements as primary documents
- **FR-3.16**: System shall support a REJECTED state transition from PENDING_REVIEW with required rejection reason (minimum 50 characters), notification to the review creator, clearing of all dispositions, and full audit trail
- **FR-3.17**: System shall support a RETURNED state for partial rework where individual findings are marked NEEDS_REWORK with comments, and the review cannot advance until all returned findings are addressed
- **FR-3.18**: System shall support re-analysis with a different framework version, creating a snapshot of current findings and dispositions, running the new analysis, producing a comparison view, and carrying forward matching dispositions
- **FR-3.19**: When re-analysis produces different results, system shall categorize findings as Unchanged, Modified, New, or Removed compared to the previous analysis run
- **FR-3.20**: System shall support saving partial review progress with auto-save on each disposition, completion percentage display, and the ability for reviewers to close and return to the review workspace at any time
- **FR-3.21**: System shall support delegation of specific findings or finding groups to other reviewers, with per-finding reviewer tracking and per-reviewer progress dashboards within a review
- **FR-3.22**: System shall support cancellation of in-progress reviews from any non-terminal state, with required cancellation reason, admin approval for reviews past the ANALYZED state, and CANCELLED as a distinct terminal state
- **FR-3.23**: System shall warn when creating a review for an application that already has an active review for an overlapping period, and prevent two reviews for the same application from being in PENDING_REVIEW simultaneously
- **FR-3.24**: System shall enforce separation between review creator and final approver (cannot be the same user)
- **FR-3.25**: System shall support multiple concurrent reviewers per review with finding assignment tracking, per-reviewer completion status, and a requirement that all assigned reviewers complete their portions before the review advances
- **FR-3.26**: System shall support reviewer reassignment with notification to old and new reviewers, transfer of in-progress dispositions, and audit trail of the reassignment with reason
- **FR-3.27**: System shall support EXTRACTION_FAILED and ANALYSIS_FAILED states with error diagnostics, retry paths, and recovery to the appropriate prior state
- **FR-3.28**: When a finding is marked Abstain, system shall require an escalation target, send notification with finding details, start an escalation SLA timer, and auto-escalate to admin if the SLA expires without resolution
- **FR-3.29**: System shall track escalation history per finding: escalation timestamp, reason, resolution timestamp, resolver identity, resolution action, and justification
- **FR-3.30**: System shall support bulk disposition of findings with a single justification applied to all selected findings, atomic application, and individual audit entries per finding referencing the bulk operation
- **FR-3.31**: System shall support finding grouping by check type, severity, department, and assigned reviewer to facilitate bulk review workflows
- **FR-3.32**: System shall support structured exception documentation for findings with Approve disposition and Medium+ severity, including exception type, approving authority, compensating controls, expiration date, follow-up action items, and regulatory mapping
- **FR-3.33**: System shall track exception expirations and generate alerts when exceptions are within 30 days of expiration
- **FR-3.34**: Exception reports shall include all active exceptions with compensating controls, expiration dates, and approval authority
- **FR-3.35**: System shall enforce configurable SLA timers for review states with default thresholds and escalation alerts at 50%, 75%, and 100% of elapsed time
- **FR-3.36**: System shall generate escalation alerts when SLA thresholds are breached, with SLA breach status visible on the dashboard and in compliance reports
- **FR-3.37**: System shall maintain full disposition history for each finding where every change creates a new immutable audit entry, and findings with changed dispositions are flagged for approver attention
- **FR-3.38**: System shall handle zero-findings reviews by transitioning to FINDINGS_GENERATED, displaying a clean review summary, allowing approval without disposition actions, and tracking clean reviews as a compliance metric
- **FR-3.39**: System shall support a review-level comment thread with immutable, timestamped, attributed comments that are included in the audit trail and compliance reports
- **FR-3.40**: System shall implement optimistic concurrency control on review entities with version checking and HTTP 409 Conflict responses for concurrent edit detection
- **FR-3.41**: Reference datasets shall be version-locked to reviews at the time of attachment, with warnings when the source dataset has been updated and the option to re-analyze with the updated version

---

### 4. Document Processing (Extraction Layer)

This is the critical layer for ensuring consistency. Extraction must be deterministic, auditable, and confidence-scored.

#### 4.1 Document Processing Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DOCUMENT UPLOAD                                  │
│  • Accept file (validate type, size, integrity)                         │
│  • Calculate SHA-256 hash for integrity verification                    │
│  • Reject corrupted or oversized uploads immediately                    │
│  • Store original file with metadata                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      FORMAT DETECTION                                    │
│  • Identify file type (CSV, XLSX, XLS, JSON, XML, PDF)                  │
│  • For PDFs: detect native vs scanned (OCR path if scanned)             │
│  • Parse into intermediate tabular representation                        │
│  • For PDFs: use Camelot with accuracy scoring                          │
│  • Parser isolation: execute in subprocess to prevent crash propagation  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                        ┌───────────┴───────────┐
                        ▼                       ▼
              ┌──────────────────┐    ┌──────────────────────┐
              │  PARSE SUCCESS   │    │  PARSE FAILURE       │
              │                  │    │                      │
              │  Continue to     │    │  Display actionable  │
              │  template match  │    │  error message       │
              │                  │    │  Allow re-upload or  │
              │                  │    │  retry with options   │
              └────────┬─────────┘    └──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    TEMPLATE MATCHING                                     │
│  • Compare against application's document templates                      │
│  • Score each template on detection criteria                            │
│  • Calculate match confidence score (0.0 - 1.0)                        │
│  • Select best match if confidence >= threshold (configurable per app)  │
│  • Flag as unknown if no match meets threshold                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
        ┌───────────────────┐           ┌───────────────────┐
        │  TEMPLATE FOUND   │           │  NO TEMPLATE      │
        │  Confidence: 0.98 │           │  (or below thresh) │
        │                   │           │                   │
        │  Apply saved      │           │  AI proposes      │
        │  mapping rules    │           │  mapping as DRAFT  │
        │  deterministically│           │  Human must        │
        │                   │           │  approve & save    │
        └───────────────────┘           └───────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      TRANSFORMATION                                      │
│  • Apply field mappings per template                                     │
│  • Execute value transformations (date parsing, value maps, etc.)       │
│  • Handle missing/null values per template rules                        │
│  • Normalize to canonical schema                                         │
│  • Calculate extraction confidence score                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       VALIDATION                                         │
│  • Check required fields present                                         │
│  • Verify uniqueness constraints                                         │
│  • Validate data types and formats                                       │
│  • Flag records with issues (warnings vs errors)                        │
│  • Generate validation summary                                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│               HUMAN CONFIRMATION CHECKPOINT                              │
│                                                                          │
│  ┌─── Extraction Summary ─────────────────────────────────────────┐    │
│  │                                                                 │    │
│  │  Confidence Score: ████████████████████░░ 96%                  │    │
│  │                                                                 │    │
│  │  Document: Fedlink_Anywhere_Users.csv                          │    │
│  │  Template: Fedlink Anywhere Users Export (matched)             │    │
│  │  File Hash: a3f2b7c...                                        │    │
│  │                                                                 │    │
│  │  Total Records: 847                                             │    │
│  │  Valid Records: 842                                             │    │
│  │  Records with Warnings: 5 (click to view)                      │    │
│  │  Records with Errors: 0                                        │    │
│  │                                                                 │    │
│  │  vs. Previous Review (Q3 2025):                                │    │
│  │    Previous: 831 records                                        │    │
│  │    Change: +16 new accounts, -0 removed                        │    │
│  │                                                                 │    │
│  │  ┌─── Sample Preview (first 10 records) ──────────────────┐   │    │
│  │  │ ID      | Name          | Status | Last Login | Roles  │   │    │
│  │  │ jsmith  | John Smith    | active | 01/15/2026 | Teller │   │    │
│  │  │ mjones  | Mary Jones    | active | 02/01/2026 | Admin  │   │    │
│  │  │ ...     | ...           | ...    | ...        | ...    │   │    │
│  │  └────────────────────────────────────────────────────────┘   │    │
│  │                                                                 │    │
│  │  [ ] I confirm this extraction accurately represents the       │    │
│  │      source document data                                      │    │
│  │                                                                 │    │
│  │  [Confirm Extraction]  [Reject - Upload Different File]        │    │
│  │                                                                 │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 4.2 Document Processing Requirements

- **FR-4.1**: System shall support CSV, XLSX, XLS, JSON, XML, and PDF file formats
- **FR-4.2**: System shall automatically detect document template based on content with confidence scoring
- **FR-4.3**: When no template matches (or confidence below threshold), system shall invoke AI mapping assistant
- **FR-4.4**: AI-proposed mappings shall NOT be applied until human approves — presented as DRAFT only
- **FR-4.5**: Approved mappings shall be saved to application template for future deterministic use
- **FR-4.6**: Extraction shall be fully reproducible given same document and same template version
- **FR-4.7**: System shall store SHA-256 hash of source document for integrity verification
- **FR-4.8**: System shall require explicit human confirmation (checkbox + button) before proceeding to analysis
- **FR-4.9**: System shall show record count comparison with previous review period including new/removed accounts
- **FR-4.10**: System shall allow re-extraction if errors discovered (only before analysis begins)
- **FR-4.11**: System shall calculate and prominently display extraction confidence score
- **FR-4.12**: Extractions with confidence below 95% shall require additional human validation with field-by-field review
- **FR-4.13**: For PDF documents, system shall detect native vs scanned PDFs and route to appropriate extraction pipeline
- **FR-4.14**: PDF extraction shall use Camelot as primary parser with pdfplumber as fallback; accuracy scores from Camelot shall be included in confidence calculation
- **FR-4.15**: System shall log all extraction metadata: tool/library used, version, accuracy score, confidence score, human reviewer, timestamp
- **FR-4.16**: Phase 1 PDF support is limited to structured/tabular PDFs. Scanned PDFs display a message directing user to convert to CSV/Excel first. OCR pipeline is Phase 3+.

#### 4.3 Confidence Threshold Configuration

- **FR-4.17**: Template match confidence threshold shall be configurable per application (default: 0.95)
- **FR-4.18**: Overall extraction confidence threshold shall be configurable per application (default: 0.95)
- **FR-4.19**: When extraction confidence falls below the configured threshold, system shall require field-by-field human review with side-by-side comparison of source data and extracted values
- **FR-4.20**: Confidence threshold changes shall be audited and require admin role

#### 4.4 Extraction Failure Recovery

When extraction fails, the system must provide actionable guidance rather than generic error messages.

- **FR-4.21**: When extraction fails, system shall display specific, actionable error messages based on failure type:

| Failure Type | Error Message | Recovery Action |
|-------------|---------------|-----------------|
| File format not recognized | "Unable to parse file. Expected CSV, Excel, or PDF." | Suggest conversion to CSV; allow re-upload |
| Expected column not found | "Column 'X' expected by template but not found in document." | Suggest reviewing template mapping; allow re-upload |
| Date parsing failed | "Date parsing failed for N records. Raw values shown below." | Show affected records with raw values; allow retry with different date format |
| Parser timeout | "File processing exceeded 30-second limit." | Suggest splitting into smaller files; allow re-upload |
| Corrupt/unreadable file | "File appears corrupted or incomplete (0 records extracted)." | Prompt re-upload from source system |
| Encoding error | "File contains unrecognized character encoding." | Suggest re-saving as UTF-8; allow re-upload |

- **FR-4.22**: When extraction partially succeeds, system shall preserve partial results as DRAFT (viewable but not confirmable) alongside the error details
- **FR-4.23**: System shall allow retry with different parser settings (e.g., alternative CSV delimiter, different encoding, skip header rows)
- **FR-4.24**: System shall log full error details including stack trace to extraction_metadata JSONB for administrative debugging
- **FR-4.25**: System shall implement parser isolation (subprocess execution) so that a parser crash does not bring down the main application process

#### 4.5 Document Upload Integrity

- **FR-4.26**: System shall calculate SHA-256 hash immediately upon upload completion and reject the upload if the file is corrupt, zero bytes, or below a minimum size threshold (configurable, default 100 bytes)
- **FR-4.27**: System shall enforce a configurable maximum file size (default: 50MB per file) and reject oversized uploads with a clear message indicating the limit
- **FR-4.28**: System shall maintain an upload retry counter (maximum 3 attempts per file per session) and log each failed attempt
- **FR-4.29**: If the client provides an expected hash (e.g., from a pre-upload integrity check), system shall compare against the calculated hash and reject on mismatch

#### 4.6 Batch Upload for Large Reviews

- **FR-4.30**: System shall support uploading multiple documents in a single batch operation for reviews requiring multiple data sources (e.g., application user list + admin report + entitlement export)
- **FR-4.31**: Batch uploads shall process each file independently — a failure in one file shall not prevent processing of other files in the batch
- **FR-4.32**: System shall display batch upload progress with per-file status (pending, processing, completed, failed)

#### 4.7 Network Failure Resilience

- **FR-4.33**: Extraction shall execute as a server-side background task, independent of client connection state
- **FR-4.34**: If the client disconnects during extraction, the operation shall continue server-side and results shall be available when the client reconnects
- **FR-4.35**: System shall provide a progress polling endpoint (`GET /api/reviews/{id}/progress`) returning: `{ operation, status, progress, estimated_remaining_seconds }`

#### 4.8 AI Mapping Assistant

When no template exists, the AI Mapping Assistant helps create one:

**Input to AI:**
- Document structure (columns/fields detected with sample values)
- Target canonical schema for the review type
- Application context (name, description, role definitions)
- Sample data rows (first 5-10 rows)

**AI Output:**
- Proposed mapping for each target field with reasoning
- Confidence level for each individual field mapping (high/medium/low)
- Suggested transformations with examples
- Questions for ambiguous fields
- Overall mapping confidence score

**Critical Constraint:** The AI's proposed mapping is presented as a DRAFT for human review. The human must:
1. Review each field mapping with side-by-side source/target preview
2. Confirm or correct transformations
3. Test extraction on sample data (preview first 10 rows with proposed mapping)
4. Approve and save the template

The AI **never** directly extracts data. It only proposes configuration that, once approved, the system uses deterministically forever after.

---

### 5. Analysis Engine (Deterministic Layer)

The Analysis Engine executes framework checks against normalized data using JSON Logic. This layer is 100% deterministic — same input always produces identical output.

#### 5.1 Analysis Execution

```python
# Pseudocode for analysis execution
def execute_analysis(review, framework, extracted_data, reference_datasets):
    findings = []
    audit_log = []
    data_quality_warnings = []
    checkpoint_state = None

    # Topological sort for dependency ordering
    ordered_checks = topological_sort(framework.checks)

    for i, check in enumerate(ordered_checks):
        if not check.enabled:
            audit_log.append({
                "check_id": check.id,
                "action": "skipped",
                "reason": "disabled",
                "timestamp": utc_now()
            })
            continue

        # Resolve datasets for cross-reference checks
        if check.condition.type == "cross_reference":
            primary_data = get_dataset(check.condition.primary_dataset, extracted_data)
            secondary_data = get_dataset(check.condition.secondary_dataset, reference_datasets)
            audit_log.append({
                "check_id": check.id,
                "action": "cross_reference_resolve",
                "primary_count": len(primary_data),
                "secondary_count": len(secondary_data)
            })
            # Warn if secondary dataset is empty
            if len(secondary_data) == 0:
                data_quality_warnings.append({
                    "check_id": check.id,
                    "type": "empty_reference_dataset",
                    "message": f"Reference dataset '{check.condition.secondary_dataset}' has 0 records"
                })

        # Apply filter first
        filtered_data = apply_filter(extracted_data, check.filter)
        audit_log.append({
            "check_id": check.id,
            "action": "filter_applied",
            "total_records": len(extracted_data),
            "filtered_records": len(filtered_data)
        })

        # Handle data quality issues gracefully
        clean_data, quality_issues = validate_data_for_check(filtered_data, check)
        if quality_issues:
            data_quality_warnings.extend(quality_issues)
            audit_log.append({
                "check_id": check.id,
                "action": "data_quality_exclusions",
                "excluded_count": len(quality_issues)
            })

        # Execute condition using JSON Logic evaluator
        matching_records = execute_condition(clean_data, check.condition)
        audit_log.append({
            "check_id": check.id,
            "action": "condition_evaluated",
            "matching_records": len(matching_records)
        })

        if matching_records:
            # Determine severity per framework rules (NOT AI)
            severity = evaluate_severity_rules(check.severity_rules, matching_records)

            # Generate plain-English explainability
            explanation = render_template(check.explainability_template, {
                "record_count": len(matching_records),
                "total_filtered": len(filtered_data),
                "settings": framework.settings
            })

            finding = Finding(
                check_id=check.id,
                check_name=check.name,
                severity=severity,               # From framework rules, NEVER AI
                record_count=len(matching_records),  # Exact count from code
                records=extract_output_fields(matching_records, check.output_fields),
                explainability=explanation,        # Template-driven, deterministic
                output_fields=check.output_fields
            )
            findings.append(finding)
        else:
            # Zero matches is a valid result, not an error
            audit_log.append({
                "check_id": check.id,
                "action": "clean_result",
                "message": "Check produced zero findings"
            })

        # Checkpoint progress for long-running analyses
        if i % checkpoint_interval == 0:
            checkpoint_state = save_checkpoint(review.id, i, findings, audit_log)

    # Calculate analysis checksum for integrity verification
    analysis_checksum = sha256(serialize(findings) + serialize(audit_log))

    return findings, audit_log, data_quality_warnings, analysis_checksum
```

#### 5.2 Analysis Requirements

- **FR-5.1**: Analysis shall execute all enabled checks in dependency-aware order (topological sort)
- **FR-5.2**: Each check execution shall be logged with record counts at each stage (pre-filter, post-filter, matching)
- **FR-5.3**: Severity shall be assigned per framework severity_rules definitions, NEVER by AI judgment
- **FR-5.4**: Analysis shall be re-runnable with identical results given same input data and framework version — 100% reproducibility guaranteed
- **FR-5.5**: System shall record framework version (semantic version + ID) used for each analysis
- **FR-5.6**: System shall support "dry run" mode to preview analysis without saving results
- **FR-5.7**: Cross-reference checks shall clearly indicate which datasets were compared, their record counts, and the match criteria used
- **FR-5.8**: System shall calculate and store SHA-256 analysis checksum for integrity verification
- **FR-5.9**: Each finding shall include a deterministic explainability statement generated from the check's explainability_template
- **FR-5.10**: System shall log the complete rule execution audit trail: rule_id, rule_version, input_data_hash, output_finding_hash, execution_timestamp, record counts at each stage

#### 5.3 Data Quality Handling

The analysis engine must handle imperfect data gracefully rather than failing on unexpected values.

- **FR-5.11**: Analysis engine shall handle data quality issues without aborting:
  - **Null/missing values**: Record is excluded from the specific check, logged as "data quality warning" with record identifier
  - **Type mismatches** (string where number expected): Record is excluded from the check, logged as "type mismatch warning" with field name and raw value
  - **Zero records in cross-reference dataset**: Check produces a warning-level finding (not an error), noting that the reference dataset was empty
  - **Check with zero results**: Logged as "clean" in audit trail — this is a valid outcome, not an error
- **FR-5.12**: Analysis shall produce a **data quality report** alongside findings, containing:
  - Records excluded from analysis and the reason for exclusion
  - Fields with high null/missing rates (threshold: >10% null)
  - Type conversion warnings with affected record identifiers
  - Dataset size mismatches (e.g., HR list has 100 records, application has 500 users) flagged as informational
- **FR-5.13**: Data quality warnings shall be prominently displayed in the review workspace and included in compliance reports

#### 5.4 Zero Findings Scenario (Clean Review)

- **FR-5.14**: When analysis produces zero findings, the review shall still transition to FINDINGS_GENERATED
- **FR-5.15**: System shall display a "Clean Review" summary: "All N checks passed across M records. No findings requiring disposition."
- **FR-5.16**: Clean reviews shall be approvable without any disposition actions (there are no findings to disposition)
- **FR-5.17**: Compliance reports shall document clean reviews as positive evidence of control effectiveness
- **FR-5.18**: Dashboard and trend reports shall track clean review count as a metric alongside finding counts

#### 5.5 Large Review Handling (10,000+ Records)

- **FR-5.19**: For datasets exceeding 10,000 records, analysis shall process data in streaming batches (configurable batch size, default 5,000 records) to manage memory consumption
- **FR-5.20**: Analysis shall report progress as a percentage and display a progress indicator in the UI with estimated time remaining
- **FR-5.21**: When a single check matches more than 500 records, system shall:
  - Generate an aggregated summary (counts grouped by key dimensions such as department, role, status)
  - Display a representative sample (first 50 records) with "load more" pagination
  - Support bulk disposition at the finding level, not the individual record level
- **FR-5.22**: Findings with more than 100 affected records shall render in a summary view by default with a "Show all records" expandable section using lazy-loading

#### 5.6 Reference Dataset Version Locking

- **FR-5.23**: When a reference dataset is attached to a review, the current version shall be snapshotted and locked to that review — subsequent updates to the reference dataset do not affect active reviews
- **FR-5.24**: System shall warn if a reference dataset has been updated since the review was created: "HR Employee List was updated on [date]. Your review is using the [original date] version."
- **FR-5.25**: Analyst may choose to re-analyze with the updated reference dataset, which creates a new analysis run and preserves the prior run for comparison
- **FR-5.26**: Audit trail shall record which reference dataset version (ID + upload timestamp + record count) was used for each analysis run

#### 5.7 Analysis Checkpointing

- **FR-5.27**: For analyses expected to exceed 30 seconds (based on record count and check count heuristics), system shall save checkpoint state at configurable intervals (default: every 10 checks)
- **FR-5.28**: If analysis is interrupted (server restart, task timeout), system shall be able to resume from the last checkpoint rather than restarting from the beginning
- **FR-5.29**: Checkpoint data shall include: completed check IDs, accumulated findings, partial audit log, and progress percentage
- **FR-5.30**: Resumed analysis shall produce identical results to an uninterrupted run — checkpointing does not affect determinism

#### 5.8 Supported Condition Types

| Condition Type | Description | Example Use | JSON Logic Operator |
|----------------|-------------|-------------|-------------------|
| date_comparison | Compare date field to threshold | Last login > 90 days ago | Custom: days_since |
| value_equals | Exact value match | Status = "Active" | `{"==": [...]}` |
| value_not_equals | Negated value match | Status != "Disabled" | `{"!=": [...]}` |
| value_in_list | Value in set of values | Department in ["IT", "Security"] | `{"in": [...]}` |
| value_matches_pattern | Regex or wildcard match | Username matches "svc_*" | Custom: pattern_match |
| field_is_null | Field is missing or empty | Manager field is blank | `{"!": {"var": ...}}` |
| field_is_not_null | Field has value | Termination date is set | `{"!!": {"var": ...}}` |
| numeric_comparison | Compare numeric values | Login count < 5 | `{"<": [...]}` |
| numeric_between | Value in numeric range | Limit between 500K and 1M | `{"and": [{">=":...}, {"<=":...}]}` |
| role_combination | Check for role pairs | Has both "Initiator" and "Approver" | Custom: role_pair_check |
| role_match | Check for role presence | Any role matching "*Admin*" | Custom: role_pattern |
| cross_reference | Compare across datasets | User in App but not in HR Active | Custom: cross_ref |
| **compound** | **Boolean combination of conditions** | **Status=active AND last_login > 90 days** | `{"and": [...]}` / `{"or": [...]}` / `{"!": {...}}` |

#### 5.9 JSON Logic Custom Operators

SAPv2 extends standard JSON Logic with domain-specific operators:

```python
# Custom operators registered with JSON Logic engine
custom_operators = {
    "days_since": lambda date_val: (utc_now() - parse_date(date_val)).days,
    "older_than_days": lambda field_val, threshold: days_since(field_val) > threshold,
    "pattern_match": lambda value, pattern: fnmatch(value, pattern),
    "role_pair_check": lambda roles, prohibited_pairs: check_prohibited_pairs(roles, prohibited_pairs),
    "role_pattern": lambda roles, patterns: any(fnmatch(r, p) for r in roles for p in patterns),
    "cross_ref": lambda primary, secondary, match_field: set_difference(primary, secondary, match_field)
}
```

---

### 6. AI Enrichment Layer

After deterministic analysis is complete, AI adds value without changing outcomes. All AI output is labeled, confidence-scored, and human-reviewable.

> **Core Principle — AI Never Counts, AI Never Decides:** The deterministic analysis engine produces all findings, record counts, and severity levels. AI enrichment operates strictly downstream: it generates human-readable descriptions, suggests remediation steps, and identifies patterns. AI output never modifies, overrides, or replaces deterministic results. If the AI layer is entirely disabled, the platform remains fully functional for compliance reviews — AI enrichment is additive, never load-bearing.

#### 6.1 LLM-Agnostic Provider Abstraction

The AI enrichment layer is **provider-agnostic** and supports any LLM backend through a unified abstraction. No single vendor is hardcoded; the platform works with any combination of providers.

**Supported Providers:**

| Provider | Implementation | Structured Output | Compliance |
|----------|---------------|-------------------|------------|
| **OpenAI** (direct API) | OpenAI SDK (`AsyncOpenAI`) | Native `response_format` | SOC 2 Type II; BAA via Enterprise plan |
| **Azure OpenAI** | OpenAI SDK (`AsyncAzureOpenAI`) | Native `response_format` | SOC 2 Type II, BAA, configurable data residency |
| **Anthropic Claude** | Anthropic SDK (`AsyncAnthropic`) | `tool_use` pattern | SOC 2 Type II; BAA via commercial agreement |
| **Google Gemini** | Google GenAI SDK | Native `response_schema` | SOC 2 Type II; BAA via Vertex AI enterprise |
| **AWS Bedrock** | Boto3 Bedrock Runtime | Model-dependent (Converse API) | SOC 2 Type II, BAA, data stays in VPC |
| **Ollama** (local) | OpenAI-compatible API | JSON mode + prompt-based schema | N/A — data never leaves premises |
| **OpenAI-Compatible** | OpenAI SDK with custom `base_url` | Varies by implementation | Varies by hosting provider |
| **Mock** (testing) | In-memory, deterministic responses | Native | N/A — no external calls |

**Provider Interface Contract:**

All providers implement the `AIProviderBase` abstract class with two core methods:

```python
class AIProviderBase(abc.ABC):
    """Abstract base class for all AI providers."""

    @abc.abstractmethod
    async def complete(
        self,
        messages: List[ChatMessage],
        *,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        response_schema: Optional[Type[BaseModel]] = None,
        timeout_seconds: int = 60,
    ) -> AIInvocationResult:
        """Send a completion request. Returns structured result with
        content, parsed output, token counts, duration, and cost."""
        ...

    async def stream(
        self,
        messages: List[ChatMessage],
        **kwargs,
    ) -> AsyncIterator[str]:
        """Optional streaming interface. Providers that don't support
        streaming raise NotImplementedError; system falls back to
        non-streaming."""
        ...
```

Every invocation returns an `AIInvocationResult` containing: raw content, optional parsed Pydantic model, model name, provider name, input/output token counts, duration, confidence score, and estimated cost in USD.

#### 6.2 Per-Function Model Routing

Each AI function can be independently routed to a different provider and model, allowing cost optimization and capability matching:

| AI Function | Purpose | Recommended Model Class | Temperature | Max Tokens | Rationale |
|-------------|---------|------------------------|-------------|------------|-----------|
| `field_mapping` | Propose column-to-schema mappings | Strong reasoning (Claude Sonnet, GPT-4o) | 0.1 | 4096 | Requires accurate schema understanding and transformation logic |
| `finding_description` | Generate human-readable finding text | General purpose | 0.2 | 2048 | Factual description grounded in deterministic data |
| `remediation` | Suggest specific remediation steps | General purpose | 0.3 | 2048 | Actionable suggestions with some creative latitude |
| `executive_summary` | Generate management-level overview | General purpose | 0.4 | 4096 | Natural language requiring slightly more creative expression |
| `pattern_detection` | Identify patterns across findings | Strong reasoning | 0.2 | 4096 | Cross-finding analysis requires strong analytical reasoning |

Configuration is managed through environment variables (simple single-provider setup) or a YAML configuration file (advanced multi-provider routing with fallback chains). See Section 11 for configuration details.

#### 6.3 Fallback Chain Support

Each AI function can define an ordered list of fallback providers. If the primary provider fails (timeout, rate limit, API error), the system automatically tries the next provider in the chain.

```
Example fallback chain for finding_description:
  1. Anthropic Claude (primary) → success → return result
  2. If fails → log failure → try Azure OpenAI (fallback 1)
  3. If fails → log failure → try OpenAI direct (fallback 2)
  4. If all fail → mark enrichment as failed, continue without AI content
```

- All attempts (including failures) are logged to the `ai_invocations` table with `is_fallback` and `fallback_from` fields
- Fallback attempts use the same prompt and parameters as the primary attempt
- The system never blocks a review due to AI provider failures — enrichment is best-effort

#### 6.4 AI Enrichment Functions

**6.4.1 Finding Descriptions**

For each finding, AI generates a human-readable description:

**Input (structured, not raw documents):**
- Finding data (check name, severity, record count, sample records — max 10)
- Application context (name, description, criticality, data classification)
- Framework remediation guidance text

**Output:**
- 2-3 sentence description of the finding
- Why this matters for this specific application
- Confidence score (0.0 - 1.0)

**Example Output:**
> "This review identified 23 user accounts in Jack Henry Silverlake that have not logged in for over 90 days but remain in active status. Given that this is the core banking system containing sensitive customer financial data subject to GLBA, dormant accounts represent an elevated risk of unauthorized access if credentials were compromised."
>
> *[AI-Generated | Confidence: 0.94 | Provider: anthropic | Model: claude-sonnet-4-5-20250929 | Generated: 2026-02-05T14:30:00Z]*

**6.4.2 Remediation Recommendations**

For each finding, AI suggests specific remediation steps:

**Input:**
- Finding data (severity, records, check remediation_guidance)
- Application context and role definitions
- Previous review remediation actions (if available)

**Output:**
- Specific, actionable remediation steps
- Suggested timeline based on severity
- Responsible party suggestions
- Confidence score

**6.4.3 Executive Summary**

AI generates review summary for management:

**Input:**
- All findings with counts and severities
- Application context
- Comparison to previous review (if available)
- Framework description and regulatory mappings

**Output:**
- Executive summary paragraph (3-5 sentences)
- Key statistics table
- Trend analysis vs. prior period
- Top priority items (ranked by severity)
- Confidence score

**6.4.4 Pattern Detection**

AI identifies patterns across findings:

**Input:**
- All findings with full record details
- Application role definitions

**Output:**
- Observations (e.g., "7 of the 12 inactive accounts are in the Marathon branch")
- Suggested root cause hypotheses
- Related findings that may have common cause
- Confidence score per observation

#### 6.5 AI Enrichment Requirements

- **FR-6.1**: AI enrichment shall occur ONLY AFTER deterministic analysis is complete and findings are locked
- **FR-6.2**: AI-generated content shall be clearly labeled with:
  - "AI-Generated" badge/label
  - Confidence score
  - Provider name and model name/version
  - Generation timestamp
  - "Pending Review" status until human approval
- **FR-6.3**: AI enrichment shall NEVER modify finding counts, severities, or categorizations
- **FR-6.4**: All AI-generated content shall be editable by reviewers
- **FR-6.5**: System shall allow regeneration of AI content without affecting underlying deterministic data
- **FR-6.6**: AI enrichment shall be optional and can be disabled per review or globally
- **FR-6.7**: System shall log all AI model invocations with: provider name, model name/version, AI function type, input hash (not full content for PII protection), output hash, confidence score, temperature used, timestamp, duration, input and output token counts, estimated cost in USD, and fallback indicator (whether this was a fallback attempt and which provider failed)
- **FR-6.8**: AI is PROHIBITED from: counting records, assigning severity levels, making compliance determinations, generating compliance documentation without human review
- **FR-6.9**: AI enrichment shall use RAG grounding from only: linked regulatory documents, approved internal policies, framework documentation, and application context
- **FR-6.10**: AI-generated content with confidence below 0.7 shall be flagged for mandatory human review before display

#### 6.6 Cost Tracking and Token Accounting

- **FR-6.11**: System shall track estimated cost per AI invocation based on a configurable token pricing table (cost per 1M input tokens and per 1M output tokens, by provider and model)
- **FR-6.12**: System shall aggregate cost data by provider, model, AI function, review, and time period
- **FR-6.13**: Admin dashboard shall display AI usage metrics: total invocations, total cost, average latency, error rate, cost by provider, invocations by function type, and fallback event history
- **FR-6.14**: System shall support configurable cost alerts (e.g., notify admin when monthly AI spend exceeds threshold)
- **FR-6.15**: Cost tracking data shall be exportable in CSV and JSON formats for financial reporting

#### 6.7 Data Classification Enforcement

- **FR-6.16**: System shall enforce provider restrictions based on a configurable data classification level:

| Classification | Allowed Providers | Use Case |
|---------------|-------------------|----------|
| `public` | Any provider | Non-sensitive test data |
| `internal` | SOC 2 certified providers only | Internal operational data |
| `confidential` | BAA-capable providers only (Azure OpenAI, Bedrock, Anthropic, Vertex AI) | Customer PII, financial records |
| `restricted` | On-premises only (Ollama, self-hosted) | Highly sensitive / air-gapped environments |

- **FR-6.17**: System shall validate at startup that all configured providers are authorized for the institution's data classification level and refuse to initialize AI services if misconfigured
- **FR-6.18**: Local model deployments (Ollama) shall always be permitted regardless of classification level, as data never leaves the institution's network

#### 6.8 Structured Output Abstraction

Different providers handle structured output differently. The abstraction layer handles this transparently:

| Provider | Strategy | Notes |
|----------|----------|-------|
| OpenAI / Azure OpenAI | Native `response_format` with Pydantic model | Most mature; supports complex nested schemas |
| Anthropic | `tool_use` pattern with JSON Schema | Reliable; schema wrapped as tool definition |
| Google Gemini | Native `response_schema` parameter | Supports Pydantic schemas via google-genai SDK |
| AWS Bedrock | Model-dependent (Converse API) | Anthropic models via Bedrock support tool_use |
| Ollama | JSON mode + schema in prompt | Validate output and retry on parse failure (max 2 retries) |
| OpenAI-Compatible | Check for `response_format` support; fall back to prompt-based | Quality varies by implementation |

For providers without native structured output, the system embeds the JSON schema in the system prompt, validates the response against the Pydantic model, and retries (up to 2 times) on parse failure.

#### 6.9 AI Failure Recovery

- **FR-6.19**: If the AI service is unavailable, enrichment shall be skipped entirely — the review proceeds without AI content and the user is notified with a "Retry enrichment" option available at any time
- **FR-6.20**: If rate-limited, the system shall implement exponential backoff with jitter (base: 1s, max: 30s, max attempts: 3) using the `tenacity` library
- **FR-6.21**: If individual finding enrichment fails while others succeed, the failed finding shall be marked as "enrichment failed" with the error reason; successfully enriched findings retain their content; per-finding retry shall be available
- **FR-6.22**: If token limits are exceeded for large finding sets, the system shall reduce input context (fewer sample records, truncated application context) and retry, flagging the result as "reduced context enrichment"
- **FR-6.23**: A review shall NEVER be blocked by AI enrichment failure. Enrichment is best-effort; all deterministic data remains intact and fully usable regardless of enrichment status. The review can be approved and closed with zero AI enrichment.

#### 6.10 AI Consistency Techniques

1. **Structured Prompts**: AI receives highly structured JSON input, never raw documents
2. **Low Temperature**: Use temperature 0.1-0.3 for factual descriptions, 0.5 max for summaries
3. **Output Constraints**: Request structured JSON output with defined fields and length limits via provider-appropriate mechanism (native structured output or schema-in-prompt fallback)
4. **Context Anchoring**: Always provide deterministic facts (counts, severities) first in prompt so AI cannot contradict them
5. **Regeneration Option**: User can regenerate any AI content; new output replaces old with full version history
6. **Confidence Scoring**: Every AI output includes a self-assessed confidence score
7. **Grounding Sources**: AI must cite which framework guidance or application context informed its output
8. **Provider Transparency**: All AI-generated content displays the provider and model used, enabling users to understand and compare output quality across providers

#### 6.11 AI Provider Administration

- **FR-6.24**: Administrator shall be able to configure AI providers through the admin settings interface, including: selecting provider type, entering connection credentials, choosing default model, and testing connectivity
- **FR-6.25**: Connection test shall verify: basic connectivity (latency), structured output capability, model availability, and compliance authorization for the configured data classification level
- **FR-6.26**: System shall support per-function model routing configuration through the admin UI, allowing different AI tasks to use different providers/models optimized for that task
- **FR-6.27**: System shall implement automatic fallback chains configurable per function, so that if a primary provider fails, secondary providers are tried transparently
- **FR-6.28**: System shall support two configuration modes: simple (single provider via environment variables) and advanced (multi-provider routing via YAML configuration file with environment variable interpolation for secrets)

---

### 7. Reporting

#### 7.1 Report Types

**7.1.1 Review Report**
Complete documentation of a single review for examiner consumption:
- Review metadata (date, scope, reviewer, application, framework version)
- Methodology documentation (framework rules used, in plain English)
- Findings summary by severity with counts
- Detailed findings with affected records and explainability statements
- AI-generated descriptions and recommendations (clearly labeled as AI-generated)
- Attestation signatures with timestamps
- Audit trail excerpt (key actions and state changes)
- Data integrity verification (document hash, extraction checksum, analysis checksum)

**7.1.2 Trend Report**
Comparison across multiple review periods:
- Finding counts over time (line chart data)
- New vs. recurring vs. resolved findings
- Remediation effectiveness (time to remediate by severity)
- Risk trend analysis with directional indicators
- Record count changes over time
- Clean review frequency tracking
- Framework version annotations (which version was used per period)

**7.1.3 Compliance Report**
Designed specifically for regulatory examination:
- Methodology documentation with regulatory control mappings
- Framework version, rules, and severity definitions
- Data sources with integrity verification (hashes)
- Extraction validation details with confidence scores
- Evidence of review and attestation
- Audit trail with hash chain verification status
- Examiner-friendly formatting

**7.1.4 Exception Report**
Findings pending remediation:
- Open findings by age and severity
- Overdue remediations with escalation status
- Exception requests and approvals
- Compensating controls documentation
- SLA compliance metrics

**7.1.5 Application Risk Summary**
Per-application risk posture:
- Current finding counts by severity
- Historical trend with framework version annotations
- Last review date and next scheduled
- Overdue items
- Clean review history

**7.1.6 Examination Evidence Package**
One-click bundle of everything an examiner needs, assembled into a single organized deliverable:

```
Evidence Package Contents:
├── 00_table_of_contents.pdf
├── 01_methodology/
│   ├── framework_definition.pdf          — Framework version, checks in plain English
│   └── regulatory_control_mappings.pdf   — FFIEC, NIST CSF mappings
├── 02_review_summary/
│   ├── executive_summary.pdf             — AI-generated (labeled) + human-approved
│   ├── findings_by_severity.pdf          — Complete finding list with dispositions
│   └── data_quality_report.pdf           — Extraction confidence, validation details
├── 03_evidence/
│   ├── source_document_hashes.pdf        — SHA-256 hashes for all source documents
│   ├── extraction_validation.pdf         — Confidence scores, human confirmation records
│   ├── analysis_checksum.pdf             — Deterministic analysis integrity proof
│   └── attestation_records.pdf           — All signatures and timestamps
├── 04_audit_trail/
│   ├── review_audit_trail.pdf            — Complete action log with hash chain status
│   ├── disposition_history.pdf           — All disposition decisions with justifications
│   └── ai_enrichment_log.pdf            — What was AI-generated vs. human-written
├── 05_trend_analysis/
│   └── prior_period_comparison.pdf       — Findings trend vs. prior review periods
├── raw_data/
│   ├── findings.json                     — Machine-readable finding data
│   ├── audit_trail.json                  — Machine-readable audit log
│   └── analysis_metadata.json            — Framework version, check definitions, checksums
└── manifest.json                         — Package metadata, generation timestamp, integrity hash
```

- **FR-7.11**: System shall generate an Examination Evidence Package as a ZIP archive containing organized PDF reports and raw JSON data files
- **FR-7.12**: Evidence package naming convention: `{BankName}_{ApplicationName}_{ReviewPeriod}_{GeneratedDate}.zip`
- **FR-7.13**: Evidence package generation shall be available for individual reviews or for all reviews within a date range (batch generation)
- **FR-7.14**: Evidence package shall include a manifest with SHA-256 integrity hash of the package contents

#### 7.2 Examiner Access Mode

- **FR-7.15**: System shall support an "Examiner" user role with read-only access to all reviews, findings, frameworks, and audit logs
- **FR-7.16**: Examiner role capabilities:
  - View all reviews, findings, dispositions, and audit trails
  - Verify hash chain integrity through the UI
  - Export any data in PDF, JSON, or CSV format
  - Generate evidence packages for any review
  - No ability to create, modify, or delete any records
- **FR-7.17**: Examiner access shall be provisioned by admin with:
  - Optional scope restriction (specific applications, date ranges)
  - Configurable expiration (default: 90 days)
  - Full audit trail of all examiner activity (every data access logged)
  - Notification to bank admin of all examiner login sessions
- **FR-7.18**: Examiner accounts shall not count against regular user license limits
- **FR-7.19**: Examiner session logging shall capture enhanced detail including all records and reports accessed

#### 7.3 Report Archival and Versioning

- **FR-7.20**: Generated reports shall be versioned — regenerating a report creates a new version while preserving previous versions
- **FR-7.21**: Report version history shall be viewable with generation timestamp, generator identity, and reason for regeneration
- **FR-7.22**: Reports associated with closed reviews shall be archived and retained for the full data retention period (minimum 7 years)
- **FR-7.23**: Archived reports shall remain retrievable and viewable without reprocessing the underlying review data
- **FR-7.24**: System shall track which report version was provided to examiners, if applicable

#### 7.4 Trend Analysis Across Review Periods

- **FR-7.25**: System shall support cross-period trend analysis for any application with two or more completed reviews
- **FR-7.26**: Trend analysis shall include:
  - Finding count trajectory by severity over time
  - New findings (not present in prior period), recurring findings (present in both), and resolved findings (present in prior but not current)
  - Average time to remediate by severity category
  - Clean review frequency and streaks
  - Record count growth trajectory (total accounts over time)
- **FR-7.27**: Trend reports shall annotate framework version changes between periods and highlight findings attributable to rule changes vs. actual data changes
- **FR-7.28**: Trend data shall be available via API for integration with external dashboards and board reporting tools

#### 7.5 Reporting Requirements

- **FR-7.1**: System shall generate PDF reports with consistent, professional formatting
- **FR-7.2**: Reports shall include framework version and check definitions used (in plain English)
- **FR-7.3**: Reports shall include extraction validation details with confidence scores
- **FR-7.4**: Reports shall include audit trail of review workflow with hash verification status
- **FR-7.5**: System shall support custom report templates
- **FR-7.6**: Reports shall clearly distinguish deterministic findings from AI-generated commentary using visual indicators (e.g., sidebar color coding, "AI-Generated" badges)
- **FR-7.7**: Compliance reports shall include regulatory control mappings (FFIEC, NIST CSF)
- **FR-7.8**: System shall support scheduled report generation (e.g., monthly compliance summary)
- **FR-7.9**: Reports shall be exportable in PDF and JSON formats
- **FR-7.10**: Examiner export capability shall produce audit trail report with: all review decisions, timestamps, reviewers, business justifications, and hash chain verification status

---
### 8. Data Model

#### 8.1 Design Principles -- Hybrid Schema

Based on performance research, SAPv2 uses a **hybrid data model**: normalized relational columns for frequently-queried fields, JSONB reserved for truly variable data.

**Why Hybrid:** PostgreSQL JSONB values over 2KB trigger TOAST storage with severe performance implications (10x+ slower queries). Query planner cannot estimate selectivity for JSONB fields, causing catastrophic plan choices. Normalized columns with proper indexes solve this.

**Rules:**
- Fields that are filtered, sorted, or joined: **normalized columns**
- Fields that are variable per application/framework: **JSONB**
- Extracted records: **separate normalized table** (not a JSONB blob on extractions)

**Soft Delete Policy:**

All entities SHALL support soft deletion via `is_active BOOLEAN DEFAULT TRUE`. Hard deletion via SQL DELETE is prohibited for all tables except session/token tables (ephemeral data) and temporary upload staging. Database roles SHALL NOT have DELETE permission on core tables. API DELETE endpoints perform soft delete (`UPDATE is_active = FALSE`). Soft-deleted records are excluded from list queries by default but remain accessible for audit trail reconstruction and regulatory examination.

**Migration Strategy:**

- All schema changes SHALL be forward-compatible (additive) where possible
- Destructive changes (column removal, type change) SHALL use a two-phase approach:
  1. Add new column, backfill, update application code
  2. Remove old column in subsequent release
- Each migration SHALL have a corresponding rollback migration
- Migrations SHALL be tested against a copy of production data before deployment
- Audit log table migrations SHALL be non-blocking (no exclusive locks)
- Partition management (creating new monthly partitions) SHALL be automated

#### 8.2 Core Entity Relationship

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│    FRAMEWORK    │       │   APPLICATION   │       │     REVIEW      │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id              │       │ id              │       │ id              │
│ name            │       │ name            │       │ name            │
│ review_type     │◀──────│ review_type     │──────▶│ application_id  │
│ version         │       │ criticality     │       │ framework_id    │
│ checks (JSONB)  │       │ context         │       │ framework_ver   │
│ settings (JSONB)│       │ templates[]     │       │ period_start    │
│ regulatory_map  │       │ role_defs (JSON)│       │ period_end      │
│ effective_date  │       │ review_schedule │       │ status          │
│ created_at      │       │ created_at      │       │ assigned_to     │
│ is_immutable    │       │ updated_at      │       │ due_date        │
└─────────────────┘       └─────────────────┘       │ notes           │
                                                    │ ai_summary      │
                                                    │ created_by      │
                          ┌─────────────────────────│ created_at      │
                          │                         └─────────────────┘
                          │                                  │
                          │    ┌──────────────────────────────┼──────────────┐
                          │    │                              │              │
                          ▼    ▼                              ▼              ▼
               ┌─────────────────┐               ┌──────────────────┐  ┌─────────────────┐
               │    DOCUMENT     │               │ EXTRACTED_RECORD │  │    FINDING      │
               ├─────────────────┤               ├──────────────────┤  ├─────────────────┤
               │ id              │               │ id               │  │ id              │
               │ review_id       │               │ extraction_id    │  │ review_id       │
               │ filename        │               │ record_type      │  │ check_id        │
               │ file_hash       │               │ identifier       │  │ check_name      │
               │ file_size       │               │ display_name     │  │ severity        │
               │ template_id     │               │ status           │  │ record_count    │
               │ confidence_score│               │ last_activity    │  │ description     │
               │ uploaded_by     │               │ roles (JSONB)    │  │ remediation     │
               │ uploaded_at     │               │ department       │  │ explainability  │
               └─────────────────┘               │ account_type     │  │ ai_generated    │
                                                 │ data (JSONB)     │  │ ai_confidence   │
                        ┌─────────────────┐      │ extended (JSONB) │  │ disposition     │
                        │   EXTRACTION    │      │ validation_status│  │ disposition_by  │
                        ├─────────────────┤      │ created_at       │  │ disposition_note│
                        │ id              │      └──────────────────┘  │ status          │
                        │ review_id       │                            │ created_at      │
                        │ document_id     │      ┌─────────────────┐   └─────────────────┘
                        │ template_id     │      │ REFERENCE_DATA  │
                        │ record_count    │      ├─────────────────┤
                        │ valid_count     │      │ id              │
                        │ warning_count   │      │ name            │
                        │ confidence_score│      │ data_type       │
                        │ confirmed_by    │      │ source_system   │
                        │ confirmed_at    │      │ freshness_days  │
                        │ checksum        │      │ uploaded_at     │
                        │ warnings (JSONB)│      │ file_hash       │
                        │ created_at      │      │ record_count    │
                        └─────────────────┘      └─────────────────┘

               ┌─────────────────┐    ┌─────────────────┐    ┌──────────────────┐
               │   AUDIT_LOG     │    │   AI_USAGE_LOG  │    │  REVIEW_COMMENT  │
               ├─────────────────┤    ├─────────────────┤    ├──────────────────┤
               │ id (BIGSERIAL)  │    │ id              │    │ id               │
               │ timestamp       │    │ review_id       │    │ review_id        │
               │ actor_id        │    │ model_name      │    │ finding_id       │
               │ actor_type      │    │ function_type   │    │ author_id        │
               │ session_id      │    │ tokens_input    │    │ body             │
               │ action          │    │ tokens_output   │    │ created_at       │
               │ entity_type     │    │ cost_estimate   │    └──────────────────┘
               │ entity_id       │    │ duration_ms     │
               │ before_state    │    │ success         │    ┌──────────────────┐
               │ after_state     │    │ created_at      │    │ NOTIFICATION_    │
               │ content_hash    │    └─────────────────┘    │ PREFERENCES      │
               │ previous_hash   │                           ├──────────────────┤
               └─────────────────┘    ┌─────────────────┐    │ id               │
                                      │    INVITES      │    │ user_id          │
                                      ├─────────────────┤    │ channel          │
                                      │ id              │    │ event_type       │
                                      │ code            │    │ enabled          │
                                      │ email           │    │ created_at       │
                                      │ role            │    └──────────────────┘
                                      │ created_by      │
                                      │ used_by         │
                                      │ expires_at      │
                                      │ is_active       │
                                      └─────────────────┘
```

#### 8.3 Canonical Schemas

**User Access Review Schema:**
```json
{
  "type": "user_access",
  "fields": {
    "identifier": { "type": "string", "required": true, "indexed": true },
    "display_name": { "type": "string", "required": false },
    "email": { "type": "string", "required": false, "indexed": true },
    "status": { "type": "enum", "values": ["active", "inactive", "disabled", "locked", "terminated"], "required": true, "indexed": true },
    "last_activity": { "type": "datetime", "required": false, "indexed": true },
    "created_date": { "type": "datetime", "required": false },
    "roles": { "type": "array", "items": "string", "required": false },
    "department": { "type": "string", "required": false, "indexed": true },
    "manager": { "type": "string", "required": false },
    "account_type": { "type": "enum", "values": ["human", "service", "system", "shared"], "required": false, "default": "human", "indexed": true },
    "extended_attributes": { "type": "object", "required": false }
  }
}
```

**Firewall Rule Review Schema:**
```json
{
  "type": "firewall_rule",
  "fields": {
    "rule_id": { "type": "string", "required": true, "indexed": true },
    "rule_name": { "type": "string", "required": false },
    "sequence": { "type": "integer", "required": false },
    "enabled": { "type": "boolean", "required": true, "indexed": true },
    "action": { "type": "enum", "values": ["allow", "deny", "drop", "reject"], "required": true, "indexed": true },
    "source": { "type": "string", "required": true },
    "source_zone": { "type": "string", "required": false },
    "destination": { "type": "string", "required": true },
    "destination_zone": { "type": "string", "required": false },
    "port": { "type": "string", "required": false },
    "protocol": { "type": "string", "required": false },
    "last_hit": { "type": "datetime", "required": false, "indexed": true },
    "hit_count": { "type": "integer", "required": false },
    "comment": { "type": "string", "required": false },
    "created_date": { "type": "datetime", "required": false },
    "modified_date": { "type": "datetime", "required": false },
    "extended_attributes": { "type": "object", "required": false }
  }
}
```

**Multi-Schema Extracted Records Strategy:**

The `extracted_records` table uses a hybrid approach to support multiple review types without schema migration:

- **Common fields** (id, extraction_id, record_index, identifier, display_name, validation_status) are normalized columns shared across all schema types
- A `record_type` discriminator column (`user_access`, `firewall_rule`) determines the schema type
- A `data` JSONB column stores schema-specific fields that are not part of the common set
- Fields needed for cross-reference matching (identifier, email) are always normalized columns
- Phase 1 implements `record_type = 'user_access'` only
- Phase 4 adds `record_type = 'firewall_rule'` without schema migration

**Schema Extension Support:**
```yaml
schema_extension:
  base_schema: "user_access"
  custom_fields:
    lending_limit:
      type: "number"
      description: "Maximum loan approval authority"
    dual_control_required:
      type: "boolean"
      description: "Requires second approval for transactions"
    branch_access:
      type: "array"
      items: "string"
      description: "Branches user can access"
```

#### 8.4 Database Schema (SQL)

```sql
-- ============================================================
-- updated_at AUTO-UPDATE TRIGGER
-- Applied to all tables with an updated_at column
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'analyst',  -- admin, analyst, reviewer, auditor
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TRIGGER update_timestamp BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- INVITE CODES
-- ============================================================
CREATE TABLE invites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255),                      -- Optional: restrict to specific email
    role VARCHAR(50) DEFAULT 'analyst',      -- Role to assign on registration
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    used_by UUID REFERENCES users(id) ON DELETE SET NULL,
    used_at TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_invites_code ON invites(code);
CREATE INDEX idx_invites_active ON invites(is_active) WHERE is_active = TRUE;

-- ============================================================
-- FRAMEWORKS (Immutable versions)
-- ============================================================
CREATE TABLE frameworks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    review_type VARCHAR(50) NOT NULL,
    version_major INTEGER DEFAULT 1,
    version_minor INTEGER DEFAULT 0,
    version_patch INTEGER DEFAULT 0,
    version_label VARCHAR(20) GENERATED ALWAYS AS (
        version_major || '.' || version_minor || '.' || version_patch
    ) STORED,
    effective_date DATE,
    expiration_date DATE,
    settings JSONB DEFAULT '{}',
    checks JSONB NOT NULL,  -- Array of check definitions (JSON Logic)
    regulatory_mappings JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    is_immutable BOOLEAN DEFAULT FALSE,  -- Set TRUE once used in a review
    parent_framework_id UUID REFERENCES frameworks(id) ON DELETE SET NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_frameworks_review_type ON frameworks(review_type);
CREATE INDEX idx_frameworks_active ON frameworks(is_active);
CREATE UNIQUE INDEX idx_frameworks_name_version ON frameworks(name, version_major, version_minor, version_patch)
    WHERE is_active = TRUE;

CREATE TRIGGER update_timestamp BEFORE UPDATE ON frameworks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- APPLICATIONS
-- ============================================================
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    review_type VARCHAR(50) NOT NULL,
    owner VARCHAR(255),
    owner_email VARCHAR(255),
    criticality VARCHAR(20) DEFAULT 'medium',  -- low, medium, high, critical
    data_classification VARCHAR(20) DEFAULT 'internal',  -- public, internal, confidential, restricted
    context TEXT,
    role_definitions JSONB DEFAULT '[]',
    regulatory_scope JSONB DEFAULT '[]',
    review_frequency VARCHAR(20) DEFAULT 'quarterly',
    next_review_date DATE,
    reminder_days JSONB DEFAULT '[30, 14, 7]',
    escalation_after_days INTEGER DEFAULT 14,
    is_active BOOLEAN DEFAULT TRUE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_applications_review_type ON applications(review_type);
CREATE INDEX idx_applications_criticality ON applications(criticality);
CREATE INDEX idx_applications_next_review ON applications(next_review_date);
CREATE UNIQUE INDEX idx_applications_name ON applications(name) WHERE is_active = TRUE;

CREATE TRIGGER update_timestamp BEFORE UPDATE ON applications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- DOCUMENT TEMPLATES
-- ============================================================
CREATE TABLE document_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID REFERENCES applications(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    format VARCHAR(50) NOT NULL,  -- csv, xlsx, xls, json, xml, pdf
    detection JSONB NOT NULL,  -- Detection rules (column presence, etc.)
    mapping JSONB NOT NULL,  -- Field mapping configuration
    validation JSONB DEFAULT '[]',  -- Validation rules
    confidence_threshold DECIMAL(3,2) DEFAULT 0.95,
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_templates_application ON document_templates(application_id);
CREATE UNIQUE INDEX idx_templates_name_app ON document_templates(name, application_id)
    WHERE is_active = TRUE;

CREATE TRIGGER update_timestamp BEFORE UPDATE ON document_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- REVIEWS
-- ============================================================
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    application_id UUID REFERENCES applications(id) ON DELETE RESTRICT,
    framework_id UUID REFERENCES frameworks(id) ON DELETE RESTRICT,
    framework_version_label VARCHAR(20) NOT NULL,  -- Snapshot of version used
    period_start DATE,
    period_end DATE,
    due_date DATE,                                   -- Review deadline
    status VARCHAR(50) DEFAULT 'created',
    -- Status enum: created, documents_uploaded, extracted, analyzed,
    --              findings_generated, pending_review, approved, closed, cancelled
    previous_review_id UUID REFERENCES reviews(id) ON DELETE SET NULL,
    analysis_checksum VARCHAR(64),  -- SHA-256 of analysis output
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_at TIMESTAMP,
    closed_at TIMESTAMP,

    -- AI-enriched summary (clearly separated)
    ai_summary TEXT,
    ai_summary_confidence DECIMAL(3,2),
    ai_summary_model VARCHAR(100),
    ai_summary_generated_at TIMESTAMP,

    -- Review-level notes and metadata
    reviewer_notes TEXT,
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_reviews_application ON reviews(application_id);
CREATE INDEX idx_reviews_status ON reviews(status);
CREATE INDEX idx_reviews_period ON reviews(period_start, period_end);
CREATE INDEX idx_reviews_due_date ON reviews(due_date);
CREATE INDEX idx_reviews_app_status ON reviews(application_id, status);
CREATE INDEX idx_reviews_assigned ON reviews(assigned_to) WHERE assigned_to IS NOT NULL;

CREATE TRIGGER update_timestamp BEFORE UPDATE ON reviews
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- REVIEW COMMENTS (threaded discussion on reviews/findings)
-- ============================================================
CREATE TABLE review_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id UUID NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    finding_id UUID,  -- NULL for review-level comments; FK added after findings table
    parent_comment_id UUID REFERENCES review_comments(id) ON DELETE CASCADE,
    author_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    body TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_review_comments_review ON review_comments(review_id);
CREATE INDEX idx_review_comments_finding ON review_comments(finding_id)
    WHERE finding_id IS NOT NULL;

CREATE TRIGGER update_timestamp BEFORE UPDATE ON review_comments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- DOCUMENTS
-- ============================================================
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id UUID REFERENCES reviews(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_hash VARCHAR(64) NOT NULL,  -- SHA-256
    file_size INTEGER NOT NULL,
    file_format VARCHAR(50) NOT NULL,
    template_id UUID REFERENCES document_templates(id) ON DELETE SET NULL,
    template_match_confidence DECIMAL(3,2),
    document_role VARCHAR(50) DEFAULT 'primary',  -- primary, supplementary, reference
    is_active BOOLEAN DEFAULT TRUE,
    uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    uploaded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_documents_review ON documents(review_id);

-- ============================================================
-- EXTRACTIONS
-- ============================================================
CREATE TABLE extractions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id UUID REFERENCES reviews(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    template_id UUID REFERENCES document_templates(id) ON DELETE SET NULL,
    record_count INTEGER NOT NULL,
    valid_record_count INTEGER NOT NULL,
    warning_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    confidence_score DECIMAL(5,4),  -- Overall extraction confidence
    extraction_tool VARCHAR(100),  -- e.g., "pandas 2.1.0", "camelot 0.11.0"
    extraction_metadata JSONB DEFAULT '{}',  -- Tool-specific metadata
    warnings JSONB DEFAULT '[]',
    checksum VARCHAR(64),  -- SHA-256 of extracted data
    confirmed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    confirmed_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_extractions_review ON extractions(review_id);

-- ============================================================
-- EXTRACTED RECORDS (Normalized with multi-schema support)
-- ============================================================
CREATE TABLE extracted_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_id UUID REFERENCES extractions(id) ON DELETE CASCADE,
    record_index INTEGER NOT NULL,  -- Row number in source
    record_type VARCHAR(50) NOT NULL DEFAULT 'user_access',  -- user_access, firewall_rule

    -- Common canonical fields (shared across all schema types)
    identifier VARCHAR(255),
    display_name VARCHAR(255),
    email VARCHAR(255),

    -- User access-specific fields (normalized for query performance)
    status VARCHAR(50),
    last_activity TIMESTAMP,
    created_date TIMESTAMP,
    department VARCHAR(255),
    manager VARCHAR(255),
    account_type VARCHAR(50) DEFAULT 'human',

    -- Variable fields stay as JSONB
    roles JSONB DEFAULT '[]',  -- Array of role strings
    extended_attributes JSONB DEFAULT '{}',

    -- Schema-specific data (for fields not in the common set)
    -- Firewall rules and future schema types store their fields here
    data JSONB DEFAULT '{}',

    -- Validation
    validation_status VARCHAR(20) DEFAULT 'valid',  -- valid, warning, error
    validation_messages JSONB DEFAULT '[]',

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_extracted_records_extraction ON extracted_records(extraction_id);
CREATE INDEX idx_extracted_records_identifier ON extracted_records(identifier);
CREATE INDEX idx_extracted_records_status ON extracted_records(status);
CREATE INDEX idx_extracted_records_last_activity ON extracted_records(last_activity);
CREATE INDEX idx_extracted_records_department ON extracted_records(department);
CREATE INDEX idx_extracted_records_account_type ON extracted_records(account_type);
CREATE INDEX idx_extracted_records_email ON extracted_records(email);
CREATE INDEX idx_extracted_records_record_type ON extracted_records(record_type);
CREATE INDEX idx_extracted_records_roles ON extracted_records USING GIN (roles jsonb_path_ops);
CREATE INDEX idx_extracted_records_extraction_status ON extracted_records(extraction_id, validation_status);

-- ============================================================
-- REFERENCE DATASETS
-- ============================================================
CREATE TABLE reference_datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    data_type VARCHAR(50) NOT NULL,  -- hr_employees, vendor_list, etc.
    source_system VARCHAR(255),
    freshness_threshold_days INTEGER DEFAULT 30,
    file_path VARCHAR(500) NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    record_count INTEGER NOT NULL,
    template_id UUID REFERENCES document_templates(id) ON DELETE SET NULL,
    uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE UNIQUE INDEX idx_reference_datasets_name ON reference_datasets(name) WHERE is_active = TRUE;

-- Reference dataset records (normalized)
CREATE TABLE reference_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID REFERENCES reference_datasets(id) ON DELETE CASCADE,
    record_index INTEGER NOT NULL,
    identifier VARCHAR(255),
    display_name VARCHAR(255),
    email VARCHAR(255),
    employment_status VARCHAR(50),
    department VARCHAR(255),
    termination_date DATE,
    extended_attributes JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_reference_records_dataset ON reference_records(dataset_id);
CREATE INDEX idx_reference_records_identifier ON reference_records(identifier);
CREATE INDEX idx_reference_records_email ON reference_records(email);
CREATE INDEX idx_reference_records_status ON reference_records(employment_status);

-- ============================================================
-- FINDINGS
-- ============================================================
CREATE TABLE findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id UUID REFERENCES reviews(id) ON DELETE CASCADE,
    check_id VARCHAR(100) NOT NULL,
    check_name VARCHAR(255) NOT NULL,
    severity VARCHAR(50) NOT NULL,  -- critical, high, medium, low, info

    -- Deterministic content
    explainability TEXT NOT NULL,  -- Template-generated explanation

    -- AI-enriched content (clearly separated)
    ai_description TEXT,
    ai_remediation TEXT,
    ai_generated BOOLEAN DEFAULT FALSE,
    ai_confidence DECIMAL(3,2),
    ai_model VARCHAR(100),
    ai_generated_at TIMESTAMP,

    -- Review disposition
    disposition VARCHAR(50),  -- approved, revoke, abstain (null = not yet reviewed)
    disposition_by UUID REFERENCES users(id) ON DELETE SET NULL,
    disposition_at TIMESTAMP,
    disposition_note TEXT,  -- Required for approve and abstain

    -- Finding status
    status VARCHAR(50) DEFAULT 'open',  -- open, in_progress, remediated, accepted_risk, closed
    record_count INTEGER NOT NULL,

    -- Record details stored as references to extracted_records
    affected_record_ids JSONB NOT NULL,  -- Array of extracted_record UUIDs
    output_fields JSONB NOT NULL,  -- Which fields to display

    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_findings_review ON findings(review_id);
CREATE INDEX idx_findings_severity ON findings(severity);
CREATE INDEX idx_findings_status ON findings(status);
CREATE INDEX idx_findings_disposition ON findings(disposition);
CREATE INDEX idx_findings_check ON findings(check_id);
CREATE INDEX idx_findings_review_severity ON findings(review_id, severity);
CREATE INDEX idx_findings_review_status ON findings(review_id, status);
CREATE INDEX idx_findings_review_disposition ON findings(review_id, disposition);

CREATE TRIGGER update_timestamp BEFORE UPDATE ON findings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Add FK from review_comments to findings (deferred because findings created after review_comments)
ALTER TABLE review_comments
    ADD CONSTRAINT fk_review_comments_finding
    FOREIGN KEY (finding_id) REFERENCES findings(id) ON DELETE CASCADE;

-- ============================================================
-- AUDIT LOG (Append-only, hash-chained)
-- ============================================================
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    actor_id UUID REFERENCES users(id) ON DELETE SET NULL,
    actor_type VARCHAR(20) NOT NULL DEFAULT 'USER',  -- USER, SYSTEM, RULE_ENGINE, AI_SERVICE
    session_id VARCHAR(100),
    request_id VARCHAR(100),  -- Correlation ID from API request
    action VARCHAR(50) NOT NULL,  -- create, read, update, delete, execute, confirm, approve, reject, login, logout
    entity_type VARCHAR(50) NOT NULL,  -- framework, application, review, document, extraction, finding, etc.
    entity_id UUID,
    before_state JSONB,  -- State before mutation (null for create/read)
    after_state JSONB,   -- State after mutation (null for delete/read)
    metadata JSONB DEFAULT '{}',  -- Additional context (IP, user agent, etc.)
    content_hash VARCHAR(64) NOT NULL,  -- SHA-256 of this entry's content
    previous_hash VARCHAR(64),  -- Hash of previous entry (chain link)

    -- AI-specific logging
    ai_model VARCHAR(100),
    ai_input_hash VARCHAR(64),
    ai_output_hash VARCHAR(64),
    ai_confidence DECIMAL(3,2),
    ai_duration_ms INTEGER
);

-- Prevent UPDATE and DELETE on audit_log
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit log entries cannot be modified or deleted';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_no_update
    BEFORE UPDATE ON audit_log
    FOR EACH ROW
    EXECUTE FUNCTION prevent_audit_modification();

CREATE TRIGGER audit_no_delete
    BEFORE DELETE ON audit_log
    FOR EACH ROW
    EXECUTE FUNCTION prevent_audit_modification();

-- Indexes for audit queries
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_log_actor ON audit_log(actor_id);
CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_hash ON audit_log(content_hash);
CREATE INDEX idx_audit_log_chain ON audit_log(previous_hash);
CREATE INDEX idx_audit_log_entity_action ON audit_log(entity_type, entity_id, action);
CREATE INDEX idx_audit_log_actor_timestamp ON audit_log(actor_id, timestamp);
CREATE INDEX idx_audit_log_request_id ON audit_log(request_id) WHERE request_id IS NOT NULL;

-- ============================================================
-- AI INVOCATION LOG (Separate for PII protection)
-- ============================================================
CREATE TABLE ai_invocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id UUID REFERENCES reviews(id) ON DELETE SET NULL,
    finding_id UUID REFERENCES findings(id) ON DELETE SET NULL,
    function_type VARCHAR(50) NOT NULL,  -- description, remediation, summary, pattern, mapping
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50),
    input_hash VARCHAR(64) NOT NULL,  -- Hash of input (not content, for PII)
    output_hash VARCHAR(64) NOT NULL,
    confidence_score DECIMAL(3,2),
    temperature DECIMAL(2,1),
    token_count_input INTEGER,
    token_count_output INTEGER,
    duration_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ai_invocations_review ON ai_invocations(review_id);
CREATE INDEX idx_ai_invocations_type ON ai_invocations(function_type);

-- ============================================================
-- AI USAGE LOG (Token tracking and cost estimation)
-- ============================================================
CREATE TABLE ai_usage_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id UUID REFERENCES reviews(id) ON DELETE SET NULL,
    invocation_id UUID REFERENCES ai_invocations(id) ON DELETE SET NULL,
    model_name VARCHAR(100) NOT NULL,
    function_type VARCHAR(50) NOT NULL,  -- description, remediation, summary, mapping
    tokens_input INTEGER NOT NULL DEFAULT 0,
    tokens_output INTEGER NOT NULL DEFAULT 0,
    cost_estimate_usd DECIMAL(10,6),  -- Estimated cost in USD
    duration_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_code VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ai_usage_review ON ai_usage_log(review_id);
CREATE INDEX idx_ai_usage_model ON ai_usage_log(model_name);
CREATE INDEX idx_ai_usage_created ON ai_usage_log(created_at);

-- ============================================================
-- NOTIFICATION PREFERENCES
-- ============================================================
CREATE TABLE notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel VARCHAR(50) NOT NULL DEFAULT 'email',  -- email, in_app
    event_type VARCHAR(100) NOT NULL,  -- review.assigned, review.overdue, finding.created, etc.
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (user_id, channel, event_type)
);

CREATE INDEX idx_notification_prefs_user ON notification_preferences(user_id);

CREATE TRIGGER update_timestamp BEFORE UPDATE ON notification_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- REVIEW-REFERENCE DATASET JUNCTION
-- ============================================================
CREATE TABLE review_reference_datasets (
    review_id UUID REFERENCES reviews(id) ON DELETE CASCADE,
    reference_dataset_id UUID REFERENCES reference_datasets(id) ON DELETE RESTRICT,
    purpose VARCHAR(100),  -- e.g., "cross_reference_hr"
    added_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (review_id, reference_dataset_id)
);

-- ============================================================
-- FOREIGN KEY ON DELETE BEHAVIOR SUMMARY
-- ============================================================
-- The following rules govern referential integrity:
--
-- ON DELETE CASCADE: Child data has no meaning without parent
--   - documents -> reviews (documents belong to a review)
--   - extractions -> reviews, documents (extraction is part of review lifecycle)
--   - extracted_records -> extractions (records belong to an extraction)
--   - findings -> reviews (findings belong to a review)
--   - review_comments -> reviews (comments belong to a review)
--   - document_templates -> applications (templates belong to an application)
--   - notification_preferences -> users (preferences belong to a user)
--   - review_reference_datasets -> reviews (junction row is part of review)
--
-- ON DELETE RESTRICT: Parent must not be deleted while children exist
--   - reviews -> applications (reviews are audit evidence; application cannot be removed)
--   - reviews -> frameworks (reviews are audit evidence; framework cannot be removed)
--   - review_reference_datasets -> reference_datasets (preserve reference data)
--   - review_comments -> users (author_id: preserve comment attribution)
--
-- ON DELETE SET NULL: Reference is informational, not structural
--   - reviews -> users (created_by, assigned_to, approved_by)
--   - frameworks -> users (created_by)
--   - applications -> users (created_by)
--   - documents -> users (uploaded_by)
--   - findings -> users (disposition_by)
--   - reviews -> reviews (previous_review_id)
--   - frameworks -> frameworks (parent_framework_id)

-- ============================================================
-- PARTITIONING for audit_log (by month)
-- ============================================================
-- Note: Implement table partitioning for audit_log by timestamp
-- for long-term retention (5+ years) with efficient archival.
-- Partition monthly: audit_log_2026_01, audit_log_2026_02, etc.
-- Archive partitions older than 2 years to cold storage.

-- ============================================================
-- ROW-LEVEL SECURITY (prepared for multi-tenant future)
-- ============================================================
-- ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY reviews_isolation ON reviews
--     USING (org_id = current_setting('app.current_org_id')::uuid);
-- (Uncomment when multi-tenancy is implemented)

-- ============================================================
-- DATABASE ROLES AND PERMISSIONS
-- ============================================================
-- Application role (used by FastAPI and Celery)
-- CREATE ROLE sapv2_app WITH LOGIN PASSWORD '...';
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO sapv2_app;
-- GRANT SELECT, INSERT ON audit_log TO sapv2_app;  -- No UPDATE/DELETE
-- REVOKE UPDATE, DELETE ON audit_log FROM sapv2_app;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO sapv2_app;
--
-- Read-only role (for reporting and monitoring)
-- CREATE ROLE sapv2_readonly WITH LOGIN PASSWORD '...';
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO sapv2_readonly;
--
-- Migration role (used by Alembic only)
-- CREATE ROLE sapv2_migrate WITH LOGIN PASSWORD '...';
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO sapv2_migrate;
```

---

### 9. User Interface Requirements

#### 9.1 Design System

**Visual Language:**
- Clean, professional interface appropriate for financial services
- White/light gray backgrounds with blue primary accent (trust, professionalism)
- shadcn/ui component library with Tailwind CSS utility classes
- Consistent spacing: 4px grid system
- Typography: System font stack (Inter preferred, fallback to system)
- Responsive: Desktop-first (primary use case) with tablet support
- Theming: Use CSS custom properties (Tailwind CSS themes) from the start so dark mode can be added without refactoring. shadcn/ui supports this natively.

**Iconography:** Lucide Icons (the default for shadcn/ui) with consistent assignments:
- Dashboard: `LayoutDashboard`
- Reviews: `ClipboardCheck`
- Frameworks: `Shield`
- Applications: `Server`
- Reference Data: `Database`
- Reports: `FileText`
- Admin/Settings: `Settings`
- Audit Log: `ScrollText`
- Users: `Users`

**Severity Color System (Accessibility-Compliant):**

Severity indicators NEVER rely on color alone. Each severity level combines color, symbol, and text label per WCAG 2.1 AA requirements:

| Severity | Color (hex) | Symbol | Label | Background | ARIA Label |
|----------|-------------|--------|-------|------------|------------|
| Critical | #D32F2F (red) | Triangle | "CRITICAL" | #FFEBEE | "Critical severity" |
| High | #F57C00 (orange) | Diamond | "HIGH" | #FFF3E0 | "High severity" |
| Medium | #FBC02D (amber) | Circle | "MEDIUM" | #FFFDE7 | "Medium severity" |
| Low | #388E3C (green) | Square | "LOW" | #E8F5E9 | "Low severity" |
| Info | #1976D2 (blue) | Info circle | "INFO" | #E3F2FD | "Info severity" |

**Status Color System:**

| Status | Color | Badge Style |
|--------|-------|-------------|
| Open | Red outline | Outlined badge |
| In Progress | Blue outline | Outlined badge |
| Pending Review | Amber outline | Outlined badge |
| Approved | Green filled | Filled badge |
| Closed | Gray filled | Filled badge |

**AI Content Indicators:**

All AI-generated content uses a consistent visual treatment:
- Light purple/violet background tint (#F3E8FD) -- verified contrast: dark gray text (#1a1a1a) on #F3E8FD = approximately 15:1 ratio (passes WCAG AA)
- "AI-Generated" badge in top-right corner with confidence score meter
- Confidence score meter must maintain sufficient contrast in both filled and unfilled states
- "Pending Review" status until human approves
- "Regenerate" and "Edit" action buttons
- AI content rendered as plain text by default. If markdown rendering is used, it must pass through a sanitizing renderer (e.g., react-markdown with rehype-sanitize). Never use `dangerouslySetInnerHTML` for AI content.

**Contrast Requirements:** All text meets WCAG 2.1 AA: 4.5:1 for normal text, 3:1 for large text (18px+) and UI components. All interactive elements have visible focus indicators (2px minimum).

**Animation and Transitions:**
- Duration scale: fast (150ms), normal (250ms), slow (350ms)
- Easing: ease-out for entrances, ease-in for exits, ease-in-out for state changes
- Sidebar collapse: 250ms ease-in-out width transition
- Modal open/close: 200ms fade + scale (0.95 to 1.0)
- Toast enter/exit: 200ms slide-in from top-right, 150ms fade-out
- Page transitions: No animation (instant swap) -- page transitions must feel instant per NFR-1.6
- Respect `prefers-reduced-motion`: Disable all non-essential animations

**Z-Index Strategy:**

| Layer | Z-Index Range | Components |
|-------|---------------|------------|
| Base content | z-0 through z-10 | Page content, cards, tables |
| Sidebar | z-20 | Navigation sidebar |
| Sticky headers / action bars | z-30 | Table headers, bulk action bars |
| Dropdowns / popovers | z-40 | Select menus, date pickers, tooltips |
| Modal backdrop | z-50 | Modal overlay |
| Modal content | z-51 | Modal dialogs |
| Toast notifications | z-60 | Success/error/warning toasts |
| Tooltips | z-70 | Help tooltips |

Note: shadcn/ui + Radix primitives handle much of this automatically, but custom components must follow this strategy for consistency.

**Modal / Dialog Types:**

| Type | Width | Use Cases | Behavior |
|------|-------|-----------|----------|
| Alert dialog | 400px | Confirmations, destructive action warnings | Two buttons max, no nested modals |
| Form dialog | 560px | Disposition entry, note addition, invite creation | Closes on submit or cancel |
| Full dialog | 800px | Review sign-off, template test results, extraction review | May include tables/scrollable content |
| Sheet/drawer | Right side overlay | Finding detail on smaller screens, help panel | Slides in from right |

All modals: Close on Escape key, trap focus within, return focus to trigger element on close, backdrop click closes (except for alert/confirmation dialogs).

**Form Validation Display:**
- Inline validation: Error message directly below the field, in red (#D32F2F), with a warning icon. Trigger on blur (not on every keystroke).
- Required field indicators: Red asterisk (*) on label. Error message reads "Required" (not just a red border).
- Form-level errors: Summary banner at top of form listing all errors (linked to fields) when user attempts to submit with errors.
- Wizard steps: Validate on "Next" click. Prevent advancing until step is valid. Show validation summary for the current step.

**Browser Support Matrix:**
- Chrome 100+ (primary target)
- Firefox 100+
- Safari 16+
- Edge 100+
- No IE11 support

#### 9.2 Responsive Design

**Breakpoint Definitions (Tailwind defaults):**

| Breakpoint | Width | Layout Behavior |
|------------|-------|-----------------|
| Desktop (xl) | >= 1280px | Full layout as wireframed: sidebar + content with master-detail panels |
| Small desktop / tablet landscape (lg) | 1024px - 1279px | Sidebar collapses to icons-only. Master-detail panels use 40/60 split instead of 33/67 |
| Tablet portrait (md) | 768px - 1023px | Sidebar becomes hamburger menu overlay. Master-detail becomes stacked (list view, tap to navigate to detail). Dashboard cards stack in single column |
| Below 768px (sm) | < 768px | Not supported for POC. Show "Please use a desktop or tablet in landscape mode" message |

**Data Table Responsive Behavior:**
- Use TanStack Table column visibility to auto-hide lower-priority columns at smaller breakpoints
- Define column priority per table (e.g., for findings: severity and check name always visible; record count and disposition status secondary; timestamps hidden on small screens)
- Provide a "Columns" dropdown for users to toggle visibility
- For extracted records table (potentially 10+ columns), switch to card view on tablet

**Complex Layout Adaptations:**
- Framework Builder on tablet: Collapse to single-column layout. Check list and check editor become separate views (tap check to open editor full-screen). Replace drag-and-drop reordering with up/down buttons.
- Mapping Editor on tablet: Replace split-pane with sequential flow: (1) View source fields, (2) For each target field select source field from dropdown, (3) Configure transform, (4) Preview. No visual connection lines on tablet.
- Review Workspace on tablet: Findings list and finding detail become back-and-forth navigation (list view, tap to open detail view, back button to return).

#### 9.3 Navigation Structure

Primary navigation is a left sidebar with icon + label. Collapsible to icon-only on smaller screens.

```
+------------------------------------------------------------+
|  SAPv2                                   [Cmd+K] [User   ] |
+---------------+--------------------------------------------+
|               |                                            |
|  Dashboard    |  [Main Content Area]                       |
|               |                                            |
|  Reviews      |                                            |
|   - Active    |                                            |
|   - Completed |                                            |
|   - Create    |                                            |
|               |                                            |
|  Frameworks   |                                            |
|   - Library   |                                            |
|   - Create    |                                            |
|               |                                            |
|  Applications |                                            |
|   - Registry  |                                            |
|   - Add New   |                                            |
|   - Templates |                                            |
|               |                                            |
|  Reference    |                                            |
|    Data       |                                            |
|               |                                            |
|  Reports      |                                            |
|   - Generate  |                                            |
|   - Archive   |                                            |
|               |                                            |
|  Admin        |                                            |
|   - Users     |                                            |
|   - Audit Log |                                            |
|   - Settings  |                                            |
|               |                                            |
+---------------+--------------------------------------------+
```

**Global Search (Cmd+K / Ctrl+K):** Command palette-style search bar in the top header. Searches across applications (by name), frameworks (by name/check name), reviews (by name/application), findings (by check name/affected user), and audit entries (by action/entity). Results are grouped by entity type. Recent searches are saved for quick access. For POC: simple text search against indexed fields. Full-text search deferred to a later phase.

#### 9.4 Key Screens -- Detailed Specifications

**9.4.1 Login Page**

```
+------------------------------------------------------------+
|                                                            |
|                     SAPv2                                  |
|              Security Analyst Platform                     |
|                                                            |
|          +----------------------------------+              |
|          |                                  |              |
|          |  Email                           |              |
|          |  [________________________]      |              |
|          |                                  |              |
|          |  Password                        |              |
|          |  [________________________]      |              |
|          |                                  |              |
|          |  [        Sign In         ]      |              |
|          |                                  |              |
|          |  Don't have an account?           |              |
|          |  Register with invite code        |              |
|          |                                  |              |
|          +----------------------------------+              |
|                                                            |
+------------------------------------------------------------+
```

**Login Page Behavior:**
- Email + password fields with sign-in button
- "Register with invite code" link navigates to registration form
- Error messages for: invalid credentials (generic "Invalid email or password" -- do not reveal which is wrong), locked account, expired session redirect
- After successful login, redirect to the page the user originally requested (or Dashboard by default)
- Bank-appropriate branding area at top
- No "forgot password" link until password reset flow is implemented (avoid dead links)

**9.4.2 Dashboard**

The dashboard follows an F-pattern reading hierarchy:

```
+--------------------------------------------------------------------+
|                          DASHBOARD                                  |
+--------------------------------------------------------------------|
|                                                                     |
|  +--- Compliance Score ---+ +-- Open Findings --+ +-- Upcoming ---+ |
|  |                        | |                    | |               | |
|  |   87%  (up 3% from Q3)| |  Crit: 2           | |  Fedlink UAR  | |
|  |   [Progress Ring]      | |  High: 5           | |  Due: Mar 15  | |
|  |                        | |  Med:  12          | |               | |
|  |                        | |  Low:  3           | |  JH Core UAR  | |
|  |                        | |                    | |  Due: Apr 01  | |
|  +------------------------+ +--------------------+ +---------------+ |
|                                                                     |
|  +--- Active Reviews -------------------------------------------+  |
|  |                                                               |  |
|  |  Application      Framework         Status          Due Date |  |
|  |  ----------------------------------------------------------- |  |
|  |  Fedlink Anywhere  UAR Standard v1.0  Pending Review  Feb 28 |  |
|  |  JH Silverlake     UAR Standard v1.0  Extracted       Mar 15 |  |
|  |  Firewall (Palo)   FW Review v1.0     Created         Mar 30 |  |
|  |                                                               |  |
|  +---------------------------------------------------------------+  |
|                                                                     |
|  +--- Compliance Trend (12 months) ------------------------------+  |
|  |                                                               |  |
|  |  [Line chart: findings over time by severity]                |  |
|  |                                                               |  |
|  +---------------------------------------------------------------+  |
|                                                                     |
|  +--- Recent Activity -------------------------------------------+  |
|  |  Josh confirmed extraction for Fedlink Anywhere (2 hrs ago)   |  |
|  |  System completed analysis for JH Silverlake (4 hrs ago)      |  |
|  |  Maria approved Fedlink UAR Q4 2025 (yesterday)              |  |
|  +---------------------------------------------------------------+  |
|                                                                     |
+---------------------------------------------------------------------+
```

**Dashboard Components:**
- **Compliance Score**: Calculated from open findings weighted by severity. Ring/gauge visualization with trend arrow. ARIA: `role="meter"` with `aria-valuenow`, `aria-valuemin="0"`, `aria-valuemax="100"`, `aria-label="Compliance score: 87 percent"`.
- **Open Findings Summary**: Count by severity with severity icons. Clickable to filter finding list
- **Upcoming Reviews**: Next 3 reviews by due date with countdown. Color-coded: green (>14 days), amber (7-14 days), red (<7 days or overdue)
- **Active Reviews Table**: All non-closed reviews with status badges. Click row to open review workspace
- **Compliance Trend Chart**: 12-month line chart showing finding counts by severity. Hover for details
- **Recent Activity Feed**: Last 10 audit log entries in human-readable format

**Dashboard Empty State (first use):** "Welcome to SAPv2. Get started by configuring your first application." with a guided setup checklist linking to: (1) Configure your first application, (2) Set up a framework, (3) Upload a reference dataset, (4) Create your first review.

**9.4.3 Review Workspace**

The primary screen for conducting a review. Layout adapts based on review status:

```
+--------------------------------------------------------------------+
|  Review: Fedlink Anywhere UAR - Q1 2026                             |
|  Application: Fedlink Anywhere | Framework: UAR Standard v1.0       |
|  Period: Jan 1 - Mar 31, 2026 | Assigned: Josh Lopez               |
|                                                                      |
|  Status: [PENDING REVIEW]                                           |
|                                                                      |
|  +--- Progress Steps -----------------------------------------------+
|  |  [check] Created > [check] Documents > [check] Extracted >       |
|  |  [check] Analyzed > [check] Enriched > [current] In Review >     |
|  |  [ ] Approved                                                     |
|  +-------------------------------------------------------------------+
|                                                                      |
|  +--- Findings Summary ----------------------------------------------+
|  |  Crit: 1 | High: 2 | Med: 5 | Low: 1 | Info: 3                  |
|  |  Total: 12 findings across 847 records                            |
|  |  Disposition: 4/12 complete                                       |
|  +-------------------------------------------------------------------+
|                                                                      |
|  +--- Findings List ---------+ +--- Finding Detail ----------------+ |
|  |                            | |                                   | |
|  |  [Filter: All] [Sort: Sev]| |  CRITICAL                         | |
|  |  [Select All] [Bulk ...]  | |  Terminated Employee               | |
|  |                            | |  with Active Access               | |
|  |  [ ] Crit: Terminated w/  | |                                   | |
|  |       Access    1 record  | |  Records: 1                       | |
|  |       Not reviewed        | |  --------------------------       | |
|  |                            | |  jdoe | John Doe                  | |
|  |  [ ] High: SoD Violation  | |  Status: Active                   | |
|  |       3 records           | |  Last Login: 11/15/2025           | |
|  |       Revoke(2) Pend(1)   | |  Roles: Wire Initiator            | |
|  |                            | |                                   | |
|  |  [ ] Med: Inactive Accts  | |  -- Explainability --             | |
|  |       23 records          | |  This check cross-references      | |
|  |       Not reviewed        | |  application users against HR...  | |
|  |                            | |                                   | |
|  |  [ ] Med: High Dollar     | |  -- AI Description --             | |
|  |       5 records           | |  AI-Generated (0.94)              | |
|  |       Approved (5)        | |  [purple tint bg]                 | |
|  |                            | |  This finding...                  | |
|  |  ...                      | |  [Edit] [Regenerate]              | |
|  |                            | |                                   | |
|  +----------------------------+ |  -- Disposition --                | |
|                                 |  [Approve] [Revoke] [Abstain]    | |
|                                 |  Justification: [___________]    | |
|                                 |  [Comments (3)]                  | |
|                                 +-----------------------------------+ |
+----------------------------------------------------------------------+
```

**Review Workspace Features:**
- **Progress Steps**: Horizontal stepper showing review lifecycle. Completed steps have checkmarks. Current step is highlighted. Future steps are grayed. ARIA: `role="list"` with each step as `role="listitem"`, current step has `aria-current="step"`. Step changes announced via `aria-live` region.
- **Findings Summary Bar**: At-a-glance severity counts with icons. Disposition progress (X of Y complete).
- **Findings List (Left Panel)**: Filterable by severity, status, disposition. Sortable by severity, record count, check name. Shows disposition status per finding. Click to select and view detail. Checkbox selection for bulk operations.
- **Finding Detail (Right Panel)**: Full finding information. Affected records table with output_fields. Deterministic explainability statement. AI-generated description (clearly labeled, purple tint). AI-generated remediation (clearly labeled). Disposition controls (Approve/Revoke/Abstain) with required justification text field. Notes field and threaded comments.
- **State-Appropriate Actions**: Button bar at top changes based on review status. E.g., "Run Analysis" when in EXTRACTED state, "Submit for Approval" when all dispositions complete.
- **Bulk Disposition**: When checkboxes are selected, a bulk action bar appears with: Approve Selected, Revoke Selected, Abstain Selected. Single justification field applies to all selected. Confirmation dialog before applying. Each disposition logged individually in audit trail.

**Keyboard Shortcuts (Review Workspace):**
- `j` / `k` or Arrow Down / Arrow Up: Navigate findings list
- `a`: Set disposition to Approve (opens justification field)
- `r`: Set disposition to Revoke
- `b`: Set disposition to Abstain
- `Enter`: Confirm disposition (after typing justification)
- `n`: Focus notes field
- `?`: Show keyboard shortcut help overlay

**9.4.4 Review Approval / Sign-Off Screen**

Displayed as a full dialog (800px) when the reviewer clicks "Submit for Approval" after all dispositions are complete:

```
+--------------------------------------------------------------------+
|  Review Sign-Off: Fedlink Anywhere UAR - Q1 2026                    |
|                                                                      |
|  Application: Fedlink Anywhere                                       |
|  Framework: UAR Standard v1.0                                        |
|  Period: Jan 1 - Mar 31, 2026                                       |
|  Documents: fedlink_users_q1_2026.csv (SHA: a3f2b7c...)             |
|  Extraction Checksum: 8d4e1f2...                                    |
|  Analysis Checksum: 2c9a0b3...                                      |
|                                                                      |
|  +--- Disposition Summary -------------------------------------------+
|  |  Check Name              Severity  Records  Disposition           |
|  |  ---------------------------------------------------------------  |
|  |  Terminated w/ Access    CRITICAL  1        Revoke                |
|  |  SoD Violation           HIGH      3        Revoke(2), Approve(1) |
|  |  Inactive Accounts       MEDIUM    23       Approve (all)        |
|  |  High Dollar Limits      MEDIUM    5        Approve (all)        |
|  |  ...                                                              |
|  +-------------------------------------------------------------------+
|                                                                      |
|  Summary: 4 Approved | 3 Revoked | 1 Abstained                      |
|                                                                      |
|  [checkbox] I have reviewed all findings and attest that the         |
|  dispositions above represent my professional judgment.              |
|                                                                      |
|  [Cancel]                                    [Sign Off and Approve]  |
+----------------------------------------------------------------------+
```

**Sign-Off Behavior:**
- Review metadata summary including document hashes, extraction checksums, and analysis checksum for integrity verification
- Complete findings disposition table (all decisions visible at once)
- Attestation checkbox must be checked before the "Sign Off and Approve" button becomes active
- Sign-off action logs to audit trail with attestation text, reviewer name, and timestamp
- Warning displayed if any findings lack disposition (should be blocked by workflow rules, but defensive display)

**9.4.5 Framework Builder**

Visual editor for creating and editing frameworks. No code writing required.

```
+--------------------------------------------------------------------+
|  Framework Builder: User Access Review - Standard                    |
|  Version: 1.0.0 | Review Type: User Access | Status: Draft          |
|                                                                      |
|  +--- Settings ---------------------------------------------------+  |
|  |  Inactive Threshold:  [90] days                                |  |
|  |  Review Period:       [3] months                               |  |
|  |  Manager Attestation: [check] Required                         |  |
|  |  High Limit Threshold: [$1,000,000]                            |  |
|  +----------------------------------------------------------------+  |
|                                                                      |
|  +--- Checks -----------------------------------------------------+  |
|  |                                                                 |  |
|  |  [+ Add Check]  [Import Check]  [Test All Against Sample Data] |  |
|  |                                                                 |  |
|  |  [=] 1. Inactive User Accounts              Medium   [On]     |  |
|  |  [=] 2. Segregation of Duties Violation      High     [On]     |  |
|  |  [=] 3. Terminated Employee w/ Active Access Critical [On]     |  |
|  |  [=] 4. Privileged Access Review             Info     [On]     |  |
|  |  [=] 5. Disabled Accounts Not Removed        Low      [On]     |  |
|  |                                                                 |  |
|  +----------------------------------------------------------------+  |
|                                                                      |
|  +--- Check Editor (selected: #1 Inactive User Accounts) --------+  |
|  |                                                                 |  |
|  |  Name: [Inactive User Accounts                            ]    |  |
|  |  Description: [Accounts with no login activity beyond thresh]  |  |
|  |                                                                 |  |
|  |  -- Conditions --                                              |  |
|  |                                                                 |  |
|  |  IF  [All] of the following are true:                          |  |
|  |                                                                 |  |
|  |  +- Condition Row -----------------------------------------+   |  |
|  |  | [Status]  [equals]  [active]                       [X] |   |  |
|  |  +--------------------------------------------------------+   |  |
|  |  +- Condition Row -----------------------------------------+   |  |
|  |  | [Last Activity]  [older than]  [90] days           [X] |   |  |
|  |  +--------------------------------------------------------+   |  |
|  |  [+ Add Condition]                                             |  |
|  |                                                                 |  |
|  |  Plain English:                                                 |  |
|  |  "Active accounts where last login is more than 90 days ago"   |  |
|  |                                                                 |  |
|  |  -- Severity --                                                |  |
|  |  Default: [Medium]                                             |  |
|  |  [ ] Use conditional severity rules                            |  |
|  |                                                                 |  |
|  |  -- Output Fields --                                           |  |
|  |  [check] Identifier  [check] Display Name  [check] Last Activity|  |
|  |  [check] Department  [check] Roles         [ ] Email          |  |
|  |                                                                 |  |
|  |  -- Remediation Guidance --                                    |  |
|  |  [Accounts inactive for extended periods should be reviewed...]|  |
|  |                                                                 |  |
|  |  [Test Check]  [Save Check]  [Delete Check]                    |  |
|  +----------------------------------------------------------------+  |
|                                                                      |
|  [Save Framework as Draft]  [Publish Version]                        |
+----------------------------------------------------------------------+
```

**Framework Builder Features:**
- **Settings Panel**: Key/value pairs for framework-wide settings referenced by checks via ${settings.x}
- **Check List**: Drag handle for reordering (desktop only; up/down buttons on tablet). Severity icon + name + toggle. Click to edit in Check Editor below. ARIA: ordered list with condition builder rows as a table with column headers (Field, Operator, Value). Announce add/remove actions with live region.
- **Check Editor - Condition Builder**: Visual rows with field/operator/value dropdowns. AND/OR grouping selector. Add/remove condition rows. Plain-English summary auto-generated below conditions.
- **Check Editor - Severity**: Default severity dropdown. Optional conditional severity rules (expandable).
- **Check Editor - Output Fields**: Checkbox list of canonical schema fields to include in findings.
- **Test Check**: Upload or select sample data, run check, show preview of matching records.
- **Publish Version**: Creates immutable version. Warns if checks are incomplete.

**Drag-and-Drop Feedback:**
- Check reordering: Blue insertion line between items during drag. Ghost element follows cursor at 50% opacity. Invalid drop zones are grayed out.
- Accessible alternative: Up/down arrow buttons always visible alongside drag handles.

**9.4.6 Application Configuration**

```
+--------------------------------------------------------------------+
|  Application: Fedlink Anywhere                                       |
|                                                                      |
|  +--- Tabs --------------------------------------------------------+|
|  |  [General] [Templates] [Role Definitions] [Review History]       ||
|  +------------------------------------------------------------------+|
|                                                                      |
|  +--- General Tab -------------------------------------------------+ |
|  |                                                                  | |
|  |  Name:               [Fedlink Anywhere                      ]   | |
|  |  Description:        [Federal Reserve wire transfer system  ]   | |
|  |  Owner:              [Operations Department                 ]   | |
|  |  Owner Email:        [ops@keysbank.com                      ]   | |
|  |  Review Type:        [User Access]                              | |
|  |  Criticality:        [High]                                     | |
|  |  Data Classification:[Confidential]                             | |
|  |  Regulatory Scope:   [check] GLBA [check] FFIEC [ ] SOX        | |
|  |                      [check] BSA                                | |
|  |                                                                  | |
|  |  Review Schedule:                                                | |
|  |    Frequency:        [Quarterly]                                | |
|  |    Next Review:      [2026-04-01]                               | |
|  |    Reminders:        [30, 14, 7] days before                    | |
|  |    Escalation:       [14] days after due                        | |
|  |                                                                  | |
|  |  Context (for AI enrichment):                                    | |
|  |  [This is the Federal Reserve wire transfer system used for     | |
|  |   sending and receiving Fedwire transfers. Access is highly     | |
|  |   sensitive due to the ability to move funds...]                | |
|  |                                                                  | |
|  +------------------------------------------------------------------+|
|                                                                      |
|  [Save Changes]                                                      |
+----------------------------------------------------------------------+
```

**9.4.7 Document Mapping Editor**

Split-pane editor for creating and editing document templates:

```
+--------------------------------------------------------------------+
|  Template Editor: Fedlink Anywhere Users Export                       |
|  Application: Fedlink Anywhere | Format: CSV                         |
|                                                                      |
|  +--- Source Fields (detected) ------+  +--- Target Schema --------+|
|  |                                    |  |  (User Access)           ||
|  |  userid          o--------------+--+--+--> identifier   mapped  ||
|  |  username        o--------------+--+--+--> display_name mapped  ||
|  |  email           o--------------+--+--+--> email        mapped  ||
|  |  status          o---- [T] -----+--+--+--> status       mapped  ||
|  |  lastlogin       o---- [T] -----+--+--+--> last_activity mapped ||
|  |  authgroup       o---- [T] -----+--+--+--> roles        mapped  ||
|  |  limit           o--------------+--+--+--> ext.limit    mapped  ||
|  |  usrlevel        o--------------+--+--+--> ext.usrlevel mapped  ||
|  |                                    |  |                          ||
|  |                                    |  |     department  unmapped ||
|  |                                    |  |     manager     unmapped ||
|  |                                    |  |     account_type default ||
|  |                                    |  |                          ||
|  +------------------------------------+  +--------------------------+|
|                                                                      |
|  Mapping Completeness: [==========------] 73% (8/11 fields)         |
|                                                                      |
|  +--- Transformation Editor (selected: status) -------------------+  |
|  |                                                                 |  |
|  |  Source: "status"  -->  Target: "status"                        |  |
|  |  Transform: [Value Map]                                         |  |
|  |                                                                 |  |
|  |  Source Value    -->    Target Value                             |  |
|  |  "A"            -->    "active"                                 |  |
|  |  "D"            -->    "disabled"                               |  |
|  |  [+ Add Mapping]                                                |  |
|  |  Default: [human]                                               |  |
|  |                                                                 |  |
|  +----------------------------------------------------------------+  |
|                                                                      |
|  +--- Live Preview (first 5 rows) --------------------------------+  |
|  |  Source: userid | Extracted: jsmith -> "jsmith" (lowercase)     |  |
|  |  Source: status | Extracted: A -> "active" (value_map)          |  |
|  |  Source: lastlogin | Extracted: 01/15/2026 10:30:00 -> 2026-.. |  |
|  +----------------------------------------------------------------+  |
|                                                                      |
|  [Test Extraction]  [Save Template]                                  |
+----------------------------------------------------------------------+
```

**Mapping Editor Features:**
- **Split Pane**: Source fields on left, target schema on right. Visual connection lines between mapped fields
- **Color Coding**: Green lines = direct mapping. Yellow lines ([T]) = transformation applied. Gray = unmapped target fields
- **Completeness Meter**: Percentage of target fields mapped. Required fields highlighted if unmapped
- **Transformation Editor**: Appears when clicking a mapped connection. Shows transform type dropdown and configuration. Live preview of transform result
- **Detection Rules**: Separate tab/section for configuring how this template is detected
- **Validation Rules**: Separate tab/section for configuring field validation
- **Test Extraction**: Upload a sample file and preview full extraction result in tabular format
- **Accessible Alternative**: Table-based mapping view alongside the visual editor. ARIA: `role="grid"` with rows representing each mapping. Columns: Source Field, Transform, Target Field, Status. Screen reader reads "userid mapped to identifier via lowercase transform, mapped."

**9.4.8 Reference Data Management**

```
+--------------------------------------------------------------------+
|  Reference Data Library                            [Upload Dataset]  |
|                                                                      |
|  +--- Dataset List ------------------------------------------------+|
|  |                                                                  ||
|  |  Name             Type          Source    Records  Uploaded      ||
|  |  ---------------------------------------------------------------||
|  |  HR Employees     hr_employees  Workday   450     Jan 15, 2026  ||
|  |    Freshness: [GREEN - 26 days old]                             ||
|  |                                                                  ||
|  |  IT Contractors   vendor_list   Manual    23      Dec 01, 2025  ||
|  |    Freshness: [RED - 71 days old - STALE]                       ||
|  |                                                                  ||
|  |  Department List  departments   Workday   35      Feb 01, 2026  ||
|  |    Freshness: [GREEN - 9 days old]                              ||
|  |                                                                  ||
|  +------------------------------------------------------------------+|
|                                                                      |
|  +--- Dataset Detail (selected: HR Employees) ---------------------+|
|  |                                                                  ||
|  |  Name: HR Active Employees                                      ||
|  |  Data Type: hr_employees    Source System: Workday               ||
|  |  Freshness Threshold: 30 days   Record Count: 450               ||
|  |  Upload Date: Jan 15, 2026  File Hash: a3f2b7c...              ||
|  |                                                                  ||
|  |  -- Sample Records (first 5) --                                 ||
|  |  ID       Name           Email              Dept      Status    ||
|  |  E001     John Doe       jdoe@bank.com      IT        Active   ||
|  |  E002     Jane Smith     jsmith@bank.com    Ops       Active   ||
|  |  ...                                                            ||
|  |                                                                  ||
|  |  -- Used In Reviews --                                          ||
|  |  Fedlink Anywhere UAR Q4 2025 (approved)                       ||
|  |  JH Silverlake UAR Q4 2025 (approved)                          ||
|  |                                                                  ||
|  |  [Replace Dataset]  [Download]  [Deactivate]                   ||
|  +------------------------------------------------------------------+|
+----------------------------------------------------------------------+
```

**Reference Data Features:**
- Dataset list with freshness indicators: green (within threshold), amber (approaching threshold), red with "STALE" label (past threshold)
- Upload wizard: file upload, template selection/creation, extraction preview, confirmation
- Dataset detail: metadata, sample records table, usage history (which reviews used this version)
- Freshness alert banner when dataset exceeds threshold
- "Replace Dataset" preserves version history and audit trail

**9.4.9 Review Creation Wizard**

Wizard-style flow for creating a new review (5 steps):

```
Step 1: Select Application
  -> Dropdown/card list of active applications
  -> Shows last review date and next due date

Step 2: Select Framework
  -> Dropdown of compatible frameworks (matching review_type)
  -> Shows version, check count, last used date

Step 3: Review Period
  -> Start date and end date pickers
  -> Auto-suggest based on application review_schedule
  -> Optional: link to previous review for comparison
  -> Due date field

Step 4: Upload Documents
  -> Drag-and-drop file upload zone
  -> Upload primary application export
  -> Upload supplementary documents
  -> Select reference datasets from library (e.g., HR employee list)
  -> Shows upload status and file hashes
  -> File drop zone: border changes to blue dashed on drag-over,
     "Drop file here" text, accept/reject animation on drop
     (green flash for valid, red shake for invalid)

Step 5: Review Summary
  -> Application name, framework version, period, documents uploaded
  -> Assigned reviewer field
  -> [Create Review] button
  -> Review enters CREATED state, auto-transitions to DOCUMENTS_UPLOADED
```

ARIA: Announce current step on each transition ("Step 3 of 5: Review Period"). Move focus to heading or first field of new step.

**9.4.10 Low-Confidence Extraction Review**

Displayed when extraction confidence falls below the configured threshold (default 95%):

```
+--------------------------------------------------------------------+
|  [WARNING] Extraction Confidence Below Threshold                     |
|  Confidence: 0.82 (threshold: 0.95)                                 |
|                                                                      |
|  +--- Field-by-Field Review ---------------------------------------+|
|  |                                                                  ||
|  |  Row  Source Column  Source Value    Extracted Value  Confidence ||
|  |  ---------------------------------------------------------------||
|  |  12   lastlogin      "Jan 15 26"    2026-01-15       0.70 LOW  ||
|  |       [Edit extracted value: ________]                          ||
|  |                                                                  ||
|  |  45   status          "Suspended"    ???              0.40 LOW  ||
|  |       Unmapped value. Select target: [active|inactive|disabled] ||
|  |                                                                  ||
|  |  89   authgroup       "ADM;FIN;OPS"  ["ADM","FIN"]   0.65 LOW  ||
|  |       Possible truncation. [Edit extracted value: ________]     ||
|  |                                                                  ||
|  +------------------------------------------------------------------+|
|                                                                      |
|  Low-confidence fields: 3 of 847 records                             |
|  [Accept As-Is]  [Correct and Re-extract]  [Reject Upload]          |
+----------------------------------------------------------------------+
```

**Low-Confidence Behavior:**
- Side-by-side comparison of source column values vs. extracted values for flagged fields
- Per-field confidence indicator (high/medium/low)
- Inline editing of individual extracted values
- "Accept As-Is" proceeds with current extraction (logged as acknowledged low-confidence)
- "Correct and Re-extract" applies corrections and re-runs extraction
- "Reject Upload" returns to document upload step

**9.4.11 User Management**

```
+--------------------------------------------------------------------+
|  User Management                              [Generate Invite Code] |
|                                                                      |
|  +--- Pending Invites ---------------------------------------------+|
|  |  Code          Email (if restricted)  Role      Expires         ||
|  |  ---------------------------------------------------------------||
|  |  INV-A3F2      jdoe@bank.com         analyst   Feb 15, 2026    ||
|  |  INV-8D4E      (any)                 reviewer  Feb 20, 2026    ||
|  |  [Copy Code] [Revoke]                                          ||
|  +------------------------------------------------------------------+|
|                                                                      |
|  +--- User List ---------------------------------------------------+|
|  |                                                                  ||
|  |  Name          Email              Role       Status  Last Login ||
|  |  ---------------------------------------------------------------||
|  |  Josh Lopez    josh@bank.com      admin      Active  Today     ||
|  |  Maria Chen    maria@bank.com     reviewer   Active  Yesterday ||
|  |  Bob Wilson    bob@bank.com       analyst    Active  Feb 01    ||
|  |  Sam Taylor    sam@bank.com       auditor    Inactive  --      ||
|  |                                                                  ||
|  |  Actions: [Edit Role] [Deactivate/Reactivate] [Reset Password] ||
|  +------------------------------------------------------------------+|
+----------------------------------------------------------------------+
```

**9.4.12 Settings Page**

```
+--------------------------------------------------------------------+
|  Settings                                                            |
|                                                                      |
|  +--- Tabs --------------------------------------------------------+|
|  |  [System Settings] [My Preferences]                              ||
|  +------------------------------------------------------------------+|
|                                                                      |
|  +--- System Settings (admin only) --------------------------------+|
|  |                                                                  ||
|  |  Session & Security:                                            ||
|  |    Session Timeout:       [30] minutes                          ||
|  |    Max Concurrent Sessions: [3]                                 ||
|  |    Password Min Length:   [16] characters                       ||
|  |                                                                  ||
|  |  AI Enrichment:                                                 ||
|  |    Global Enable:         [check] Enabled                       ||
|  |    Model:                 [GPT-4o]                              ||
|  |    Temperature:           [0.2]                                 ||
|  |    Default Confidence Threshold: [0.95]                         ||
|  |                                                                  ||
|  |  Extraction Defaults:                                           ||
|  |    Confidence Threshold:  [0.95]                                ||
|  |    Max File Size:         [50] MB                               ||
|  |                                                                  ||
|  |  [Save Settings]                                                ||
|  +------------------------------------------------------------------+|
|                                                                      |
|  +--- My Preferences (all users) ----------------------------------+|
|  |                                                                  ||
|  |  Notifications:                                                 ||
|  |    [check] Email when review assigned to me                     ||
|  |    [check] Email when review is overdue                         ||
|  |    [check] Email when review approved/rejected                  ||
|  |    [ ] Email on new findings                                    ||
|  |                                                                  ||
|  |  Display:                                                       ||
|  |    Timezone: [America/New_York]                                 ||
|  |                                                                  ||
|  |  Password:                                                      ||
|  |    [Change Password]                                            ||
|  |                                                                  ||
|  |  [Save Preferences]                                             ||
|  +------------------------------------------------------------------+|
+----------------------------------------------------------------------+
```

**9.4.13 Report Viewer / Archive**

```
+--------------------------------------------------------------------+
|  Reports                                                             |
|                                                                      |
|  +--- Tabs --------------------------------------------------------+|
|  |  [Generate Report] [Report Archive]                              ||
|  +------------------------------------------------------------------+|
|                                                                      |
|  +--- Generate Report Tab -----------------------------------------+|
|  |                                                                  ||
|  |  Report Type: [Executive Summary | Detailed Findings |          ||
|  |                Regulatory Package | Trend Analysis |            ||
|  |                Audit Trail Export]                               ||
|  |                                                                  ||
|  |  Application:  [Fedlink Anywhere]                               ||
|  |  Review:       [Q1 2026 UAR]                                    ||
|  |  Date Range:   [2026-01-01] to [2026-03-31]                    ||
|  |                                                                  ||
|  |  [Generate Report]                                              ||
|  |  Progress: [===========------] 65% Generating...                ||
|  +------------------------------------------------------------------+|
|                                                                      |
|  +--- Report Archive Tab ------------------------------------------+|
|  |                                                                  ||
|  |  [Filter: All Types] [Filter: All Applications]                 ||
|  |                                                                  ||
|  |  Report               Type        Generated    By       Size   ||
|  |  ---------------------------------------------------------------||
|  |  Fedlink Q1 2026      Executive   Feb 10       Josh     1.2MB  ||
|  |  Fedlink Q1 2026      Detailed    Feb 10       Josh     3.4MB  ||
|  |  JH Core Q4 2025      Regulatory  Jan 15       Maria    5.1MB  ||
|  |                                                                  ||
|  |  [Download] [Preview] [Bulk Download for Examiner Package]      ||
|  +------------------------------------------------------------------+|
+----------------------------------------------------------------------+
```

**9.4.14 Audit Log Viewer**

```
+--------------------------------------------------------------------+
|  Audit Log                                    [Export JSON] [Export CSV]|
|                                                                      |
|  +--- Filters ---------------------------------------------------+  |
|  |  Date Range: [2026-01-01] to [2026-02-05]                    |  |
|  |  Actor: [All]  Action: [All]  Entity: [All]                  |  |
|  |  [Apply Filters]                                              |  |
|  +----------------------------------------------------------------+  |
|                                                                      |
|  Hash Chain Status: [check] Verified (14,283 entries, no tampering)  |
|                                                                      |
|  +--- Log Entries ------------------------------------------------+  |
|  |                                                                 |  |
|  |  2026-02-05 14:30:22 UTC | Josh Lopez | EXECUTE                |  |
|  |  Entity: Review (abc-123) | Action: run_analysis               |  |
|  |  Framework: UAR Standard v1.0 | Records analyzed: 847          |  |
|  |  Hash: a3f2b7c... | Prev: 8d4e1f2...                         |  |
|  |                                                                 |  |
|  |  2026-02-05 14:28:15 UTC | Josh Lopez | CONFIRM                |  |
|  |  Entity: Extraction (def-456) | Action: confirm_extraction     |  |
|  |  Records: 847 valid, 5 warnings | Confidence: 0.96            |  |
|  |  Hash: 8d4e1f2... | Prev: 2c9a0b3...                         |  |
|  |                                                                 |  |
|  |  ...                                                            |  |
|  +----------------------------------------------------------------+  |
|                                                                      |
|  [Verify Hash Chain]  [Prev Page]  Page 1 of 47  [Next Page]        |
|  [Print]                                                             |
+----------------------------------------------------------------------+
```

#### 9.5 Interaction Patterns

**Wizard Pattern**: Used for multi-step creation flows (review creation, framework publishing). 5-7 steps maximum. Progress indicator at top. Validation before allowing next step. Save-as-draft capability at any step. Review/summary screen before final submission.

**Master-Detail Pattern**: Used for list-to-detail views (findings, applications, frameworks). Left panel shows filterable/sortable list. Right panel shows selected item detail. Mobile/tablet: list and detail are separate screens with navigation between them.

**Confirmation Pattern**: Used for destructive or irreversible actions.

| Action Type | Confirmation Level |
|-------------|-------------------|
| Extraction confirmation, review sign-off, framework publish, review deletion | Modal with checkbox acknowledgment |
| Delete document before extraction, remove reference dataset, deactivate user | Modal without checkbox |
| Save draft, add note, change sort/filter | No confirmation (inline action) |
| Finding disposition changes | Undo via toast within 10 seconds instead of pre-confirmation |

**Toast Notifications**: Success actions show brief green toast (auto-dismiss 3s). Error actions show persistent red toast with details. Warning actions show amber toast (auto-dismiss 5s). ARIA: Success toasts use `aria-live="polite"`, error toasts use `aria-live="assertive"`.

**Loading States**:
- Skeleton screens for initial page loads (matching the layout structure of the destination page)
- For operations over 5 seconds: dedicated progress panel with estimated time and progress detail
- Extraction: "Processing row X of Y"
- Analysis: "Running check X of Y: [check name]"
- AI enrichment: "Enriching finding X of Y"
- Allow navigation away with notification badge when complete
- Progress updates delivered via SSE (Server-Sent Events) -- see Section 11.3

**Empty States** (per-screen):
- Dashboard (first use): "Welcome to SAPv2. Get started by configuring your first application." with guided setup checklist
- Reviews (none): "No reviews yet. Create your first review to begin." with Create Review button
- Frameworks (none): "No frameworks created. Start with a pre-built template or create your own." with links to starter templates
- Applications (none): "No applications configured. Add your first application." with Add Application button
- Reference Data (none): "No reference datasets uploaded. Upload your HR employee list to enable cross-reference checks." with Upload button
- Findings (no findings for review): "No findings generated. Run analysis to identify findings." (contextual to review state)

**First-Time User Onboarding**:
- Detected on first login when user has no reviews and no applications
- Persistent setup checklist widget (dismissible, re-accessible from "?" icon):
  1. "Configure your first application" (links to Applications > Add New)
  2. "Set up a framework" (links to Frameworks > Create, with starter templates)
  3. "Upload a reference dataset" (links to Reference Data, explains cross-reference)
  4. "Create your first review" (links to Review wizard)
- Pre-loaded starter framework templates (from `backend/data/starters/`) available for one-click import

**Concurrent Edit Handling**:
- Optimistic concurrency via `updated_at` timestamp comparison on save (returns 409 Conflict if stale)
- "This review has been updated by [user] at [time]. Reload to see changes." banner on conflict
- Per-finding indicator: "[User] is reviewing this finding" (lightweight, advisory only)

**Print Stylesheet**:
- `@media print` stylesheet hides navigation, resizes content to full width, preserves severity colors/icons, ensures readable font sizes
- Explicit "Print" button on Review Workspace, Audit Log, and Report preview screens

#### 9.6 Accessibility Requirements

**Skip Navigation:**
- Visually-hidden "Skip to main content" link as the first focusable element on every page
- "Skip to findings" link on the Review Workspace page
- Links become visible on focus (standard pattern: `sr-only focus:not-sr-only`)

**Screen Reader Flows:**
- Dashboard: Announce compliance score as "Compliance score: 87 percent, up 3 percent from last quarter." Findings summary as "Open findings: 2 critical, 5 high, 12 medium, 3 low." Active reviews table with proper `<caption>`.
- Review Workspace: Announce review status on page load. Findings list as a listbox with severity and disposition status per item. Finding detail as a region with headings for each section (Explainability, AI Description, Disposition).
- Framework Builder: Check list as an ordered list. Condition builder rows as a table with column headers (Field, Operator, Value). Announce add/remove actions with live region.
- Wizard steps: Announce current step on each transition ("Step 3 of 5: Review Period").

**Focus Management:**
- Modal open: Move focus to the first focusable element. Trap focus within (Tab cycles within modal only).
- Modal close: Return focus to the element that triggered the modal.
- Wizard step change: Move focus to the heading or first field of the new step. Announce step change via `aria-live` region.
- Toast notifications: `aria-live="polite"` for success, `aria-live="assertive"` for errors.
- Dynamic content (finding detail panel): When a finding is selected, announce the finding name and severity, move focus to detail panel heading.

**ARIA Patterns for Custom Components:**
- **Mapping Editor**: `role="grid"` with rows for each mapping. Columns: Source Field, Transform, Target Field, Status. Alternative table-based fallback view alongside visual editor.
- **Condition Builder**: `role="list"` with `role="listitem"` for each row. Reorder uses `aria-grabbed` and `aria-dropeffect` for drag-and-drop, plus accessible up/down buttons.
- **Compliance Score Gauge**: `role="meter"` with `aria-valuenow`, `aria-valuemin="0"`, `aria-valuemax="100"`, `aria-label`.
- **Progress Stepper**: `role="list"` with each step as `role="listitem"`. Current step has `aria-current="step"`. Completed steps indicated by "completed" in `aria-label`.
- **Severity Badge**: `aria-label="Critical severity"` (includes icon meaning and text label).

**Keyboard Navigation for Data Tables:**
- Row navigation: Arrow keys to move between rows. Enter to select/open detail. Escape to deselect.
- Sort controls: Sortable column headers are buttons. Space/Enter to cycle sort direction. Announce sort change via `aria-live`.
- Filters: Tab to filter controls. Standard form interaction. Announce result count change after filter applied.
- Pagination: Tab to page controls. Previous/next as buttons. Announce current page and total.

**Touch Targets:**
- All clickable/tappable elements: minimum 44x44px touch target
- Disposition buttons (Approve/Revoke/Abstain): adequate spacing so touch targets do not overlap
- Small icon buttons (delete condition row, remove mapping): sufficient padding to meet 44px minimum

---

### 10. Non-Functional Requirements

#### 10.1 Performance

- **NFR-1.1**: Document extraction shall complete within 30 seconds for files up to 50,000 records
- **NFR-1.2**: Framework analysis shall complete within 60 seconds for datasets up to 50,000 records
- **NFR-1.3**: AI enrichment shall complete within 120 seconds for reviews with up to 50 findings
- **NFR-1.4**: Report generation shall complete within 60 seconds
- **NFR-1.5**: Dashboard shall load within 2 seconds
- **NFR-1.6**: Page navigation shall feel instant (<300ms) for cached data
- **NFR-1.7**: File upload shall show progress indicator for files > 5MB
- **NFR-1.8**: API queries shall enforce a 30-second statement timeout; background tasks shall enforce a 120-second statement timeout

#### 10.2 Security

- **NFR-2.1**: All data shall be encrypted at rest (AES-256) and in transit (TLS 1.2+)
- **NFR-2.2**: System shall enforce role-based access control (admin, analyst, reviewer, auditor roles)
- **NFR-2.3**: All user actions shall be logged in immutable hash-chained audit trail
- **NFR-2.4**: Source documents shall be stored with SHA-256 integrity verification
- **NFR-2.5**: AI processing shall use Azure OpenAI with BAA -- no data sent to consumer AI services
- **NFR-2.6**: Session timeout after 30 minutes of inactivity
- **NFR-2.7**: Password requirements: minimum 12 characters, complexity requirements per bank policy
- **NFR-2.8**: JWT tokens shall expire after 8 hours maximum

**CORS Configuration:**
- Allowed Origins: Configured per environment via `CORS_ORIGINS` environment variable
  - Development: `http://localhost:3000`, `http://localhost:5173`
  - Staging: `https://staging.sapv2.app`
  - Production: `https://app.sapv2.app` (or custom domain)
- Allowed Methods: GET, POST, PUT, DELETE, OPTIONS
- Allowed Headers: Authorization, Content-Type, X-Request-ID
- Credentials: true
- Max Age: 3600 seconds (preflight cache)
- No wildcard origins in production

**Input Validation Specifications:**

String Field Constraints:
- `name` fields: 1-255 characters, no control characters
- `description`/`context` fields: 0-5000 characters
- `notes` fields: 0-10000 characters
- `email` fields: valid email format per RFC 5322, max 255 characters
- Version labels: semantic version format (N.N.N)
- `check_id`: 1-100 characters, alphanumeric + underscore/hyphen only

JSONB Field Constraints:
- `checks` array: maximum 100 checks per framework
- `roles` array: maximum 50 roles per record
- `regulatory_mappings`: maximum 20 mappings per framework
- `settings` object: maximum 50 key-value pairs, values max 1000 characters

File Path Security:
- Uploaded files stored with UUID-based names, never user-supplied names
- File paths SHALL NOT contain "..", "~", or absolute paths
- Stored file paths are server-generated, never from client input

**File Upload Security:**

Size Limits:
- Maximum file size: 50MB per file
- Maximum files per review: 20
- Maximum total storage per review: 200MB

File Type Validation (defense in depth):
1. Extension check: `.csv`, `.xlsx`, `.xls`, `.json`, `.xml`, `.pdf` only
2. MIME type check: must match expected type for extension
3. Magic bytes check: verify file header matches claimed type
4. Content validation: attempt to parse as claimed type before accepting

Storage:
- Files stored outside web root in S3-compatible storage
- Files named by UUID, never by user-supplied filename
- Original filename stored in metadata only
- Files served through authenticated API endpoint, never direct URL

Content Security:
- CSV/Excel files: strip formulas (`=`, `+`, `-`, `@`) from cell values to prevent CSV injection
- PDF files: no JavaScript execution
- XML files: disable external entity processing (XXE prevention)

Virus Scanning (Phase 2+):
- ClamAV integration for uploaded file scanning
- Files quarantined until scan completes
- Scan results logged in audit trail

**API Authentication Flow:**

Token Strategy:
- Access token: JWT, 15-minute expiration, stored in memory (not localStorage)
- Refresh token: opaque token, 8-hour expiration, stored in httpOnly secure cookie
- Refresh token rotation: each refresh invalidates the previous token
- Token revocation: refresh tokens stored in database; logout deletes the record
- All active sessions per user tracked

Session Management:
- Maximum concurrent sessions per user: 3
- Session timeout: 30 minutes of API inactivity (server-side check)
- Password change: invalidates all refresh tokens for that user
- Admin deactivation: invalidates all tokens immediately

Token Payload (access token):
```json
{
  "sub": "user-uuid",
  "email": "user@bank.com",
  "role": "analyst",
  "iat": 1707134400,
  "exp": 1707135300
}
```

**Secret Management:**
- All secrets SHALL be stored as environment variables, never in code or config files
- Railway environment variables for production deployment
- `.env` file for local development (in `.gitignore`, never committed)
- JWT signing key: minimum 256-bit, rotatable without downtime
- Database credentials: separate read-only and read-write users
- Azure OpenAI API key: stored as environment variable, rotatable
- File encryption key (for at-rest encryption): separate from application secrets

Required Environment Variables:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: JWT signing key (min 64 hex chars)
- `AZURE_OPENAI_API_KEY`: Azure OpenAI API key (if AI provider = azure_openai)
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI endpoint URL
- `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET`: File storage credentials (if storage = s3)

**Request ID / Correlation Tracing:**
- Every API request SHALL be assigned a unique request_id (UUID v4)
- Request ID is included in:
  - Response header: `X-Request-ID`
  - All log entries generated during the request
  - Audit log entries created during the request (`request_id` column)
  - Error responses
- If client provides `X-Request-ID` header, server uses it (enables end-to-end tracing)
- Background tasks (Celery) inherit the request_id from the triggering API request

#### 10.3 Compliance & Regulatory-Grade Audit Trail

- **NFR-3.1**: System shall maintain audit trail for minimum 5 years (aligning with BSA requirements)
- **NFR-3.2**: System shall support export of all data for regulatory examination in JSON and CSV formats
- **NFR-3.3**: Framework versions shall be immutable once used in a review (is_immutable flag)
- **NFR-3.4**: Audit log entries shall be immutable (append-only, enforced by database triggers preventing UPDATE and DELETE)
- **NFR-3.5**: Each audit entry shall include:
  - Timestamp (UTC, millisecond precision)
  - Actor ID, actor type (USER, SYSTEM, RULE_ENGINE, AI_SERVICE)
  - Session ID
  - Request ID (correlation with API request)
  - Action type (create, read, update, delete, execute, confirm, approve, reject, login, logout)
  - Entity type and ID
  - Before/after state for mutations (JSONB)
  - SHA-256 hash of entry content
  - Hash of previous entry (blockchain-style chain)
- **NFR-3.6**: System shall detect and alert on audit log tampering via hash chain verification function
- **NFR-3.7**: Audit logs shall be exportable in standard formats (JSON, CSV) for examination
- **NFR-3.8**: Document uploads shall be stored with SHA-256 hash for integrity verification
- **NFR-3.9**: System shall log all AI model invocations in separate ai_invocations table with:
  - Model name and version
  - Input hash (not full content, for PII protection)
  - Output hash
  - Confidence score
  - Timestamp, duration, token counts
- **NFR-3.10**: Audit log table shall be partitioned by month for efficient long-term storage and archival
- **NFR-3.11**: Application database role shall have INSERT and SELECT only on audit tables -- never UPDATE or DELETE

#### 10.4 Reliability

- **NFR-4.1**: System shall provide 99.5% availability during business hours (M-F 7am-7pm ET)
- **NFR-4.2**: Data shall be backed up daily with 30-day retention
- **NFR-4.3**: System shall support disaster recovery with RPO of 24 hours
- **NFR-4.4**: Long-running operations (extraction, analysis, enrichment) shall be fault-tolerant with retry capability

**Health Check Endpoints:**

| Endpoint | Purpose | Auth Required |
|----------|---------|---------------|
| `GET /health` | Basic liveness check (process running) | No |
| `GET /health/ready` | Readiness check (all dependencies healthy) | No |

Readiness checks include:
- PostgreSQL connection: execute `SELECT 1`
- Redis connection: execute `PING`
- S3/file storage: verify bucket exists
- Celery worker: verify at least one worker responding (if applicable)

Response format:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 86400,
  "checks": {
    "database": { "status": "healthy", "latency_ms": 2 },
    "redis": { "status": "healthy", "latency_ms": 1 },
    "storage": { "status": "healthy" },
    "celery": { "status": "healthy", "workers": 2 }
  }
}
```

Railway health check: `GET /health` (TCP probe interval: 30s).

**Structured Logging:**
- All application logs SHALL use JSON format (configurable to plain text for local development)
- Log fields: `timestamp`, `level`, `message`, `request_id`, `user_id`, `module`, `duration_ms`
- Log levels: DEBUG (dev only), INFO (normal operations), WARNING (recoverable issues), ERROR (failures), CRITICAL (system-level failures)
- Sensitive data (passwords, tokens, PII) SHALL NOT appear in logs
- Log destination: stdout (for Railway log aggregation)

**Error Tracking (Sentry):**
- Sentry integration for automatic error capture and alerting in staging and production
- FastAPI and SQLAlchemy integrations enabled
- 10% trace sample rate for performance monitoring
- Release tagged with git commit SHA
- Environment tag for staging/production differentiation

**Connection Pooling:**

SQLAlchemy AsyncEngine Configuration:
- `pool_size`: 10 (per process)
- `max_overflow`: 5 (burst capacity)
- `pool_timeout`: 30 seconds
- `pool_recycle`: 1800 seconds (30 min, prevents stale connections)
- `pool_pre_ping`: True (verify connection before use)

Celery Worker Pool:
- Each worker: `pool_size=3`, `max_overflow=2`
- Worker concurrency: 4 (prefork)

Total connection budget (Railway PostgreSQL plan):
- API server: 15 connections
- Celery workers (2): 10 connections
- Alembic migrations: 1 connection
- Admin/monitoring: 2 connections
- Reserve: 2 connections
- Total: approximately 30 connections (verify against Railway plan limit)
- PgBouncer recommended if connection limits are exceeded

#### 10.5 Accessibility

- **NFR-5.1**: All UI shall meet WCAG 2.1 Level AA compliance
- **NFR-5.2**: Color shall never be the sole indicator of meaning (always paired with icons/text)
- **NFR-5.3**: All interactive elements shall have visible keyboard focus indicators (2px minimum)
- **NFR-5.4**: All images and icons shall have appropriate alt text or ARIA labels
- **NFR-5.5**: Minimum contrast ratio: 4.5:1 for normal text, 3:1 for large text (18px+) and UI components
- **NFR-5.6**: All modals shall trap focus and return focus to trigger element on close
- **NFR-5.7**: Skip navigation links shall be present on all pages
- **NFR-5.8**: All custom components shall implement appropriate ARIA patterns (see Section 9.6)
- **NFR-5.9**: System shall respect `prefers-reduced-motion` user preference
- **NFR-5.10**: All clickable/tappable elements shall have a minimum 44x44px touch target

---

### 11. Technical Architecture

#### 11.1 Technology Stack (Finalized)

**Frontend:**
- React 18+ with TypeScript (strict mode)
- Component library: shadcn/ui (built on Radix UI primitives)
- Styling: Tailwind CSS
- State management: React Query (TanStack Query) for server state, Zustand for client state
- Form handling: React Hook Form with Zod validation schemas
- Routing: React Router v6
- Charts: Recharts for compliance trend visualizations
- Table: TanStack Table for sortable/filterable data tables
- Date handling: date-fns
- File upload: react-dropzone
- Icons: Lucide Icons

**Backend:**
- Python 3.11+ with FastAPI
- PostgreSQL 15+ for primary data store (hybrid schema)
- Redis for caching and background job queues
- S3-compatible storage for documents (Railway volumes for POC, AWS S3 or Cloudflare R2 for production)
- Alembic for database migrations
- SQLAlchemy 2.0 for ORM with async support
- Pydantic v2 for request/response validation
- Celery for background task processing (extraction, analysis, enrichment)
- PgBouncer for connection pooling (if connection limits are exceeded)

**Rule Engine:**
- json-logic-qubit (Python JSON Logic implementation)
- Custom operator extensions for domain-specific conditions
- Rule definitions stored as JSON in framework.checks JSONB column

**AI Integration:**
- Azure OpenAI for AI enrichment functions
- Primary model: GPT-4o (or GPT-5.2 when available)
- Fallback: GPT-4o-mini for high-volume, low-complexity tasks
- Structured prompting with JSON output mode
- Temperature: 0.1-0.3 for factual content, 0.5 max for creative summaries
- All invocations logged to ai_invocations table
- Token usage tracked in ai_usage_log table for cost monitoring

**Document Processing:**
- pandas for CSV/Excel extraction and data transformation
- Camelot for PDF table extraction (primary -- provides accuracy scoring)
- pdfplumber for PDF fallback
- openpyxl for Excel read/write
- python-docx for Word documents (future)

**Observability:**
- Structured JSON logging to stdout (for Railway log aggregation)
- Sentry for error tracking and performance monitoring
- Request ID middleware for end-to-end tracing
- Health check endpoints for deployment monitoring

**Infrastructure:**
- Containerized deployment (Docker)
- Railway for POC hosting
- GitHub Actions for CI/CD
- Docker Compose for local development
- CDN (Cloudflare) for frontend static assets in production

#### 11.2 Project Structure

```
sapv2/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── auth.py
│   │   │   │   ├── frameworks.py
│   │   │   │   ├── applications.py
│   │   │   │   ├── reviews.py
│   │   │   │   ├── documents.py
│   │   │   │   ├── findings.py
│   │   │   │   ├── reference_data.py
│   │   │   │   ├── reports.py
│   │   │   │   ├── users.py
│   │   │   │   ├── settings.py
│   │   │   │   └── audit.py
│   │   │   └── deps.py          # Dependency injection (auth, db session)
│   │   ├── core/
│   │   │   ├── config.py        # Environment config (Pydantic Settings)
│   │   │   ├── security.py      # JWT, password hashing, RBAC
│   │   │   ├── audit.py         # Audit logging with hash chaining
│   │   │   ├── logging.py       # Structured JSON logging setup
│   │   │   ├── middleware.py     # Request ID middleware
│   │   │   └── exceptions.py    # Custom exception classes
│   │   ├── services/
│   │   │   ├── extraction/
│   │   │   │   ├── csv_extractor.py
│   │   │   │   ├── excel_extractor.py
│   │   │   │   ├── pdf_extractor.py     # Camelot + pdfplumber
│   │   │   │   ├── template_matcher.py  # Confidence-scored matching
│   │   │   │   ├── transformer.py       # Value transforms (date, map, etc.)
│   │   │   │   └── validator.py         # Extraction validation
│   │   │   ├── analysis/
│   │   │   │   ├── rule_engine.py       # JSON Logic execution
│   │   │   │   ├── condition_evaluator.py  # Custom operators
│   │   │   │   ├── cross_reference.py   # Cross-dataset matching
│   │   │   │   ├── severity_resolver.py # Conditional severity evaluation
│   │   │   │   └── explainability.py    # Template-driven explanations
│   │   │   ├── ai/
│   │   │   │   ├── azure_client.py      # Azure OpenAI client wrapper
│   │   │   │   ├── prompts.py           # Structured prompt templates
│   │   │   │   ├── mapping_assistant.py # AI template mapping proposals
│   │   │   │   ├── enrichment.py        # Finding descriptions, remediation
│   │   │   │   └── confidence.py        # Confidence scoring
│   │   │   ├── storage/
│   │   │   │   ├── local.py             # Local filesystem storage
│   │   │   │   └── s3.py               # S3-compatible object storage
│   │   │   ├── reporting/
│   │   │   │   ├── pdf_generator.py     # PDF report generation
│   │   │   │   └── templates/           # Report templates
│   │   │   └── audit_service.py         # Audit log business logic
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── invite.py
│   │   │   ├── framework.py
│   │   │   ├── application.py
│   │   │   ├── document_template.py
│   │   │   ├── review.py
│   │   │   ├── review_comment.py
│   │   │   ├── document.py
│   │   │   ├── extraction.py
│   │   │   ├── extracted_record.py
│   │   │   ├── reference_dataset.py
│   │   │   ├── finding.py
│   │   │   ├── audit_log.py
│   │   │   ├── ai_invocation.py
│   │   │   ├── ai_usage_log.py
│   │   │   └── notification_preference.py
│   │   ├── schemas/               # Pydantic request/response schemas
│   │   │   ├── auth.py
│   │   │   ├── framework.py
│   │   │   ├── application.py
│   │   │   ├── review.py
│   │   │   ├── document.py
│   │   │   ├── finding.py
│   │   │   ├── user.py
│   │   │   ├── settings.py
│   │   │   └── audit.py
│   │   ├── tasks/                 # Celery background tasks
│   │   │   ├── extraction_task.py
│   │   │   ├── analysis_task.py
│   │   │   └── enrichment_task.py
│   │   └── main.py
│   ├── tests/
│   │   ├── test_extraction/
│   │   ├── test_analysis/
│   │   ├── test_audit/
│   │   └── test_api/
│   ├── alembic/
│   │   └── versions/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── celery_worker.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/               # shadcn/ui components
│   │   │   ├── layout/           # Sidebar, header, page layout
│   │   │   ├── dashboard/        # Dashboard widgets
│   │   │   ├── reviews/          # Review workspace components
│   │   │   ├── frameworks/       # Framework builder components
│   │   │   ├── applications/     # Application config components
│   │   │   ├── findings/         # Finding list/detail components
│   │   │   ├── mapping/          # Document mapping editor
│   │   │   ├── extraction/       # Extraction confirmation components
│   │   │   ├── reference/        # Reference data management
│   │   │   ├── reports/          # Report viewer/archive
│   │   │   ├── users/            # User management components
│   │   │   ├── settings/         # Settings page components
│   │   │   ├── auth/             # Login, registration, password
│   │   │   ├── audit/            # Audit log viewer
│   │   │   └── shared/           # Severity badges, status badges, error boundaries
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Reviews.tsx
│   │   │   ├── ReviewWorkspace.tsx
│   │   │   ├── CreateReview.tsx
│   │   │   ├── Frameworks.tsx
│   │   │   ├── FrameworkBuilder.tsx
│   │   │   ├── Applications.tsx
│   │   │   ├── ApplicationConfig.tsx
│   │   │   ├── ReferenceData.tsx
│   │   │   ├── Reports.tsx
│   │   │   ├── AuditLog.tsx
│   │   │   ├── Users.tsx
│   │   │   ├── Settings.tsx
│   │   │   ├── Login.tsx
│   │   │   ├── Register.tsx
│   │   │   └── NotFound.tsx
│   │   ├── hooks/
│   │   │   ├── useReviews.ts     # React Query hooks for reviews
│   │   │   ├── useFrameworks.ts
│   │   │   ├── useApplications.ts
│   │   │   ├── useFindings.ts
│   │   │   ├── useAudit.ts
│   │   │   ├── useAuth.ts
│   │   │   ├── useUsers.ts
│   │   │   ├── useSettings.ts
│   │   │   ├── useEventSource.ts # SSE hook for real-time updates
│   │   │   └── useKeyboardShortcuts.ts
│   │   ├── lib/
│   │   │   ├── api.ts            # API client (fetch wrapper)
│   │   │   ├── auth.ts           # Auth context/provider
│   │   │   ├── constants.ts      # Severity colors, status maps, etc.
│   │   │   ├── types.ts          # TypeScript type definitions
│   │   │   └── utils.ts          # Formatters, helpers
│   │   ├── stores/
│   │   │   └── uiStore.ts        # Zustand store for UI state
│   │   └── App.tsx
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── vite.config.ts
│   └── Dockerfile
├── docker-compose.yml
├── docker-compose.dev.yml
├── railway.toml
├── .github/
│   └── workflows/
│       ├── test.yml
│       └── deploy.yml
└── README.md
```

#### 11.3 Real-Time Update Architecture (SSE)

Long-running operations (extraction, analysis, AI enrichment) deliver progress updates to the frontend via Server-Sent Events (SSE). SSE is simpler than WebSocket and sufficient for one-directional server-to-client updates.

**SSE Endpoint:**
- `GET /api/reviews/{id}/progress` -- SSE stream for review-related task progress

**Event Types:**
- `extraction_progress`: stage, current row, total rows, percentage
- `analysis_progress`: stage, current check, total checks, percentage
- `enrichment_progress`: stage, current finding, total findings, percentage
- `task_complete`: task type, result summary
- `task_error`: task type, error message, retry available

**Frontend Integration:**
- `useEventSource` hook wrapping the EventSource API with auto-reconnect
- Fallback: polling every 5 seconds if SSE connection fails or is unavailable

**State Management Integration:**
- SSE events update React Query cache via `queryClient.setQueryData`
- Optimistic updates for finding dispositions: update UI immediately, show "Saving..." indicator, revert on error with toast and retry option
- Non-optimistic operations (extraction confirmation, analysis execution, AI enrichment, framework publishing): wait for server confirmation before UI update

**Offline Behavior:**
- Persistent "You are offline" banner when connectivity is lost
- Disposition actions queued locally in Zustand store and replayed on reconnection
- Server-requiring actions (extraction, analysis, upload) disabled while offline
- "Reconnected -- syncing changes" banner on reconnection
- Conflict resolution UI if sync detects stale data

**Error Boundary Strategy:**
- Root error boundary: Catches catastrophic errors. Shows "Something went wrong" with "Reload Application" button. Logs error to backend.
- Route-level error boundary: Per-page error handling. Shows "This page encountered an error" with "Go to Dashboard" link. Other navigation still works.
- Component-level error boundary: For complex widgets (chart, table, mapping editor). Shows "Unable to load [component name]" with "Retry" button.

#### 11.4 Monitoring and Observability

**Structured Logging Setup:**

All backend services use structured JSON logging for machine-parseable output:
- JSON format in staging/production, plain text format available for local development
- Fields: `timestamp`, `level`, `logger`, `message`, `module`, `function`, `line`, `request_id`, `user_id`
- Exception stack traces included when present
- Sensitive data never logged (passwords, tokens, PII, file contents)
- Log destination: stdout (Railway aggregates from stdout)

**Request ID Middleware:**

Every API request is assigned a unique request ID (UUID v4) via middleware:
- If client provides `X-Request-ID` header, the server uses it
- Request ID is set on `request.state.request_id` for access in route handlers
- Request ID is included in the `X-Request-ID` response header
- All log entries and audit log entries include the request ID
- Celery tasks inherit the originating request ID

**Error Tracking (Sentry):**

Sentry integration for production error capture:
- FastAPI integration with endpoint-level transaction tracking
- SQLAlchemy integration for database query tracing
- 10% trace sample rate for performance monitoring
- Release tagged with `RAILWAY_GIT_COMMIT_SHA`
- Environment tag for staging/production

**Application Metrics (Phase 2+):**
- API request count and latency by endpoint (p50, p95, p99)
- Background task queue depth and processing time
- AI invocation count, latency, and error rate
- Active user sessions
- Database connection pool utilization
- File storage usage

**Alerting Thresholds:**
- API error rate > 5%: WARNING
- API p95 latency > 2s: WARNING
- Background task failure rate > 10%: CRITICAL
- Database connection pool exhaustion: CRITICAL
- Audit hash chain verification failure: CRITICAL (immediate notification)

#### 11.5 Database Backup Strategy

**Railway PostgreSQL Built-in Backups:**
- Automatic daily backups with 7-day retention (Pro plan)
- Point-in-time recovery within retention window
- Manual snapshot via Railway dashboard before major migrations

**Pre-Migration Backup Workflow:**
1. Before deploying schema-breaking migrations, trigger a manual Railway snapshot
2. Deploy the migration
3. If migration fails, restore from snapshot
4. Keep the snapshot for 30 days as a recovery point

**Audit Log Archival:**
- New monthly partition created automatically on the 1st of each month
- Partitions older than 24 months: exported to cold storage (compressed Parquet, S3)
- Archival process: verify hash chain integrity, export, upload with encryption, verify uploaded file
- Hot partitions (last 24 months) remain in PostgreSQL for direct queries
- "Include archived" parameter on audit API triggers async query against cold storage

#### 11.6 Scaling Strategy

| Component | Initial (POC) | Growth | Scaling Trigger |
|-----------|---------------|--------|-----------------|
| API | 1 instance, 2 workers | 2-4 instances | p95 response time > 500ms |
| Worker | 1 instance, 2 concurrency | 2+ instances | Queue depth > 100 tasks |
| PostgreSQL | Railway Starter (1 GB) | Railway Pro (8 GB+) | Connection saturation > 80% |
| Redis | Railway Starter (256 MB) | Railway Pro (1 GB+) | Memory > 80% |
| Frontend | 1 static instance | CDN | Global distribution needed |

**Connection Pooling Escalation:**
- Start with SQLAlchemy built-in pooling (pool_size=10, max_overflow=5)
- If connection limits are exceeded, add PgBouncer as a connection multiplexer between application and PostgreSQL
- PgBouncer transaction-mode pooling allows many application connections to share fewer database connections

**Container Security:**
- All containers run as non-root user (`appuser`)
- Minimal base images (`python:3.11-slim`, `node:20-alpine`, `nginx:1.27-alpine`)
- Multi-stage builds to exclude build tools from runtime images
- No secrets baked into images -- all injected via environment variables
- `HEALTHCHECK` directives ensure unhealthy containers are restarted

**CDN for Frontend:**
- Cloudflare CDN in front of Railway for static asset distribution
- Aggressive caching for `/assets/` (1 year, immutable content-hashed filenames)
- SPA fallback routing handled by nginx or Cloudflare Page Rules
- Security headers (X-Frame-Options, X-Content-Type-Options, Referrer-Policy) enforced at CDN edge

**File Storage Architecture:**

Storage Organization:
```
/documents/{review_id}/{document_uuid}.{ext}       -- Review documents
/reference/{dataset_uuid}/{file_uuid}.{ext}         -- Reference datasets
/reports/{review_id}/{report_uuid}.pdf              -- Generated reports
/temp/{upload_uuid}.{ext}                           -- Temporary uploads (TTL: 24h)
```

Lifecycle Management:
- Temporary uploads: delete after 24 hours if not associated with a review
- Documents for closed reviews: retain for 5 years (regulatory requirement)
- Documents for deleted/cancelled reviews: retain for 90 days, then delete
- Generated reports: retain for 1 year, regenerable on demand

Storage Backend Configuration:
- Local filesystem for development (`STORAGE_BACKEND=local`)
- S3-compatible object storage for production (`STORAGE_BACKEND=s3`)
- Backend abstraction supports both via storage service interface
- At-rest encryption: S3 server-side encryption (SSE-S3 or SSE-KMS)
- In-transit: TLS 1.2+ for all S3 API calls

---
### 12. API Contract (Phase 1)

All endpoints use the `/api/v1/` URL prefix. The API follows REST conventions with consistent error handling, pagination, rate limiting, and versioning as specified below.

#### 12.1 API Versioning Strategy

All API endpoints SHALL use URL-based versioning:
- Current version: `/api/v1/`
- Version is part of the URL path; clients may optionally send `Accept-Version: v1` header for explicitness
- Breaking changes require a new version number (e.g., `/api/v2/`)
- Previous versions supported for minimum 6 months after deprecation notice
- Deprecation communicated via `Sunset` and `Deprecation` response headers on affected endpoints

Phase 1 establishes `/api/v1/` for all endpoints. Future phases add backwards-compatible endpoints under `/api/v1/` or introduce `/api/v2/` for breaking changes.

#### 12.2 Standard Error Response Schema

All API errors SHALL return a consistent JSON envelope:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Framework name is required",
    "details": [
      {"field": "name", "message": "This field is required"},
      {"field": "version_major", "message": "Must be >= 1"}
    ],
    "request_id": "req_abc123def456"
  }
}
```

**Standard HTTP Status Codes:**

| Code | Meaning | When Used |
|------|---------|-----------|
| 400 | Bad Request | Validation errors, malformed input |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient role/permissions |
| 404 | Not Found | Resource does not exist |
| 409 | Conflict | State transition violation, duplicate resource |
| 413 | Payload Too Large | File upload exceeds limit |
| 422 | Unprocessable Entity | Valid JSON but semantic errors |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server error |

**Machine-Readable Error Codes:**

| Code | Description |
|------|-------------|
| `AUTH_INVALID_CREDENTIALS` | Login with wrong email or password |
| `AUTH_TOKEN_EXPIRED` | Access or refresh token has expired |
| `AUTH_INSUFFICIENT_ROLE` | User role does not permit this action |
| `VALIDATION_ERROR` | One or more fields failed validation |
| `RESOURCE_NOT_FOUND` | Requested entity does not exist |
| `STATE_TRANSITION_INVALID` | Review or framework state does not allow this action |
| `FRAMEWORK_IMMUTABLE` | Attempted to modify a published framework |
| `EXTRACTION_NOT_CONFIRMED` | Analysis attempted before extraction confirmation |
| `FILE_FORMAT_UNSUPPORTED` | Uploaded file type not in allowed list |
| `FILE_TOO_LARGE` | Uploaded file exceeds maximum size |
| `RATE_LIMIT_EXCEEDED` | Too many requests in the current window |
| `HASH_CHAIN_INTEGRITY_FAILURE` | Audit log hash chain verification failed |
| `CONCURRENT_EDIT_CONFLICT` | Another user modified the resource since last read |
| `REVIEW_SLA_BREACHED` | Review has exceeded its SLA timer |

#### 12.3 Pagination Specification

All list endpoints SHALL support cursor-based pagination with a consistent response envelope:

**Query Parameters:**
- `limit`: integer (default: 50, max: 200)
- `cursor`: string (opaque, base64-encoded cursor token; omit for first page)
- `sort_by`: string (field name; default varies by endpoint)
- `sort_order`: `"asc"` | `"desc"` (default: `"desc"`)

**Response Envelope:**

```json
{
  "items": [...],
  "next_cursor": "eyJpZCI6ImFiYy0xMjMifQ==",
  "has_more": true,
  "total": 1247
}
```

**Paginated Endpoints and Default Sort:**

| Endpoint | Default Sort |
|----------|-------------|
| `GET /api/v1/reviews` | `created_at desc` |
| `GET /api/v1/reviews/{id}/findings` | `severity desc, check_id asc` |
| `GET /api/v1/reviews/{id}/findings/{fid}/records` | `record_index asc` |
| `GET /api/v1/audit` | `timestamp desc` |
| `GET /api/v1/reference-datasets/{id}/records` | `record_index asc` |
| `GET /api/v1/frameworks` | `created_at desc` |
| `GET /api/v1/applications` | `name asc` |
| `GET /api/v1/users` | `created_at desc` |

#### 12.4 Rate Limiting

All API endpoints SHALL enforce rate limits per authenticated user:

| Endpoint Category | Rate Limit | Window |
|-------------------|-----------|--------|
| Authentication (login, register) | 10 requests | 1 minute |
| Read operations (GET) | 300 requests | 1 minute |
| Write operations (POST/PUT/DELETE) | 60 requests | 1 minute |
| File uploads | 10 requests | 1 minute |
| AI enrichment | 20 requests | 5 minutes |
| Report generation | 5 requests | 5 minutes |
| Audit export | 2 requests | 5 minutes |

**Rate Limit Response Headers (included in all responses):**

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Maximum requests allowed in current window |
| `X-RateLimit-Remaining` | Requests remaining in current window |
| `X-RateLimit-Reset` | Unix timestamp when the window resets |

Exceeded rate limits return HTTP 429 with a `Retry-After` header indicating seconds until the next available request.

#### 12.5 Health Check Endpoints

```
GET  /health                  - Liveness probe (200 if process is running)
GET  /health/ready            - Readiness probe (200 if all dependencies healthy)
```

These endpoints do NOT require authentication. Railway health check uses `GET /health` with a 30-second probe interval.

**Readiness response:**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 86400,
  "checks": {
    "database": {"status": "healthy", "latency_ms": 2},
    "redis": {"status": "healthy", "latency_ms": 1},
    "storage": {"status": "healthy"},
    "celery": {"status": "healthy", "workers": 2}
  }
}
```

Status values: `healthy`, `degraded` (non-critical dependency down), `unhealthy` (critical dependency down, returns 503).

#### 12.6 Authentication

```
POST /api/v1/auth/register         - Create account (invite code required)
POST /api/v1/auth/login            - Get JWT token pair (access + refresh)
POST /api/v1/auth/logout           - Invalidate refresh token
POST /api/v1/auth/refresh          - Refresh access token
GET  /api/v1/auth/me               - Get current user profile
POST /api/v1/auth/password-reset   - Request password reset email
POST /api/v1/auth/password-reset/confirm - Reset password with token
```

#### 12.7 User Management (Admin)

```
GET    /api/v1/users                     - List all users (admin only, paginated)
GET    /api/v1/users/{id}                - Get user details
PUT    /api/v1/users/{id}                - Update user profile
PATCH  /api/v1/users/{id}/role           - Change user role (admin only)
PUT    /api/v1/users/{id}/deactivate     - Deactivate user account (admin only)
PUT    /api/v1/users/{id}/reactivate     - Reactivate user account (admin only)
POST   /api/v1/invites                   - Create invite code (admin only)
GET    /api/v1/invites                   - List invite codes and their status
DELETE /api/v1/invites/{id}              - Revoke invite code
```

#### 12.8 Settings (Admin)

```
GET    /api/v1/settings                  - Get system settings
PUT    /api/v1/settings                  - Update system settings
GET    /api/v1/settings/ai               - Get AI provider configuration
PUT    /api/v1/settings/ai               - Update AI provider settings
```

System settings include: session timeout, default confidence thresholds, SLA timer defaults, notification preferences, organization profile (name, logo, timezone).

#### 12.9 AI Provider

```
GET    /api/v1/ai/providers              - List available AI providers and current selection
GET    /api/v1/ai/usage                  - Get AI token usage and cost tracking (current period)
GET    /api/v1/ai/usage/history          - Get AI usage history (paginated, filterable by date range)
```

#### 12.10 Frameworks

```
GET    /api/v1/frameworks                    - List all frameworks (filterable by review_type, status)
POST   /api/v1/frameworks                    - Create framework (draft)
GET    /api/v1/frameworks/{id}               - Get framework with checks
PUT    /api/v1/frameworks/{id}               - Update framework (draft only)
DELETE /api/v1/frameworks/{id}               - Soft delete framework
POST   /api/v1/frameworks/{id}/publish       - Publish version (makes immutable)
POST   /api/v1/frameworks/{id}/deprecate     - Mark framework as deprecated
POST   /api/v1/frameworks/{id}/archive       - Archive framework (no longer usable for new reviews)
POST   /api/v1/frameworks/{id}/clone         - Clone framework as new draft
GET    /api/v1/frameworks/{id}/versions      - List framework version history
POST   /api/v1/frameworks/{id}/test          - Dry-run checks against sample data
POST   /api/v1/frameworks/import             - Import framework from JSON package
POST   /api/v1/frameworks/{id}/export        - Export framework as portable JSON package
```

#### 12.11 Applications

```
GET    /api/v1/applications                          - List all applications
POST   /api/v1/applications                          - Create application
GET    /api/v1/applications/{id}                     - Get application with templates
PUT    /api/v1/applications/{id}                     - Update application
DELETE /api/v1/applications/{id}                     - Soft delete application
POST   /api/v1/applications/{id}/templates           - Add document template
PUT    /api/v1/applications/{id}/templates/{tid}     - Update template
DELETE /api/v1/applications/{id}/templates/{tid}     - Remove template
POST   /api/v1/applications/{id}/templates/{tid}/test - Test template against uploaded file
GET    /api/v1/applications/{id}/reviews             - List reviews for application
```

#### 12.12 Reference Datasets

```
GET    /api/v1/reference-datasets              - List all reference datasets
POST   /api/v1/reference-datasets              - Upload new reference dataset
GET    /api/v1/reference-datasets/{id}         - Get dataset metadata and sample records
DELETE /api/v1/reference-datasets/{id}         - Remove reference dataset
GET    /api/v1/reference-datasets/{id}/records - Get dataset records (paginated)
```

#### 12.13 Reviews

```
GET    /api/v1/reviews                         - List reviews (filterable by status, application, date)
POST   /api/v1/reviews                         - Create review (assign framework + application)
GET    /api/v1/reviews/{id}                    - Get review with current state
PUT    /api/v1/reviews/{id}                    - Update review metadata
PUT    /api/v1/reviews/{id}/status             - Transition review status
POST   /api/v1/reviews/{id}/cancel             - Cancel review (requires reason; admin approval if past ANALYZED)
DELETE /api/v1/reviews/{id}                    - Delete review (only if status=created)
GET    /api/v1/reviews/{id}/comparison         - Get comparison with previous review
GET    /api/v1/reviews/{id}/progress           - Get progress of current long-running operation
GET    /api/v1/reviews/{id}/tasks              - List background tasks for this review
```

#### 12.14 Documents

```
POST   /api/v1/reviews/{id}/documents                      - Upload document
GET    /api/v1/reviews/{id}/documents                      - List documents
DELETE /api/v1/reviews/{id}/documents/{did}                - Remove document (before extraction)
POST   /api/v1/reviews/{id}/documents/{did}/extract        - Run extraction
GET    /api/v1/reviews/{id}/documents/{did}/extraction     - Get extraction results with sample
POST   /api/v1/reviews/{id}/documents/{did}/confirm        - Confirm extraction (human checkpoint)
POST   /api/v1/reviews/{id}/reference-datasets/{rsid}      - Attach reference dataset to review
```

#### 12.15 Analysis

```
POST   /api/v1/reviews/{id}/analyze            - Run framework analysis (deterministic)
GET    /api/v1/reviews/{id}/findings           - Get findings (filterable, sortable, paginated)
GET    /api/v1/reviews/{id}/findings/{fid}     - Get single finding with affected records
PUT    /api/v1/reviews/{id}/findings/{fid}     - Update finding (disposition, notes)
POST   /api/v1/reviews/{id}/findings/bulk-disposition  - Set disposition on multiple findings
POST   /api/v1/reviews/{id}/enrich             - Run AI enrichment on all findings
POST   /api/v1/reviews/{id}/findings/{fid}/enrich  - Re-run AI enrichment on single finding
POST   /api/v1/reviews/{id}/findings/bulk-enrich   - Run AI enrichment on selected findings
GET    /api/v1/reviews/{id}/findings/{fid}/records - Get affected records for finding (paginated)
POST   /api/v1/reviews/{id}/approve            - Submit review approval with attestation
POST   /api/v1/reviews/{id}/reject             - Reject review (send back with reason)
```

**Bulk Disposition Request Body:**

```json
{
  "finding_ids": ["uuid1", "uuid2", "uuid3"],
  "disposition": "approved",
  "justification": "Reviewed - access appropriate for job function"
}
```

Bulk operations are atomic: all succeed or all fail. Each finding receives its own audit trail entry referencing the bulk operation ID. Maximum 200 findings per bulk request.

#### 12.16 Reports

```
POST   /api/v1/reviews/{id}/reports/review     - Generate review report (PDF)
POST   /api/v1/reviews/{id}/reports/compliance - Generate compliance report (PDF)
POST   /api/v1/reviews/{id}/reports/evidence   - Generate examination evidence package (ZIP)
POST   /api/v1/reports/trend                   - Generate trend report (specify application + date range)
POST   /api/v1/reports/exceptions              - Generate exception report
GET    /api/v1/reports/{report_id}             - Download generated report
```

#### 12.17 Audit

```
GET    /api/v1/audit                           - List audit entries (filterable by date, actor, entity, action)
GET    /api/v1/audit/export                    - Export audit log (JSON or CSV)
POST   /api/v1/audit/verify                    - Verify hash chain integrity
GET    /api/v1/audit/stats                     - Audit statistics (entry counts, last verified)
```

#### 12.18 Background Tasks

```
GET    /api/v1/tasks/{id}                      - Get task status and progress
```

Task status response:

```json
{
  "id": "task-uuid",
  "type": "analysis",
  "status": "running",
  "progress": 65,
  "started_at": "2026-02-10T14:30:00Z",
  "completed_at": null,
  "error_message": null,
  "review_id": "review-uuid"
}
```

Task status values: `pending`, `running`, `completed`, `failed`.

#### 12.19 Webhook / Event Specification (Phase 3+)

The system SHALL emit events for key state changes. Phase 3 implements an internal event bus (Python signals/callbacks). Phase 4+ adds optional webhook delivery to configured URLs.

**Event Types:**

| Event Type | Trigger |
|------------|---------|
| `review.status_changed` | Review transitions between lifecycle states |
| `review.overdue` | Review passes its scheduled completion date |
| `review.sla_breached` | Review exceeds SLA timer for current state |
| `finding.disposition_changed` | Finding disposition is set or changed |
| `reference_dataset.stale` | Reference dataset passes freshness threshold |
| `audit.chain_verification_failed` | Hash chain integrity check fails |
| `extraction.confidence_below_threshold` | Extraction confidence below configured minimum |
| `framework.published` | Framework version published |

**Event Payload Format:**

```json
{
  "event_type": "review.status_changed",
  "event_id": "evt_uuid",
  "timestamp": "2026-02-10T14:30:00Z",
  "actor_id": "user-uuid",
  "payload": {
    "review_id": "review-uuid",
    "from_status": "extracted",
    "to_status": "analyzed"
  }
}
```

**Webhook Delivery (Phase 4+):**
- Webhooks registered per event type via admin settings
- Delivery uses HTTP POST with HMAC-SHA256 signature in `X-SAPv2-Signature` header
- Retry policy: 3 attempts with exponential backoff (10s, 60s, 300s)
- Delivery status logged; failed deliveries visible in admin dashboard

---

### 13. Reference Implementation: Fedlink User Access Review

This section provides a concrete, end-to-end example using real Fedlink data structures, including the first-time setup journey, data migration from spreadsheets, and error recovery at each phase.

#### 13.1 First-Time Setup Journey

Before running the first Fedlink review, a new SAPv2 installation must be configured. This walkthrough covers the complete onboarding experience.

**Step 1: Initial Admin Account**

The first admin account is created via a CLI script that runs against the database directly. This is the only account created outside the normal invite flow:

```bash
# On first deploy, Railway runs:
railway run python scripts/create_initial_admin.py
# Prompts for: email, password, full name
# Creates user with role=admin, generates first invite codes
```

**Step 2: Organization Profile**

After first login, the setup wizard presents the organization profile screen:

| Field | Example Value | Purpose |
|-------|--------------|---------|
| Bank name | "First Community Bank" | Report branding, audit attribution |
| Primary contact | "Josh Lopez" | System administrator contact |
| Timezone | "America/Chicago" | SLA calculations, report timestamps |
| Logo | Upload PNG/SVG | Report header branding |

**Step 3: Import Starter Frameworks**

The setup wizard presents the starter framework library:

| Starter Framework | Review Type | Checks Included |
|-------------------|------------|-----------------|
| User Access Review - Standard | `user_access` | Terminated employee detection, inactive accounts, disabled accounts not removed, high-privilege access review |
| User Access Review - Privileged | `user_access` | All standard checks + high dollar limits, admin access review, segregation of duties |
| Firewall Rule Review - Standard | `firewall_rule` | Overly permissive rules, unused rules, any-any rules, expired temporary rules |

Each imported framework arrives in DRAFT status. The wizard guides threshold customization:

- "How many days of inactivity should flag an account?" (default: 90)
- "What dollar limit requires management attestation?" (default: $1,000,000)
- "Which role patterns indicate admin access?" (default: `ADMIN*`, `SECURI*`)

**Step 4: Create Fedlink Application**

Guided application creation with common banking system defaults:

```yaml
application:
  name: "Fedlink Anywhere"
  vendor: "Federal Reserve Bank"
  review_type: "user_access"
  context: "Wire transfer and ACH settlement system used for interbank transactions"
  data_classification: "confidential"
  review_schedule:
    frequency: "quarterly"
    reminder_days_before: 14
    assigned_reviewer: null  # Set after user creation
```

**Step 5: Upload Sample Document and Create Template**

The wizard prompts the user to upload a sample Fedlink CSV for template creation:

1. Upload `Fedlink Anywhere Users.CSV`
2. System auto-detects columns: userid, username, status, lastlogin, limit, authgroup
3. AI mapping assistant suggests field mappings (with confidence scores)
4. User reviews and confirms each mapping
5. System saves template as DRAFT, runs validation against the sample data
6. User sees extraction preview: "50 records parsed, 0 validation errors, confidence 0.98"
7. User publishes template

**Step 6: Upload Reference Data**

Guided HR data import:

1. Upload `All Employees.xlsx`
2. System detects columns: Employee ID, Name, Status, Department, Email
3. User maps fields to reference schema: identifier, display_name, employment_status, department, email
4. System validates: "312 records parsed, 0 errors"
5. Reference dataset saved with freshness metadata

**Step 7: First Review Walkthrough**

The wizard walks through the complete review lifecycle with coaching tooltips at each state:

1. **Create review** -- Tooltip: "Select the framework and time period for this review"
2. **Upload documents** -- Tooltip: "Upload the exports from Fedlink. The system will match them to your templates."
3. **Confirm extraction** -- Tooltip: "Verify the parsed data looks correct. Check record counts and sample values."
4. **Run analysis** -- Tooltip: "The system will apply all framework checks deterministically."
5. **Review findings** -- Tooltip: "Each finding needs a disposition: Approve, Revoke, or Abstain."
6. **Approve review** -- Tooltip: "Final sign-off creates an immutable audit record."

#### 13.2 Data Migration from Spreadsheet Reviews

Community banks migrating from Excel-based access reviews can import historical data for trend continuity.

**Import Wizard:**

```
POST /api/v1/reviews/import-historical
```

**Step 1: Upload Historical Spreadsheet**

The import wizard accepts CSV or Excel files containing prior review summaries. Required columns:

| Column | Description | Example |
|--------|-------------|---------|
| review_date | Date the review was completed | 2025-09-30 |
| application_name | System that was reviewed | Fedlink Anywhere |
| total_accounts | Number of accounts reviewed | 847 |
| findings_critical | Count of critical findings | 2 |
| findings_high | Count of high findings | 5 |
| findings_medium | Count of medium findings | 12 |
| findings_low | Count of low findings | 8 |
| findings_info | Count of informational findings | 23 |
| overall_status | Review outcome | Completed - Remediation Required |
| reviewer_name | Who performed the review | Josh Lopez |

**Step 2: Map to SAPv2 Structure**

The mapping tool allows users to associate imported data with existing SAPv2 applications:

1. Match `application_name` to SAPv2 application records
2. Set review period (quarter/month) based on review_date
3. Optionally upload the original spreadsheet as an attachment

**Step 3: Historical Review Records**

Imported reviews are stored with `source = "historical_import"` and are clearly distinguished in the UI:

- Shown with a "Historical Import" badge in review lists
- Included in trend analysis charts (dashed lines for imported periods vs. solid for native reviews)
- NOT included in hash-chain audit trail (they predate the system)
- NOT editable -- they serve as read-only reference points

**Step 4: Trend Continuity**

After import, the trend analysis dashboard shows historical context:

```
Q1 2025: 50 findings (imported from spreadsheet)
Q2 2025: 47 findings (imported from spreadsheet)
Q3 2025: 42 findings (imported from spreadsheet)
Q4 2025: 38 findings (first native SAPv2 review)
Q1 2026: 31 findings (native SAPv2 review)
```

#### 13.3 Fedlink Data Sources

| Document | Format | Purpose | Key Fields | Document Role |
|----------|--------|---------|------------|---------------|
| Fedlink Anywhere Users.CSV | CSV | User accounts with status, limits, last login | userid, username, status (A/D), lastlogin, limit, authgroup | Primary |
| Fedlink Users.pdf | PDF | Detailed permissions per user | Fedlink ID, Level, Outgoing Limit, OFAC permissions | Supplementary |
| All Employees.xlsx | Excel | HR source of truth for cross-reference | Employee ID, Name, Status, Department | Reference Dataset |
| Fedlink Roles.xlsx | Excel | Role definitions and risk levels | Role Name, Description, Risk Level | Configuration Reference |

#### 13.4 Example Document Template (Fedlink Anywhere CSV)

```yaml
document_template:
  id: "fedlink_anywhere_users"
  name: "Fedlink Anywhere Users Export"
  format: "csv"
  confidence_threshold: 0.95

  detection:
    method: "column_presence"
    required_columns: ["userid", "username", "status", "lastlogin", "limit", "authgroup"]

  mapping:
    identifier:
      source: "userid"
      transform: "lowercase"
    display_name:
      source: "username"
    email:
      source: "email"
      transform: "lowercase"
    status:
      source: "status"
      transform: "value_map"
      value_map:
        "A": "active"
        "D": "disabled"
    last_activity:
      source: "lastlogin"
      transform: "parse_date"
      date_format: "MM/DD/YYYY HH:mm:ss"
    roles:
      source: "authgroup"
      transform: "to_array"
    account_type:
      default: "human"
    extended_attributes:
      limit:
        source: "limit"
        transform: "parse_number"
      usrlevel:
        source: "usrlevel"
        transform: "parse_number"

  validation:
    - field: "identifier"
      rule: "required"
    - field: "identifier"
      rule: "unique"
    - field: "last_activity"
      rule: "valid_date"
```

#### 13.5 Cross-Document Correlation Example

**Scenario:** Detect terminated employees with active Fedlink access

```yaml
check:
  id: "terminated_with_fedlink_access"
  name: "Terminated Employee with Active Fedlink Access"

  severity_rules:
    - condition: { ">": [{"var": "days_since_termination"}, 30] }
      severity: "critical"
    - condition: { ">": [{"var": "days_since_termination"}, 7] }
      severity: "high"
    - condition: { ">=": [{"var": "days_since_termination"}, 0] }
      severity: "medium"
  default_severity: "critical"

  condition:
    type: "cross_reference"
    mode: "present_in_primary_absent_in_secondary"

    primary_dataset:
      document_template: "fedlink_anywhere_users"
      filter:
        field: "status"
        operator: "equals"
        value: "active"

    secondary_dataset:
      reference_dataset_type: "hr_employees"
      filter:
        field: "employment_status"
        operator: "equals"
        value: "active"

    match_on:
      - primary_field: "email"
        secondary_field: "email"
        transform: "lowercase"

  output_fields:
    - identifier
    - display_name
    - email
    - status
    - last_activity

  explainability_template: |
    This check cross-references active Fedlink Anywhere accounts against the
    HR active employee list. Found ${record_count} active Fedlink accounts
    where the associated employee is not in the HR active employees list,
    indicating possible terminated employee access.

  remediation_guidance: |
    CRITICAL: Access for terminated employees must be removed immediately.
    1. Disable the Fedlink account
    2. Review audit logs for any activity since termination
    3. Document findings and escalate if suspicious activity detected
```

#### 13.6 Complete Framework for Fedlink

```yaml
framework:
  id: "fedlink_uar_standard"
  name: "Fedlink User Access Review - Standard"
  version: "1.0.0"
  review_type: "user_access"

  regulatory_mappings:
    - framework: "FFIEC"
      category: "Access Management"
      controls: ["AC-2", "AC-6"]

  settings:
    inactive_threshold_days: 90
    high_limit_threshold: 1000000

  checks:
    - id: "terminated_with_fedlink_access"
      name: "Terminated Employee with Active Fedlink Access"
      severity_rules:
        - condition: { ">": [{"var": "days_since_termination"}, 30] }
          severity: "critical"
        - condition: { ">": [{"var": "days_since_termination"}, 7] }
          severity: "high"
        - condition: { ">=": [{"var": "days_since_termination"}, 0] }
          severity: "medium"
      default_severity: "critical"
      enabled: true
      condition:
        type: "cross_reference"
        mode: "present_in_primary_absent_in_secondary"
        primary_dataset: "application_users"
        secondary_dataset: "hr_active_employees"
        match_field: "email"
      filter:
        field: "status"
        operator: "equals"
        value: "active"

    - id: "inactive_accounts"
      name: "Inactive Fedlink Accounts"
      description: "Active accounts with no login in 90+ days"
      default_severity: "medium"
      enabled: true
      condition:
        type: "compound"
        operator: "AND"
        conditions:
          - field: "status"
            operator: "equals"
            value: "active"
          - field: "last_activity"
            operator: "older_than_days"
            value: "${settings.inactive_threshold_days}"

    - id: "disabled_still_in_system"
      name: "Disabled Accounts Not Removed"
      description: "Accounts marked disabled but still present in system"
      default_severity: "low"
      enabled: true
      condition:
        field: "status"
        operator: "equals"
        value: "disabled"

    - id: "high_limit_review"
      name: "High Dollar Limit Accounts"
      description: "Accounts with wire limits >= $1M requiring management attestation"
      default_severity: "info"
      enabled: true
      condition:
        field: "extended_attributes.limit"
        operator: "greater_than_or_equal"
        value: "${settings.high_limit_threshold}"

    - id: "admin_access_review"
      name: "Administrative Access Review"
      description: "Accounts with ADMIN or SECURITY level access"
      default_severity: "info"
      enabled: true
      condition:
        type: "role_match"
        field: "roles"
        mode: "any"
        patterns:
          - "ADMINI*"
          - "SECURI*"
          - "*ADMIN*"
```

#### 13.7 Error Recovery Examples by Phase

Each phase of the review lifecycle has specific failure modes and recovery paths:

**Document Upload Errors:**

| Error | User Sees | Recovery Path |
|-------|-----------|---------------|
| File too large (> 50MB) | "File exceeds maximum size of 50MB. Please split into smaller files or convert PDF tables to CSV." | Re-upload smaller file |
| Wrong format | "File type .docx is not supported. Accepted formats: CSV, XLSX, XLS, PDF, JSON." | Convert file and re-upload |
| Corrupted file | "File could not be read. The file may be corrupted or password-protected." | Re-export from source system |
| Duplicate upload | "This file has already been uploaded to this review (matching SHA-256 hash)." | Skip or replace existing |

**Extraction Errors:**

| Error | User Sees | Recovery Path |
|-------|-----------|---------------|
| Column not found | "Expected column 'userid' was not found. Available columns: UserID, User_Name, ..." | Edit template mapping or re-upload with correct export |
| Date parse failures | "15 of 847 records have unparseable dates in 'lastlogin'. Sample: '13/32/2025'." | View affected records, fix source data, re-extract |
| Low confidence | "Extraction confidence 0.72 is below threshold 0.95. 238 records had validation warnings." | Review warnings, adjust template, or override threshold |
| Parser timeout | "Extraction timed out after 30 seconds. File may be too large for this format." | Convert PDF to CSV, split large files |

**Analysis Errors:**

| Error | User Sees | Recovery Path |
|-------|-----------|---------------|
| Type mismatch | "Check 'high_limit_review' encountered non-numeric values in 'limit' for 3 records. These records were excluded." | Review data quality report, fix source data if needed |
| Empty reference dataset | "Cross-reference check 'terminated_with_fedlink_access' found 0 records in HR dataset. Verify reference data is current." | Upload updated reference dataset, re-analyze |
| Zero findings | "All 5 checks passed with zero findings. This is a clean review." | Proceed to approval (no dispositions needed) |

**AI Enrichment Errors:**

| Error | User Sees | Recovery Path |
|-------|-----------|---------------|
| Provider unavailable | "AI enrichment service is temporarily unavailable. Your deterministic findings are unaffected." | Retry later; review proceeds without enrichment |
| Rate limited | "AI enrichment was rate-limited. 12 of 23 findings were enriched. Remaining findings will be retried." | Wait and retry; already-enriched findings are preserved |
| Token limit | "Finding description was truncated due to token limits. Showing reduced-context enrichment." | Accept reduced enrichment or regenerate with fewer sample records |

---

### 14. Implementation Phases

#### Phases 1-5: Backend Foundation (COMPLETE)

Phases 1 through 5 have been implemented and tested, delivering the complete backend API and domain logic. All 266 tests pass.

**Phase 1 -- Foundation (COMPLETE):**
- Regulatory-grade audit trail with SHA-256 hash chaining
- Hash chain integrity verification endpoint
- Immutable audit log with tamper detection
- User authentication with JWT (access + refresh tokens)
- Invite-code registration flow
- Role-based access control (admin, analyst, reviewer)
- Password hashing with bcrypt, session management

**Phase 2 -- Configuration (COMPLETE):**
- Application CRUD with context, data classification, review schedules
- Document template management with field mappings and transforms
- Framework CRUD with JSON Logic check definitions
- Framework versioning, publishing, and immutability enforcement
- Starter framework library (basic UAR, privileged access)

**Phase 3 -- Document Processing (COMPLETE):**
- CSV parser with delimiter detection, encoding handling
- Excel parser with multi-sheet support
- PDF parser with table extraction (pdfplumber)
- Image parser with OCR (Tesseract)
- Word document parser
- Document upload with SHA-256 integrity verification
- Template matching with confidence scoring
- Extraction with human confirmation checkpoint
- 169 tests covering all parsers and extraction workflows

**Phase 4 -- AI Mapping (COMPLETE):**
- AI provider abstraction layer (Azure OpenAI, OpenAI, mock)
- Provider fallback chain with automatic switchover
- Structured prompt templates for field mapping suggestions
- Mapping proposal generation with confidence scores
- Mapping approval workflow (accept, modify, reject per field)
- Token usage tracking per invocation
- 193 tests covering provider abstraction and mapping workflows

**Phase 5 -- Analysis Engine (COMPLETE):**
- Reference dataset upload, versioning, and freshness tracking
- Deterministic analysis engine with JSON Logic rule evaluation
- Five core check types: date comparison, value comparison, compound conditions, cross-reference, role pattern matching
- Conditional severity rules with dynamic evaluation
- Explainability template rendering
- Cross-reference merging module for multi-dataset correlation
- Analysis checksum generation for reproducibility verification
- 266 tests total, including determinism golden tests

#### Phase 6: Frontend Foundation (Weeks 1-6)

**Deliverables:**
- React 18 application with TypeScript and Vite
- Authentication UI: login, registration (invite code), password reset
- Application shell: sidebar navigation, header, breadcrumbs
- shadcn/ui component library integration with design system
- API client layer with JWT token management and refresh logic
- Protected route handling with role-based access
- Dashboard skeleton with placeholder widgets
- Docker Compose integration for local full-stack development
- Frontend CI pipeline (lint, type-check, unit tests)

**Technical Deliverables:**
- React Router v6 with nested layouts
- Zustand or React Context for auth state management
- Axios/fetch wrapper with interceptors for token refresh, error handling, request IDs
- TanStack Query for server state management and caching
- Responsive layout supporting 1024px+ viewports
- Accessibility: WCAG 2.1 AA compliance from the start

**Success Criteria:**
- User can register, log in, and see the dashboard
- Navigation reflects user role (admin sees admin sections)
- API errors display consistently via toast notifications
- Frontend tests pass in CI with > 70% coverage on critical paths

#### Phase 7: Frontend Features (Weeks 7-14)

**Deliverables:**
- Review workflow UI: create review, upload documents, confirm extraction, run analysis
- Finding review screen: finding list with severity badges, filtering, sorting
- Finding detail: affected records table, disposition controls, AI enrichment display
- Bulk disposition interface: multi-select, filter-based selection, batch apply
- Framework builder UI: check editor, JSON Logic visual builder, dry-run testing
- Application configuration screens: template editor, mapping editor with live preview
- Reference dataset management: upload, version history, freshness indicators
- Admin screens: user management, invite codes, system settings, AI configuration
- Report generation triggers with download management
- Audit log viewer with filtering, search, and hash verification
- AI content visual treatment: purple tint background, "AI Generated" badges, regenerate button

**Technical Deliverables:**
- Virtual scrolling for large finding lists (1000+ findings)
- File upload with progress indicators and drag-and-drop
- Real-time task progress polling for extraction, analysis, and enrichment
- Data table component with server-side pagination, sorting, and filtering
- Form validation with Zod schemas matching backend Pydantic models

**Success Criteria:**
- End-to-end Fedlink review completable through the UI
- Bulk disposition works for 200+ findings
- Framework builder creates valid JSON Logic checks
- AI enrichment clearly visually distinguished from deterministic content
- All screens functional at 1024px viewport width

#### Phase 8: Integration and Polish (Weeks 15-20)

**Deliverables:**
- End-to-end test suite (Playwright) covering core review workflow
- First-time setup wizard (guided onboarding flow)
- Historical review import wizard
- Evidence package generation (ZIP with organized reports + raw data)
- Email notification system (review assignment, overdue alerts, SLA warnings)
- Compliance calendar with upcoming review schedule
- Trend analysis dashboard with historical comparison charts
- Performance optimization: lazy loading, code splitting, API response caching
- Railway deployment pipeline: staging + production environments
- Monitoring: Sentry integration, structured logging, health check endpoints
- Security hardening: CORS lockdown, CSP headers, rate limiting middleware

**Technical Deliverables:**
- GitHub Actions CI/CD: test on PR, deploy staging on develop merge, deploy production on main merge
- Docker multi-stage builds for API, worker, and frontend
- Alembic migration testing against staging database
- Load testing with k6: verify NFR performance targets
- Security scanning: dependency audit, OWASP headers check

**Success Criteria:**
- E2E tests cover: login, create review, upload, extract, analyze, disposition, approve
- Deployment takes < 10 minutes from merge to live
- Zero-downtime deployments verified on staging
- Performance NFRs met: extraction < 30s, analysis < 60s, dashboard < 2s
- Sentry captures errors with request IDs correlated to audit log

#### Phase 9: Beta and Feedback (Weeks 21-26)

**Deliverables:**
- Internal beta with real Fedlink review data
- Examiner feedback integration (read-only examiner role, evidence package review)
- Feedback collection mechanism (in-app feedback widget)
- Iteration on UX based on real review workflow observations
- Documentation: user guide, admin guide, examiner walkthrough
- Framework library expansion based on beta feedback
- Bug fixes, edge case handling, error message improvements
- Performance tuning based on real-world data sizes

**Success Criteria:**
- At least one complete quarterly review cycle conducted in SAPv2
- Examiner (or examiner proxy) validates evidence package completeness
- Review completion time < 50% of previous spreadsheet-based process
- User satisfaction score > 4/5 from beta participants
- Zero critical or high bugs remaining at beta exit
- All compliance calendar reminders firing correctly

---

### 15. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| AI produces inconsistent enrichment | Medium | High | Structured prompts, low temperature, confidence scoring, regeneration option |
| Document parsing fails for edge cases | High | Medium | Robust error handling, confidence scoring, manual override, CSV fallback for PDF |
| Framework rules insufficient for complex checks | High | Medium | JSON Logic extensibility with custom operators, compound conditions, code escape hatch |
| Users create mappings incorrectly | Medium | Medium | Validation, live preview, confidence scoring, comparison to prior periods |
| Performance issues with large datasets | Medium | Low | Hybrid data model (not pure JSONB), pagination, async processing, indexing |
| Regulatory requirements change | Medium | Medium | Flexible framework system, version control, regulatory mapping structure |
| PDF extraction unreliable for complex layouts | Medium | High | Phase 1 limited to CSV/Excel; PDF Phase 2 with pdfplumber accuracy scoring; CSV conversion fallback |
| JSONB blob storage becomes bottleneck | High | Medium | Hybrid schema from day 1: extracted_records as normalized table, JSONB only for variable data |
| Rule engine complexity grows unmanageable | Medium | Medium | JSON Logic keeps rules portable and testable; dry-run testing; version control |
| User adoption resistance | Medium | Medium | Familiar spreadsheet paradigms, minimal clicks, phased rollout, quick wins first |
| Audit log tampering | Critical | Low | Hash chaining, database triggers preventing UPDATE/DELETE, restricted DB permissions |
| AI provider lock-in | Medium | Medium | Provider abstraction layer with pluggable backends; mock provider for testing; switchover requires only environment variable change and < 1 hour verification |
| Railway scaling limits | Medium | Low | Containerized architecture is portable to any Docker host (AWS ECS, GCP Cloud Run); Railway-specific dependencies limited to deployment config |
| LLM cost overruns | High | Medium | Token usage tracking per invocation with per-review and monthly budget limits; configurable token caps per enrichment call; AI usage dashboard with cost projections; mock provider for development |
| Data breach regulatory impact | Critical | Low | AES-256 encryption at rest, TLS 1.2+ in transit; field-level encryption for PII; immutable audit trail for forensic investigation; incident response plan with regulatory notification timeline |
| Single developer bus factor | High | Medium | Comprehensive PRD as architectural source of truth; inline code documentation; 266+ automated tests as living specification; Claude Code-assisted development reduces ramp-up time for new contributors |
| Frontend complexity exceeds timeline | Medium | Medium | shadcn/ui component library reduces custom UI development; phased delivery with working software at each phase boundary; critical workflow (review lifecycle) prioritized over admin polish |
| Stale reference datasets produce false findings | High | Medium | Freshness tracking with configurable thresholds; prominent warnings when reference data exceeds freshness window; review-level lock to specific dataset version |

---

### 16. Success Metrics

**Consistency (Primary Goal):**
- Same document + same framework = identical finding counts 100% of time
- Extraction record counts match source document row counts
- Analysis checksum matches on re-run with same inputs

**Efficiency:**
- Review completion time reduced by 50% vs. manual spreadsheet process
- New application onboarding time < 30 minutes with AI mapping assistance
- Extraction confirmation takes < 2 minutes per document
- Bulk disposition of homogeneous findings < 5 minutes per batch

**Quality:**
- Zero missed critical findings (validated against manual review for first 3 quarters)
- Auditor/examiner acceptance of methodology documentation
- AI enrichment confidence scores average > 0.85

**Adoption:**
- All quarterly user access reviews conducted in platform within 6 months
- Framework library covers 80% of recurring review types within 12 months
- User satisfaction score > 4/5 in quarterly feedback

**Compliance:**
- Zero examination findings related to access review methodology
- Audit trail hash chain verification passes 100% of integrity checks
- All reviews completed within scheduled timeframe (< 5% overdue)

**AI Cost Efficiency:**
- AI cost per review < $2.00 for standard enrichment (target based on GPT-4o pricing)
- AI cost per review < $5.00 for full enrichment including executive summary
- Monthly AI spend trackable and under configurable budget cap
- Provider switchover time < 1 hour (environment variable change + verification)

**Operational Resilience:**
- Mean time to recovery (MTTR) for API outage < 15 minutes
- Mean time to recovery for failed deployment (rollback) < 10 minutes
- Mean time to recovery for database issue < 30 minutes
- Health check uptime > 99.5% (measured monthly)

**Examiner Satisfaction:**
- Evidence package accepted by examiner without supplemental requests in > 80% of reviews
- Examiner walkthrough of the platform completes in < 30 minutes
- Methodology documentation rated "adequate" or "strong" by examiner

---

### 17. Glossary

| Term | Definition |
|------|------------|
| **Framework** | A reusable, versioned set of checks defining what to analyze in a security review. Contains executable JSON Logic rules, not prose. |
| **Framework Lifecycle** | The progression of a framework through states: DRAFT (editable), PUBLISHED (immutable, usable for reviews), DEPRECATED (still usable but with warning), ARCHIVED (read-only, not usable for new reviews). |
| **Application** | A system or service subject to security review. Includes context, role definitions, document templates, and review schedule. |
| **Review** | An instance of applying a framework to an application for a specific time period. Follows defined lifecycle states. |
| **Check** | A single rule within a framework that identifies a specific condition. Deterministic -- same input always produces same output. |
| **Finding** | A result produced when records match a check's condition. Includes deterministic data (counts, severity) and optional AI enrichment. |
| **Disposition** | The reviewer's decision on a finding: Approve (access appropriate), Revoke (access should be removed), or Abstain (cannot determine, escalation required). Recorded with justification and timestamp. |
| **Extraction** | The process of normalizing a source document to canonical schema using a saved template. Deterministic and confidence-scored. |
| **Template** | Saved configuration for extracting data from a specific document type. Includes detection rules, field mappings, and transformations. |
| **Reference Dataset** | A shared dataset (e.g., HR employee list) used for cross-reference checks across multiple reviews. Versioned with freshness tracking. |
| **Enrichment** | AI-generated content that supplements deterministic findings. Always labeled, confidence-scored, and human-reviewable. |
| **Explainability** | Template-driven plain-English explanation of why a finding was generated, including record counts and threshold values. Deterministic. |
| **JSON Logic** | A standard for expressing rules as JSON data structures. Used by SAPv2 for deterministic, portable, serializable rule evaluation. |
| **Confidence Score** | A 0.0-1.0 measure of extraction accuracy or AI output reliability. Below threshold triggers mandatory human review. |
| **Hash Chain** | Cryptographic linking of audit log entries where each entry includes the hash of the previous entry, enabling tamper detection. |
| **Provider Abstraction** | The AI provider layer that decouples SAPv2's enrichment logic from any specific AI vendor. Supports Azure OpenAI, OpenAI, and mock providers with a common interface. Enables switchover via configuration change without code modification. |
| **Fallback Chain** | Ordered list of AI providers tried in sequence when the primary provider fails. Example: Azure OpenAI -> OpenAI -> mock (graceful degradation). |
| **Evidence Package** | A comprehensive ZIP archive containing all artifacts needed for regulatory examination: review reports, audit trails, methodology documentation, source document hashes, extraction details, disposition records, and AI enrichment logs. Generated via `POST /api/v1/reviews/{id}/reports/evidence`. |
| **SLA** | Service Level Agreement. In SAPv2, configurable time limits for how long a review can remain in each lifecycle state before escalation alerts fire. Example: PENDING_REVIEW state has a 10-business-day SLA. |
| **MTTR** | Mean Time to Recovery. The average time from detection of a system issue to full resolution. SAPv2 targets: API outage < 15 minutes, failed deployment < 10 minutes, database issue < 30 minutes. |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-04 | Josh Lopez | Initial draft |
| 1.1 | 2026-02-04 | Josh Lopez | Added implementation decisions, Fedlink reference, API contracts, DB schema |
| 2.0 | 2026-02-05 | Josh Lopez | Comprehensive enhancement: regulatory alignment (FFIEC/OCC/GLBA), hybrid data model, detailed UI/UX specifications, reference dataset management, confidence scoring, JSON Logic rule engine detail, explainability templates, severity rules, accessibility requirements, enhanced API contracts, complete database schema with triggers and indexes, project structure, glossary expansion |
| 3.0 | 2026-02-10 | Josh Lopez | PRD v3.0 overhaul: Added standard error response schema, cursor-based pagination specification, rate limiting with headers, API versioning strategy (/api/v1/), webhook/event system, bulk operation endpoints, user management and settings endpoints, health check endpoints, AI provider endpoints; expanded reference implementation with first-time setup journey, spreadsheet data migration wizard, error recovery examples per phase; updated implementation phases to reflect completed backend (Phases 1-5, 266 tests) and rebaselined remaining work into Phases 6-9 (frontend, integration, beta); added new risks (AI provider lock-in, Railway scaling, LLM cost overruns, data breach impact, bus factor); added success metrics for AI cost per review, provider switchover time, MTTR targets, examiner satisfaction; expanded glossary with Provider Abstraction, Fallback Chain, Evidence Package, Framework Lifecycle, Disposition detail, SLA, MTTR; incorporated deployment and operations design (CI/CD, Docker, Railway, monitoring, runbooks) |
