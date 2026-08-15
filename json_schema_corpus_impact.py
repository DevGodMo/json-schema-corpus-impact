#!/usr/bin/env python3
"""JSON Schema Corpus Impact Gate.

Validate the same representative JSON fixtures against two supplied JSON Schema
versions and report fixture-level validity transitions with source-linked error
evidence.

This tool measures impact on the supplied corpus. It does not prove semantic
backward/forward compatibility for all possible JSON instances.
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from jsonschema import exceptions as js_exceptions
from jsonschema.validators import validator_for

VERSION = "0.1.0"
IMPACTS = ("NEWLY_INVALID", "NEWLY_VALID", "UNCHANGED_VALID", "UNCHANGED_INVALID")


@dataclass(frozen=True)
class ValidationErrorEvidence:
    instance_path: str
    schema_path: str
    validator: str
    message: str


@dataclass(frozen=True)
class FixtureImpact:
    fixture_id: str
    impact: str
    old_valid: bool
    new_valid: bool
    old_errors: list[dict[str, Any]]
    new_errors: list[dict[str, Any]]
    fixture_source_ref: str
    old_schema_source_ref: str
    new_schema_source_ref: str


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _json_pointer(parts: Iterable[Any]) -> str:
    escaped = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "" if not escaped else "/" + "/".join(escaped)


def _build_validator(schema: Mapping[str, Any]):
    cls = validator_for(schema)
    cls.check_schema(schema)
    return cls(schema)


def _validate(validator, instance: Any) -> list[ValidationErrorEvidence]:
    errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: (
            tuple(str(part) for part in error.absolute_path),
            tuple(str(part) for part in error.absolute_schema_path),
            error.message,
        ),
    )
    return [
        ValidationErrorEvidence(
            instance_path=_json_pointer(error.absolute_path),
            schema_path=_json_pointer(error.absolute_schema_path),
            validator=str(error.validator),
            message=error.message,
        )
        for error in errors
    ]


def _impact(old_valid: bool, new_valid: bool) -> str:
    if old_valid and not new_valid:
        return "NEWLY_INVALID"
    if not old_valid and new_valid:
        return "NEWLY_VALID"
    if old_valid and new_valid:
        return "UNCHANGED_VALID"
    return "UNCHANGED_INVALID"


def evaluate_corpus(
    old_schema: Mapping[str, Any],
    new_schema: Mapping[str, Any],
    fixtures: list[tuple[str, Any, str]],
    *,
    old_schema_source_ref: str,
    new_schema_source_ref: str,
) -> dict[str, Any]:
    old_validator = _build_validator(old_schema)
    new_validator = _build_validator(new_schema)

    impacts: list[FixtureImpact] = []
    for fixture_id, instance, fixture_source_ref in sorted(fixtures, key=lambda row: row[0]):
        old_error_objects = _validate(old_validator, instance)
        new_error_objects = _validate(new_validator, instance)
        old_valid = not old_error_objects
        new_valid = not new_error_objects
        impacts.append(
            FixtureImpact(
                fixture_id=fixture_id,
                impact=_impact(old_valid, new_valid),
                old_valid=old_valid,
                new_valid=new_valid,
                old_errors=[asdict(error) for error in old_error_objects],
                new_errors=[asdict(error) for error in new_error_objects],
                fixture_source_ref=fixture_source_ref,
                old_schema_source_ref=old_schema_source_ref,
                new_schema_source_ref=new_schema_source_ref,
            )
        )

    counts = {impact: 0 for impact in IMPACTS}
    for item in impacts:
        counts[item.impact] += 1

    return {
        "schema_version": 1,
        "tool_version": VERSION,
        "old_schema_dialect": old_schema.get("$schema"),
        "new_schema_dialect": new_schema.get("$schema"),
        "fixture_count": len(impacts),
        "impact_counts": counts,
        "impacts": [asdict(item) for item in impacts],
    }


def render_markdown(result: Mapping[str, Any]) -> str:
    counts = result["impact_counts"]
    lines = [
        "# JSON Schema Corpus Impact",
        "",
        f"Fixtures evaluated: **{result['fixture_count']}**",
        "",
        "| Impact | Count |",
        "|---|---:|",
    ]
    for impact in IMPACTS:
        lines.append(f"| `{impact}` | {counts[impact]} |")

    lines.extend(["", "## Fixture results", ""])
    for item in result["impacts"]:
        lines.append(f"### `{item['fixture_id']}` — `{item['impact']}`")
        lines.append("")
        lines.append(f"- Old valid: `{str(item['old_valid']).lower()}`")
        lines.append(f"- New valid: `{str(item['new_valid']).lower()}`")
        lines.append(f"- Fixture source: `{item['fixture_source_ref']}`")
        lines.append(f"- Old schema source: `{item['old_schema_source_ref']}`")
        lines.append(f"- New schema source: `{item['new_schema_source_ref']}`")
        if item["new_errors"]:
            lines.append("- New-schema evidence:")
            for error in item["new_errors"]:
                lines.append(
                    f"  - `{error['validator']}` at instance `{error['instance_path'] or '/'}` / "
                    f"schema `{error['schema_path'] or '/'}`: {error['message']}"
                )
        lines.append("")

    lines.extend(
        [
            "---",
            "This report describes validity transitions for the supplied fixture corpus only; ",
            "it is not universal semantic compatibility proof.",
            "",
        ]
    )
    return "\n".join(lines)


def _collect_fixture_paths(explicit: list[Path], patterns: list[str]) -> list[Path]:
    resolved: dict[str, Path] = {}
    for path in explicit:
        resolved[str(path)] = path
    for pattern in patterns:
        for match in glob.glob(pattern, recursive=True):
            path = Path(match)
            if path.is_file():
                resolved[str(path)] = path
    paths = [resolved[key] for key in sorted(resolved)]
    if not paths:
        raise ValueError("no fixture files matched")
    return paths


def _should_fail(result: Mapping[str, Any], mode: str) -> bool:
    counts = result["impact_counts"]
    if mode == "never":
        return False
    if mode == "newly-invalid":
        return counts["NEWLY_INVALID"] > 0
    if mode == "any-change":
        return counts["NEWLY_INVALID"] > 0 or counts["NEWLY_VALID"] > 0
    raise ValueError(f"unsupported fail mode: {mode}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Show which representative JSON fixtures change validity between two JSON Schemas."
    )
    parser.add_argument("old_schema", type=Path)
    parser.add_argument("new_schema", type=Path)
    parser.add_argument("fixtures", nargs="*", type=Path)
    parser.add_argument(
        "--fixture-glob",
        action="append",
        default=[],
        help="Fixture glob evaluated by Python (repeatable; useful in GitHub Actions).",
    )
    parser.add_argument("--old-source-ref")
    parser.add_argument("--new-source-ref")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path, help="Write report to a file instead of stdout.")
    parser.add_argument(
        "--fail-on",
        choices=("never", "newly-invalid", "any-change"),
        default="never",
        help="Optional CI gate. Exit 3 when the selected transition condition is present.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    args = parser.parse_args(argv)

    try:
        old_schema = _load_json(args.old_schema)
        new_schema = _load_json(args.new_schema)
        if not isinstance(old_schema, dict) or not isinstance(new_schema, dict):
            raise ValueError("schemas must be JSON objects")

        fixture_paths = _collect_fixture_paths(args.fixtures, args.fixture_glob)
        fixtures = [(str(path), _load_json(path), str(path)) for path in fixture_paths]
        result = evaluate_corpus(
            old_schema,
            new_schema,
            fixtures,
            old_schema_source_ref=args.old_source_ref or str(args.old_schema),
            new_schema_source_ref=args.new_source_ref or str(args.new_schema),
        )

        report = (
            json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
            if args.format == "json"
            else render_markdown(result)
        )
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(report, encoding="utf-8")
        else:
            sys.stdout.write(report)

        return 3 if _should_fail(result, args.fail_on) else 0
    except (OSError, ValueError, json.JSONDecodeError, js_exceptions.SchemaError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
