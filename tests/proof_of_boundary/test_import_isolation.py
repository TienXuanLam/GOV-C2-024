# PB-4: Import Isolation Verification
# Verifies that this template does not directly import Level 0 (agenticstar-platform SDK)

import ast
import os

import pytest


_PROHIBITED = ["agenticstar"]


def _scan_imports(filepath: str) -> list[str]:
    with open(filepath) as f:
        tree = ast.parse(f.read(), filename=filepath)
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for p in _PROHIBITED:
                    if alias.name == p or alias.name.startswith(f"{p}."):
                        violations.append(f"{filepath}:{node.lineno} — import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for p in _PROHIBITED:
                    if node.module == p or node.module.startswith(f"{p}."):
                        violations.append(f"{filepath}:{node.lineno} — from {node.module} import ...")
    return violations


def _find_python_files(directory: str) -> list[str]:
    py_files = []
    for root, _dirs, files in os.walk(directory):
        for f in files:
            if f.endswith(".py"):
                py_files.append(os.path.join(root, f))
    return py_files


class TestImportIsolation:
    """PB-4: Template must not import Level 0 (agenticstar SDK)."""

    def test_no_prohibited_imports_in_src(self):
        src_dir = os.path.join(os.path.dirname(__file__), "..", "..", "src")
        if not os.path.exists(src_dir):
            pytest.skip("src/ directory not found")

        violations = []
        for filepath in _find_python_files(src_dir):
            violations.extend(_scan_imports(filepath))

        assert violations == [], "Import Isolation violations found:\n" + "\n".join(violations)
