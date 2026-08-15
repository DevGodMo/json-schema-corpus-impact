import json
import tempfile
import unittest
from pathlib import Path

import json_schema_corpus_impact as tool


class CorpusImpactTests(unittest.TestCase):
    def setUp(self):
        self.old_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["id", "legacy"],
            "properties": {
                "id": {"type": "string"},
                "legacy": {"type": "boolean"},
                "mode": {"type": "string"},
            },
            "additionalProperties": False,
        }
        self.new_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["id", "mode"],
            "properties": {
                "id": {"type": "string"},
                "legacy": {"type": "boolean"},
                "mode": {"enum": ["live"]},
            },
            "additionalProperties": False,
        }

    def test_all_transition_classes_and_source_evidence(self):
        fixtures = [
            ("breaks.json", {"id": "a", "legacy": True}, "fixture://breaks"),
            ("fixed.json", {"id": "f", "mode": "live"}, "fixture://fixed"),
            ("stable.json", {"id": "s", "legacy": True, "mode": "live"}, "fixture://stable"),
            ("invalid.json", {"id": 7}, "fixture://invalid"),
        ]
        result = tool.evaluate_corpus(
            self.old_schema,
            self.new_schema,
            fixtures,
            old_schema_source_ref="schema://old",
            new_schema_source_ref="schema://new",
        )
        by_id = {row["fixture_id"]: row for row in result["impacts"]}
        self.assertEqual("NEWLY_INVALID", by_id["breaks.json"]["impact"])
        self.assertEqual("NEWLY_VALID", by_id["fixed.json"]["impact"])
        self.assertEqual("UNCHANGED_VALID", by_id["stable.json"]["impact"])
        self.assertEqual("UNCHANGED_INVALID", by_id["invalid.json"]["impact"])
        self.assertEqual("required", by_id["breaks.json"]["new_errors"][0]["validator"])
        self.assertEqual("schema://new", by_id["breaks.json"]["new_schema_source_ref"])

    def test_markdown_summary_preserves_boundary(self):
        result = tool.evaluate_corpus(
            self.old_schema,
            self.new_schema,
            [("x.json", {"id": "x", "legacy": True}, "fixture://x")],
            old_schema_source_ref="schema://old",
            new_schema_source_ref="schema://new",
        )
        report = tool.render_markdown(result)
        self.assertIn("NEWLY_INVALID", report)
        self.assertIn("not universal semantic compatibility proof", report)

    def test_cli_gate_exit_code(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            old_path = root / "old.json"
            new_path = root / "new.json"
            fixture_path = root / "breaks.json"
            output_path = root / "report.json"
            old_path.write_text(json.dumps(self.old_schema), encoding="utf-8")
            new_path.write_text(json.dumps(self.new_schema), encoding="utf-8")
            fixture_path.write_text(json.dumps({"id": "a", "legacy": True}), encoding="utf-8")
            code = tool.main(
                [
                    str(old_path),
                    str(new_path),
                    str(fixture_path),
                    "--output",
                    str(output_path),
                    "--fail-on",
                    "newly-invalid",
                ]
            )
            self.assertEqual(3, code)
            self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()
