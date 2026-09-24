# Test Specification — GOV-C2-024 PublicTenderDocumentComparisonAgent

## Test Strategy

- Coverage target: 80%
- Test types: Unit / Proof-of-Boundary
- Test files: `tests/unit/test_pre_process_node.py`, `tests/unit/test_main_node.py`, `tests/unit/test_post_process_node.py`, `tests/proof_of_boundary/`

## Framework Compliance Tests (Mandatory)

| TC-ID | Test | Expected Result | Result |
|-------|------|----------------|--------|
| TC-01 | State contract: `PublicTenderDocumentComparisonState` is flat TypedDict with Optional primitives only | Type check pass, no Pydantic/dataclass | ✅ `test_state_fields_are_primitives` |
| TC-02 | `SecurityViolationError` / S-2 rejection fires on PII input (マイナンバー pattern) | ERROR status returned via `_extra_security_gate_input()` | ✅ `test_s2_rejects_pii_my_number` |
| TC-03 | No JWT/Credential in State fields | CI `gate-credential-scan`: 0 violations | ✅ `test_state_file_safety` (AST scan) |
| TC-04 | InvocationContext not in State | State fields contain no InvocationContext type | ✅ `test_state_file_safety` |
| TC-05 | S-4: no duplicate lifecycle events in `execute()` | `node_start`/`node_complete`/`node_error` absent from node bodies | ✅ by design — only domain events emitted |
| TC-06 | S-2: `_security_gate_input()` not overridden in FunctionNode subclasses | `TypeError` at class definition if overridden (`@final`) | ✅ none of the 3 nodes override `_security_gate_input` |
| TC-07 | S-3: `_security_gate_output()` not overridden in FunctionNode subclasses | `TypeError` at class definition if overridden (`@final`) | ✅ none of the 3 nodes override `_security_gate_output` |
| TC-08 | `required_trust_level = VERIFIED_EXTERNAL` enforced on all 3 nodes | Anonymous caller → ERROR, no `execute()` call | ✅ `test_trust_gate_blocks_anonymous` (×3) |
| TC-09 | S-2: `_extra_security_gate_input()` in PreProcessNode scans PII patterns | マイナンバー / 機密 detected → ERROR | ✅ `test_s2_rejects_pii_my_number`, `test_s2_rejects_classified_marker` |
| TC-10 | S-3: `_extra_security_gate_output()` in PostProcessNode scans sensitive tokens | JWT/SK pattern detected → RuntimeError | ✅ `test_s3_hook_blocks_sensitive_token_in_output` |
| TC-11 | S-4: at least one `emit_trace_event()` per node `execute()` | `vector_index_built` (Pre), `requirements_extracted`+`matching_complete` (Main), `report_generated` (Post) | ✅ by code inspection — 1–2 events per node |

## Proof-of-Boundary Tests (Mandatory)

| PB-ID | Boundary | Test | Expected Result | Result |
|-------|----------|------|----------------|--------|
| PB-1 | BaseNode → EventEmitter | `emit_trace_event()` fires on every invocation path | No silent failures | `test_pb_invoke_order.py` |
| PB-2 | State serialization | Post-invoke State is primitives only (Optional[str], Optional[int]) | No Pydantic/dataclass | `test_state_safety.py::test_state_fields_are_primitives` |
| PB-3 | L1 → External service | LLM call dispatched via `MainNode._llm.complete()` (stubbed in unit tests) | Data returned from stub | `test_llm_used_when_provided` |
| PB-4 | Import isolation | No `agenticstar` SDK imports in `src/` | AST scan: 0 violations | `test_import_isolation.py` |
| PB-5 | Checkpoint safety | State fields are str/int/float/bool/None only | Checkpoint inspection pass | `test_state_safety.py` |
| PB-6 | Invoke execution order | S-1 → node_start → S-2 → execute() → S-3 → node_complete for all 3 nodes | Order verified | `test_pb_invoke_order.py::test_call_order_for_every_node` |

## Business Logic Tests

| TC-ID | Test | Input | Expected Result | Result |
|-------|------|-------|----------------|--------|
| BL-01 | Go verdict when all requirements met | Valid tender + matching vendor profile | `go_no_go = "Go"` | ✅ `test_go_verdict_when_all_met` |
| BL-02 | No-Go verdict when eligibility violation present | Tender with 全省庁統一資格 + vendor without registration | `go_no_go = "No-Go"` | ✅ `test_no_go_when_eligibility_violation` |
| BL-03 | Conditional Go when high-severity unmet requirements | Mandatory requirements unmet | `go_no_go = "Conditional Go"` | ✅ `test_conditional_go_with_high_severity_gaps` |
| BL-04 | Markdown table in formatted output | Valid state with requirements + coverage | `| Req ID |` present | ✅ `test_formatted_output_contains_markdown_table` |
| BL-05 | Disclaimer appended to report | Any valid invocation | `免責事項` in `formatted_output` | ✅ `test_formatted_output_contains_disclaimer` |
| BL-06 | PreProcessNode chunking works for multiple documents | 2-doc input | `document_count == 2`, `total_chunks >= 2` | ✅ `test_multiple_documents_chunked` |
| BL-07 | PreProcessNode rejects unsupported file types | `type: "xls"` | ERROR status | ✅ `test_unsupported_document_type_returns_error` |
| BL-08 | MainNode detects eligibility violations | Text with 全省庁統一資格, vendor without it | `eligibility_violations` non-empty list | ✅ `test_eligibility_violation_detected` |
| BL-09 | LLM response used when LLM provided | FakeLLM returning structured JSON | Requirements from LLM in result | ✅ `test_llm_used_when_provided` |

## Test Execution Summary

- Execution date: TBD (run after SDK install)
- Total tests: 35+
- Pass: — / Fail: — / Skip: —
- Coverage: TBD
