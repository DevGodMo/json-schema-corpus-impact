---
name: Real corpus feedback
about: Share a real JSON Schema migration case and whether corpus-level validity flips helped.
title: "[real-corpus] "
labels: []
assignees: []
---

## What were you migrating?

Briefly describe the schema change and the role of the fixture/example corpus in your repository.

## How did you run JSON Schema Corpus Impact Gate?

- CLI or GitHub Action:
- Old schema source/ref:
- New schema source/ref:
- Fixture corpus size / shape:

Please redact secrets or confidential data. A minimal public reproduction is preferred when possible.

## What changed validity?

Which fixtures were `NEWLY_INVALID`, `NEWLY_VALID`, or otherwise relevant to the migration?

## Did this change a migration decision?

Did fixture-level old/new validity impact reveal work or risk that a schema diff or your normal validator/test-suite workflow did not make equally clear? Please explain.

## Would you use this repeatedly?

Would this be useful in CI or on future schema changes? If so, what repeated workflow would you want to preserve?

## Missing output or workflow support

Examples: PR/SARIF annotations, migration summary, baseline/history, larger-corpus performance, dialect support, or another bounded need.

## Boundary acknowledgement

This tool reports observed impact on the supplied fixture corpus. It does not prove universal semantic compatibility for JSON instances that are not represented in that corpus.
