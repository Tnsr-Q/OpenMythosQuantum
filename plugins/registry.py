#!/usr/bin/env python3
"""
Katopu Plugin Registry (ACT-020)
================================

Capability-aware, hash-verified plugin registry.

Discovers plugin descriptors (`plugin.json`) in the `plugins/` directory,
validates each descriptor against `descriptor.schema.json`, and verifies
the integrity of the entrypoint file via SHA-256 (extending the ACT-019
freeze primitive to non-JSON artifacts — see `REGISTRY_SPEC.md`).

Stdlib-only: ``json``, ``hashlib``, ``hmac``, ``pathlib``, ``argparse``,
``re``, ``sys``, ``importlib.util`` (used only if a caller explicitly
loads a plugin module).

Public API
----------

- ``Registry.load(plugins_dir)``           — discover + validate descriptors.
- ``Registry.list_plugins(lifecycle=None)``
- ``Registry.get(plugin_id)``
- ``Registry.get_by_capability(capability)``
- ``Registry.verify_integrity(plugin_id=None)``
- ``Registry.set_lifecycle(plugin_id, new_state)``

CLI
---

::

    python3 registry.py list [--lifecycle=STATE]
    python3 registry.py find --capability=CAP
    python3 registry.py verify [--id=PLUGIN_ID]
    python3 registry.py show --id=PLUGIN_ID

Exit codes: ``0`` success, ``1`` verification/logic failure, ``2`` usage.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

# --------------------------------------------------------------------------- #
# Minimal JSON Schema Draft 2020-12 validator (scoped to descriptor.schema.json)
# --------------------------------------------------------------------------- #

class SchemaValidationError(Exception):
    """Raised when a descriptor fails schema validation."""


def _validate(instance: Any, schema: dict, path: str = "$") -> list[str]:
    """Return a list of validation errors; empty list means valid.

    Supports the subset of JSON Schema used by ``descriptor.schema.json``:
    type, properties, required, additionalProperties=false, enum, pattern,
    minLength, maxLength, minItems, maxItems, uniqueItems, items, minimum.
    """
    errors: list[str] = []

    t = schema.get("type")
    if t == "object":
        if not isinstance(instance, dict):
            errors.append(f"{path}: expected object, got {type(instance).__name__}")
            return errors
        for req in schema.get("required", []):
            if req not in instance:
                errors.append(f"{path}: missing required property '{req}'")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in instance:
                if key not in props:
                    errors.append(f"{path}: additional property '{key}' not allowed")
        for key, subschema in props.items():
            if key in instance:
                errors.extend(_validate(instance[key], subschema, f"{path}.{key}"))
    elif t == "array":
        if not isinstance(instance, list):
            errors.append(f"{path}: expected array, got {type(instance).__name__}")
            return errors
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: array has {len(instance)} items, minimum {schema['minItems']}")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{path}: array has {len(instance)} items, maximum {schema['maxItems']}")
        if schema.get("uniqueItems") and len(instance) != len({json.dumps(x, sort_keys=True) for x in instance}):
            errors.append(f"{path}: array items must be unique")
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(instance):
                errors.extend(_validate(item, item_schema, f"{path}[{i}]"))
    elif t == "string":
        if not isinstance(instance, str):
            errors.append(f"{path}: expected string, got {type(instance).__name__}")
            return errors
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: string shorter than minLength {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append(f"{path}: string longer than maxLength {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{path}: string does not match pattern {schema['pattern']!r}")
        if "enum" in schema and instance not in schema["enum"]:
            errors.append(f"{path}: value {instance!r} not in enum {schema['enum']}")
    elif t == "integer":
        # bool is a subclass of int in Python; reject explicitly
        if not isinstance(instance, int) or isinstance(instance, bool):
            errors.append(f"{path}: expected integer, got {type(instance).__name__}")
            return errors
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: value {instance} < minimum {schema['minimum']}")

    # enum at any type
    if "enum" in schema and t is None and instance not in schema["enum"]:
        errors.append(f"{path}: value {instance!r} not in enum {schema['enum']}")

    return errors


def validate_descriptor(descriptor: dict, schema: dict) -> None:
    """Raise ``SchemaValidationError`` with all validation errors, if any."""
    errors = _validate(descriptor, schema)
    if errors:
        raise SchemaValidationError(
            "descriptor failed schema validation:\n  - " + "\n  - ".join(errors)
        )


# --------------------------------------------------------------------------- #
# Lifecycle
# --------------------------------------------------------------------------- #

LIFECYCLE_STATES = {"registered", "active", "deprecated", "revoked"}

_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "registered": {"active", "revoked"},
    "active": {"deprecated", "revoked"},
    "deprecated": {"active", "revoked"},
    "revoked": set(),
}


def is_valid_transition(src: str, dst: str) -> bool:
    """Return True iff transitioning from *src* to *dst* is allowed."""
    if src not in LIFECYCLE_STATES or dst not in LIFECYCLE_STATES:
        return False
    return dst in _ALLOWED_TRANSITIONS[src]


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

@dataclass
class PluginRecord:
    """One entry in the registry."""
    id: str
    descriptor: dict
    descriptor_path: Path
    entrypoint_path: Path

    @property
    def capabilities(self) -> list[str]:
        return list(self.descriptor.get("capabilities", []))

    @property
    def version(self) -> str:
        return self.descriptor["version"]

    @property
    def lifecycle(self) -> str:
        return self.descriptor["lifecycle"]

    @property
    def integrity_hash(self) -> str:
        return self.descriptor["integrity"]["entrypoint"]


class Registry:
    """In-memory plugin registry."""

    def __init__(self, plugins_dir: Path, schema: dict) -> None:
        self.plugins_dir = Path(plugins_dir)
        self.schema = schema
        self._records: dict[str, PluginRecord] = {}

    # ------------------------------------------------------------------ load
    @classmethod
    def load(cls, plugins_dir: str | Path, schema_path: str | Path | None = None) -> "Registry":
        """Discover + validate every ``plugin.json`` under *plugins_dir*."""
        plugins_dir = Path(plugins_dir)
        schema_path = Path(schema_path) if schema_path else plugins_dir / "descriptor.schema.json"
        with open(schema_path, "r", encoding="utf-8") as fh:
            schema = json.load(fh)
        reg = cls(plugins_dir, schema)
        reg.load_descriptors()
        return reg

    def load_descriptors(self) -> None:
        """(Re)populate the registry by scanning for ``plugin.json`` files."""
        self._records.clear()
        for child in sorted(self.plugins_dir.iterdir()):
            if not child.is_dir():
                continue
            desc_path = child / "plugin.json"
            if not desc_path.is_file():
                continue
            with open(desc_path, "r", encoding="utf-8") as fh:
                descriptor = json.load(fh)
            validate_descriptor(descriptor, self.schema)
            pid = descriptor["id"]
            if pid in self._records:
                raise ValueError(f"duplicate plugin id: {pid!r}")
            entrypoint_path = child / descriptor["entrypoint"]["path"]
            if not entrypoint_path.is_file():
                raise FileNotFoundError(
                    f"plugin {pid!r}: entrypoint file missing: {entrypoint_path}"
                )
            self._records[pid] = PluginRecord(
                id=pid,
                descriptor=descriptor,
                descriptor_path=desc_path,
                entrypoint_path=entrypoint_path,
            )

    # ------------------------------------------------------------------ query
    def list_plugins(self, lifecycle: str | None = None) -> list[PluginRecord]:
        recs = list(self._records.values())
        if lifecycle is not None:
            recs = [r for r in recs if r.lifecycle == lifecycle]
        return sorted(recs, key=lambda r: r.id)

    def get(self, plugin_id: str) -> PluginRecord:
        if plugin_id not in self._records:
            raise KeyError(f"plugin not found: {plugin_id!r}")
        return self._records[plugin_id]

    def get_by_capability(self, capability: str) -> list[PluginRecord]:
        """Return active/registered/deprecated plugins exposing *capability*.

        Revoked plugins are never returned (see REGISTRY_SPEC §6).
        """
        return [
            rec
            for rec in self.list_plugins()
            if capability in rec.capabilities and rec.lifecycle != "revoked"
        ]

    # -------------------------------------------------------------- integrity
    def verify_integrity(self, plugin_id: str | None = None) -> dict[str, bool]:
        """Verify on-disk entrypoint bytes match recorded SHA-256.

        Returns a dict mapping plugin_id → True/False.
        """
        targets: Iterable[PluginRecord]
        if plugin_id is None:
            targets = self._records.values()
        else:
            targets = [self.get(plugin_id)]
        results: dict[str, bool] = {}
        for rec in targets:
            recorded = rec.integrity_hash
            if not recorded.startswith("sha256:"):
                results[rec.id] = False
                continue
            expected_hex = recorded[len("sha256:"):]
            with open(rec.entrypoint_path, "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
            results[rec.id] = hmac.compare_digest(digest, expected_hex)
        return results

    # -------------------------------------------------------------- lifecycle
    def set_lifecycle(self, plugin_id: str, new_state: str) -> None:
        """In-memory lifecycle transition (not persisted to disk)."""
        rec = self.get(plugin_id)
        if not is_valid_transition(rec.lifecycle, new_state):
            raise ValueError(
                f"invalid lifecycle transition for {plugin_id!r}: "
                f"{rec.lifecycle} → {new_state}"
            )
        rec.descriptor["lifecycle"] = new_state


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _format_plugin_row(rec: PluginRecord) -> str:
    caps = ",".join(rec.capabilities)
    return f"{rec.id:22s} {rec.version:10s} {rec.lifecycle:11s} [{caps}]"


def _cmd_list(reg: Registry, args: argparse.Namespace) -> int:
    records = reg.list_plugins(lifecycle=args.lifecycle)
    if not records:
        print("(no plugins)")
        return 0
    print(f"{'ID':22s} {'VERSION':10s} {'LIFECYCLE':11s} CAPABILITIES")
    for rec in records:
        print(_format_plugin_row(rec))
    return 0


def _cmd_find(reg: Registry, args: argparse.Namespace) -> int:
    matches = reg.get_by_capability(args.capability)
    if not matches:
        print(f"(no plugins expose capability {args.capability!r})")
        return 1
    for rec in matches:
        print(_format_plugin_row(rec))
    return 0


def _cmd_verify(reg: Registry, args: argparse.Namespace) -> int:
    results = reg.verify_integrity(plugin_id=args.id)
    all_ok = True
    for pid, ok in results.items():
        status = "OK" if ok else "FAIL"
        print(f"{status:5s} {pid}")
        if not ok:
            all_ok = False
    return 0 if all_ok else 1


def _cmd_show(reg: Registry, args: argparse.Namespace) -> int:
    rec = reg.get(args.id)
    print(json.dumps(rec.descriptor, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="registry",
        description="Katopu plugin registry CLI (ACT-020).",
    )
    parser.add_argument(
        "--plugins-dir",
        default=str(Path(__file__).resolve().parent),
        help="Path to the plugins directory (default: directory containing this script).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List all plugins.")
    p_list.add_argument("--lifecycle", choices=sorted(LIFECYCLE_STATES))

    p_find = sub.add_parser("find", help="Find plugins by capability.")
    p_find.add_argument("--capability", required=True)

    p_verify = sub.add_parser("verify", help="Verify entrypoint integrity.")
    p_verify.add_argument("--id", default=None)

    p_show = sub.add_parser("show", help="Show a descriptor.")
    p_show.add_argument("--id", required=True)

    args = parser.parse_args(argv)

    try:
        reg = Registry.load(args.plugins_dir)
    except (SchemaValidationError, ValueError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    dispatch = {
        "list": _cmd_list,
        "find": _cmd_find,
        "verify": _cmd_verify,
        "show": _cmd_show,
    }
    try:
        return dispatch[args.cmd](reg, args)
    except KeyError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
