# JSON Schema Corpus Impact Gate

**See which real JSON fixtures break when your schema changes.**

Experimental `v0.1.0` developer utility. It validates the **same representative JSON fixture corpus** under an old and a new JSON Schema, then reports which fixtures changed validity and the validator evidence behind each transition.

> This tool reports observed impact on the fixtures you supply. It does **not** prove semantic backward/forward compatibility for every possible JSON instance.

## What it reports

Each fixture is classified as one of:

- `NEWLY_INVALID` — valid under the old schema, invalid under the new schema;
- `NEWLY_VALID` — invalid under the old schema, valid under the new schema;
- `UNCHANGED_VALID`;
- `UNCHANGED_INVALID`.

For each fixture the report preserves:

- fixture path/source reference;
- old and new schema source references;
- old/new validity;
- JSON Pointer instance and schema paths for validation errors;
- validator keyword and message.

The point is migration-impact evidence over a representative corpus, not another structural schema diff.

## 60-second example

Requirements: Python 3 and `jsonschema`.

```bash
python3 -m pip install -r requirements.txt

python3 json_schema_corpus_impact.py \
  examples/old.schema.json \
  examples/new.schema.json \
  --fixture-glob 'examples/fixtures/*.json' \
  --format markdown
```

The bundled corpus demonstrates all four transition classes. `examples/fixtures/breaks.json` is accepted by the old schema and rejected by the new schema because the new schema requires `mode`.

Machine-readable output:

```bash
python3 json_schema_corpus_impact.py \
  examples/old.schema.json \
  examples/new.schema.json \
  --fixture-glob 'examples/fixtures/*.json' \
  --format json \
  --old-source-ref git://your-repo/schema@old \
  --new-source-ref git://your-repo/schema@new
```

## CI gate

Use `--fail-on newly-invalid` to return exit code `3` when any supplied fixture flips valid → invalid:

```bash
python3 json_schema_corpus_impact.py old.schema.json new.schema.json \
  --fixture-glob 'tests/fixtures/*.json' \
  --fail-on newly-invalid
```

Other modes are `never` and `any-change`.

## GitHub Action

This repository contains a thin composite Action. No Marketplace listing is required to consume a public action directly.

```yaml
name: schema-corpus-impact
on:
  pull_request:

jobs:
  impact:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: DevGodMo/json-schema-corpus-impact@main
        with:
          old-schema: schemas/previous.schema.json
          new-schema: schemas/current.schema.json
          fixtures: 'tests/fixtures/*.json'
          format: markdown
          output: json-schema-corpus-impact.md
          fail-on: newly-invalid
```

The Action installs only the bounded Python dependency declared in `requirements.txt`, runs the same CLI, writes the requested report, and fails only according to `fail-on`.

## Tests

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile json_schema_corpus_impact.py
```

The tests cover:

- all four validity-transition classes;
- validator/error-path and source-reference evidence;
- human-readable report boundary language;
- `newly-invalid` CI gate exit behavior.

## Supported boundary

Technically supported in this experimental version:

- local old/new JSON Schemas accepted by the installed Python `jsonschema` validator;
- representative local JSON fixtures;
- deterministic fixture-level validity transitions;
- JSON and Markdown reports;
- optional source labels for the two schema versions;
- a thin GitHub Action wrapper.

Not claimed or provided:

- universal semantic compatibility proof;
- safe migration generation;
- exhaustive analysis of instances not in your corpus;
- guaranteed arbitrary remote `$ref` resolution;
- hosted execution, telemetry, auth, persistence, dashboards, billing, or support SLA;
- package-registry or GitHub Marketplace distribution.

## Why corpus impact?

A schema diff tells you what changed structurally. A one-sided validator run tells you whether fixtures pass one schema. This utility holds the corpus constant and shows **which representative documents actually flip validity across the two supplied schema versions**, with evidence attached.

That is a narrower claim—and the one this experimental public test is designed to validate.

## License

MIT. See `LICENSE`.
