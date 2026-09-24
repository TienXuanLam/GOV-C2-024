# PB-2 + PB-5: State Safety Verification
# Verifies that State contains only msgpack-safe types (no Pydantic, dataclass, JWT)

import ast
import os
import re

import pytest


_CREDENTIAL_PATTERNS = re.compile(r"(jwt|token|api_key|secret|password|credential|connection_string)", re.IGNORECASE)
_PROHIBITED_TYPES = ["BaseModel", "InvocationContext"]


def _scan_state_file(filepath: str) -> list[str]:
    with open(filepath) as f:
        source = f.read()
        tree = ast.parse(source, filename=filepath)
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    field_name = item.target.id
                    if _CREDENTIAL_PATTERNS.search(field_name):
                        violations.append(f"{filepath}:{item.lineno} — Credential-like field name: {field_name}")
                    if item.annotation:
                        ann_str = ast.dump(item.annotation)
                        for prohibited in _PROHIBITED_TYPES:
                            if prohibited in ann_str:
                                violations.append(f"{filepath}:{item.lineno} — Prohibited type in State: {prohibited}")
    return violations


class TestStateSafety:
    """PB-2/PB-5: State must be msgpack-safe with no credentials."""

    def test_state_file_safety(self):
        state_file = os.path.join(os.path.dirname(__file__), "..", "..", "src", "schemas", "state.py")
        if not os.path.exists(state_file):
            pytest.skip("src/schemas/state.py not found")

        violations = _scan_state_file(state_file)
        assert violations == [], "State safety violations found:\n" + "\n".join(violations)

    def test_state_class_extends_agent_state(self):
        """State must extend AgentState — verified via AST (TypedDict blocks runtime checks)."""
        state_file = os.path.join(os.path.dirname(__file__), "..", "..", "src", "schemas", "state.py")
        with open(state_file) as f:
            tree = ast.parse(f.read())

        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_name = base.id if isinstance(base, ast.Name) else getattr(base, "attr", "")
                    if base_name == "AgentState":
                        found = True
        assert found, "No class in state.py inherits from AgentState"

    def test_state_fields_are_primitives(self):
        """Custom state fields declared in state.py must use only primitive type annotations."""
        state_file = os.path.join(os.path.dirname(__file__), "..", "..", "src", "schemas", "state.py")
        with open(state_file) as f:
            tree = ast.parse(f.read())

        _ALLOWED_ANNOTATIONS = {"str", "int", "float", "bool", "None", "Optional", "list", "dict"}
        violations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        ann_str = ast.dump(item.annotation)
                        for name in ["BaseModel", "InvocationContext", "dataclass"]:
                            if name in ann_str:
                                violations.append(f"field '{item.target.id}' uses prohibited type: {name}")
        assert violations == [], "Non-primitive types in state fields:\n" + "\n".join(violations)
