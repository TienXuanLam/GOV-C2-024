from src.services.tender_comparison_service import compare_vendor_evidence, extract_requirements


def test_statutory_marker_is_a_review_reference_not_a_legal_verdict():
    requirements = extract_requirements("全省庁統一資格 eligibility")
    coverage, gaps, flags = compare_vendor_evidence(requirements, {"name": "Vendor"})
    assert coverage
    assert gaps
    assert flags
    assert all(item["status"] != "Eligibility Violation" for item in coverage)


def test_matching_profile_evidence_can_be_located():
    requirements = [{"id": "REQ-001", "text": "technical evidence", "type": "mandatory", "law_ref": ""}]
    coverage, gaps, flags = compare_vendor_evidence(requirements, {"technical": "evidence"})
    assert coverage[0]["status"] == "evidence_found"
    assert gaps == []
    assert flags == []
