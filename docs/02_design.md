# GOV-C2-024 Design Specification

## Position in AgentCore Architecture

- **Agent class:** `PublicTenderDocumentComparisonAgent`
- **L1 Base:** `AgentBaseGraph`
- **Category:** Cat 2 fixed domain workflow
- **Composition:** outer `AgentBaseGraph` + `TenderComparisonWorkflowGraphNode` + inner `BaseGraph`

## Workflow

`PreProcessNode` accepts at most ten uniquely identified PDF/DOCX/JSON/TXT text
records, enforces the 1 MiB request and per-document limits, blocks regulated
markers, chunks text, and validates a non-empty vendor profile. The inner graph runs:

`RequirementExtractionNode → VendorCoverageNode`

The edge is fail-fast. Extraction preserves a source-clause reference. Coverage
logic reports only whether supporting profile evidence was located; mandatory or
statutory gaps become `mandatory_review_flags`. It does not declare eligibility,
bid approval, rejection or disqualification.

`PostProcessNode` builds an escaped Markdown/JSON matrix and one bounded advisory
signal: `ready_for_human_bid_review`, `bid_team_evidence_review_required`,
`capability_gap_review_required`, or `manual_legal_and_procurement_review_required`.
The mandatory legal/eligibility disclaimer is always included.

## State and Security

The state is a flat TypedDict; list/object payloads are JSON strings. Domain nodes
require `VERIFIED_EXTERNAL` and emit trace events. S-3 rejects credentials and
prohibited legal or bid determinations. The agent has no submission or procurement
decision connector.
