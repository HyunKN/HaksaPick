"""Negative tests: the gate must fail when mandatory evidence is missing."""
import json
import tempfile
import unittest
from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location

ROOT = Path(__file__).resolve().parents[2]
spec = spec_from_file_location("quality_verify", ROOT / "quality/checks/verify.py")
module = module_from_spec(spec)
spec.loader.exec_module(module)


class QualityGateTests(unittest.TestCase):
    def make_repo(self, root: Path) -> None:
        for relative in module.REQUIRED:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")
        document = {
            "schema_version": 1,
            "rules": [{
                "id": "TEST-APPROVAL",
                "rule": "approved writes only",
                "runtime_owner": "backend/src/main",
                "test_owner": "backend/src/test",
                "status": "planned",
                "evidence": {},
            }],
        }
        (root / "quality/policies.json").write_text(json.dumps(document), encoding="utf-8")

    def test_empty_scaffold_passes_without_claiming_service_coverage(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_repo(root)
            self.assertEqual(module.validate(root), [])

    def test_missing_policy_document_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_repo(root)
            (root / "docs/PRD.md").unlink()
            self.assertTrue(any("docs/PRD.md" in x for x in module.validate(root)))

    def test_component_without_tests_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_repo(root)
            (root / "core/app").mkdir(parents=True)
            errors = module.validate(root)
            self.assertTrue(any("core/tests" in x for x in errors))
            self.assertTrue(any("core/pyproject.toml" in x for x in errors))

    def test_duplicate_policy_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_repo(root)
            path = root / "quality/policies.json"
            document = json.loads(path.read_text())
            document["rules"].append(document["rules"][0].copy())
            path.write_text(json.dumps(document))
            self.assertTrue(any("Duplicate" in x for x in module.validate(root)))

    def test_false_enforced_claim_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_repo(root)
            path = root / "quality/policies.json"
            document = json.loads(path.read_text())
            document["rules"][0]["status"] = "enforced"
            path.write_text(json.dumps(document))
            self.assertTrue(any("missing runtime evidence" in x for x in module.validate(root)))


if __name__ == "__main__":
    unittest.main()
