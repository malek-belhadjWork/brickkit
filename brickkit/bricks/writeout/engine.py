"""writeout engine — write extracted+validated records to a CSV.

Input: the list of records from `validate` (or `extract`). For each record, emit
one row: the configured field->column mapping, plus optional source and
ok/flags status columns.

Output: a small summary dict {"written", "destination"}.
"""
from __future__ import annotations

import csv
from pathlib import Path


def _columns(config):
    cols = []
    if config.source_column:
        cols.append(config.source_column)
    cols.extend(config.mapping.values())
    if config.include_status:
        cols += ["valid", "flags"]
    return cols


def _row(rec, config):
    fields = rec.get("fields", {})
    row = {}
    if config.source_column:
        row[config.source_column] = rec.get("source", "")
    for field, column in config.mapping.items():
        row[column] = fields.get(field, {}).get("value", "")
    if config.include_status:
        validation = rec.get("validation", {})
        row["valid"] = validation.get("ok", "")
        row["flags"] = ";".join(
            f"{f['field']}:{f['code']}" for f in validation.get("flags", [])
        )
    return row


def run(data, config):
    dest = Path(config.destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    columns = _columns(config)
    with dest.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        for rec in data:
            writer.writerow(_row(rec, config))
    return {"written": len(data), "destination": str(dest)}
