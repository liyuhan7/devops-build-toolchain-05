"""Validate repository JSON contracts without third-party dependencies."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterable


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_ROOT = REPOSITORY_ROOT / "contracts"
REQUIRED_SCHEMA_FIELDS = {"$schema", "$id", "title", "type"}


def iter_references(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        reference = value.get("$ref")
        if isinstance(reference, str):
            yield reference
        for child in value.values():
            yield from iter_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_references(child)


def validate() -> list[str]:
    errors: list[str] = []
    schema_ids: dict[str, Path] = {}
    json_files = sorted(CONTRACTS_ROOT.rglob("*.json"))

    if not json_files:
        return ["No JSON contracts found under contracts/."]

    for path in json_files:
        relative_path = path.relative_to(REPOSITORY_ROOT)
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"{relative_path}: cannot parse JSON: {exc}")
            continue

        if path.name.endswith(".schema.json"):
            if not isinstance(document, dict):
                errors.append(f"{relative_path}: schema root must be an object")
                continue

            missing = sorted(REQUIRED_SCHEMA_FIELDS - document.keys())
            if missing:
                errors.append(
                    f"{relative_path}: missing schema fields: {', '.join(missing)}"
                )

            schema_id = document.get("$id")
            if isinstance(schema_id, str):
                previous = schema_ids.get(schema_id)
                if previous is not None:
                    errors.append(
                        f"{relative_path}: duplicate $id also used by "
                        f"{previous.relative_to(REPOSITORY_ROOT)}"
                    )
                else:
                    schema_ids[schema_id] = path

        for reference in iter_references(document):
            target = reference.split("#", 1)[0]
            if not target or target.startswith(("https://", "http://")):
                continue
            target_path = (path.parent / target).resolve()
            if not target_path.is_file():
                errors.append(f"{relative_path}: unresolved local $ref: {reference}")

    if not errors:
        schema_count = sum(path.name.endswith(".schema.json") for path in json_files)
        print(f"Validated {len(json_files)} JSON file(s), including {schema_count} schema(s).")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
