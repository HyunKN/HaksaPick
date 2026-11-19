"""Dependency-free repository Quality Gate. Not production runtime security code."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = (
    "docs/PRD.md",
    "docs/API_SPEC.md",
    "docs/DATA_MODEL.md",
    "docs/DEVELOPMENT_PROCESS.md",
    "AGENTS.md",
    ".github/pull_request_template.md",
    ".github/workflows/quality-gate.yml",
    "quality/README.md",
    "quality/policies.json",
    "quality/tests/test_verify.py",
)


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED:
        if not (root / relative).is_file():
            errors.append(f"Required file missing: {relative}")

    policy_file = root / "quality/policies.json"
    if policy_file.is_file():
        try:
            document = json.loads(policy_file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(f"Invalid policy JSON: {exc}")
        else:
            if document.get("schema_version") != 1:
                errors.append("Policy schema_version must be 1")
            rules = document.get("rules")
            if not isinstance(rules, list) or not rules:
                errors.append("Policy rules must be a nonempty list")
            else:
                seen: set[str] = set()
                for index, rule in enumerate(rules):
                    if not isinstance(rule, dict):
                        errors.append(f"Rule #{index} must be an object")
                        continue
                    rule_id = rule.get("id")
                    if not isinstance(rule_id, str) or not rule_id.strip():
                        errors.append(f"Rule #{index} has no ID")
                        continue
                    if rule_id in seen:
                        errors.append(f"Duplicate policy ID: {rule_id}")
                    seen.add(rule_id)
                    for field in ("rule", "runtime_owner", "test_owner"):
                        if not isinstance(rule.get(field), str) or not rule[field].strip():
                            errors.append(f"{rule_id}: missing {field}")
                    status = rule.get("status")
                    if status not in ("planned", "enforced"):
                        errors.append(f"{rule_id}: invalid status {status!r}")
                    evidence = rule.get("evidence")
                    if not isinstance(evidence, dict):
                        errors.append(f"{rule_id}: evidence must be an object")
                    elif status == "enforced":
                        for kind, owner_key in (("runtime", "runtime_owner"), ("test", "test_owner")):
                            value = evidence.get(kind)
                            owner = rule.get(owner_key)
                            if not isinstance(value, str) or not value.strip() or not isinstance(owner, str):
                                errors.append(f"{rule_id}: enforced rule missing {kind} evidence")
                                continue
                            path = Path(value)
                            if path.is_absolute() or ".." in path.parts or not value.startswith(owner.rstrip("/") + "/"):
                                errors.append(f"{rule_id}: {kind} evidence must be inside {owner}")
                            elif not (root / path).is_file():
                                errors.append(f"{rule_id}: {kind} evidence does not exist: {value}")

    # A source component may not silently bypass its own executable test suite.
    if (root / "core/app").exists():
        if not (root / "core/pyproject.toml").is_file():
            errors.append("Core source exists but core/pyproject.toml is missing")
        if not list((root / "core/tests").rglob("test_*.py")):
            errors.append("Core source exists but core/tests/test_*.py is missing")
    if (root / "backend/src/main").exists():
        if not (root / "backend/gradlew").is_file():
            errors.append("Backend source exists but Gradle wrapper backend/gradlew is missing")
        tests = root / "backend/src/test"
        if not list(tests.rglob("*Test.java")) and not list(tests.rglob("*Tests.java")):
            errors.append("Backend source exists but backend/src/test/*Test.java is missing")
    if (root / "frontend/src").exists():
        for name in ("package.json", "package-lock.json"):
            if not (root / "frontend" / name).is_file():
                errors.append(f"Frontend source exists but frontend/{name} is missing")
        tests = root / "frontend"
        if not any(path for pattern in ("*.test.ts", "*.test.tsx", "*.spec.ts", "*.spec.tsx") for path in tests.rglob(pattern)):
            errors.append("Frontend source exists but a frontend test file is missing")
    return errors


def main() -> int:
    errors = validate(ROOT)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: policy registry, evidence paths and component test boundaries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
