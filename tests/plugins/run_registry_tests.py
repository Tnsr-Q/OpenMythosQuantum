#!/usr/bin/env python3
"""
Deterministic tests for the ACT-020 plugin registry.

Test cases
----------

- TEST-REG-001: descriptor schema validates both existing plugin descriptors
                (and rejects mutated descriptors).
- TEST-REG-002: registry.py lists exactly 2 plugins.
- TEST-REG-003: registry verifies integrity of both plugins (matching SHA-256).
- TEST-REG-004: registry rejects tampered entrypoint bytes (mutation → fail).
- TEST-REG-005: capability lookup finds sha256_verifier by "webhook.verify.sha256".
- TEST-REG-006: capability lookup finds freeze_snapshot by "hash.freeze.sha256".
- TEST-REG-007: lifecycle transitions are enforced (valid allowed, invalid rejected).

Exit 0 on success, 1 on any failure.
"""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "plugins"))

import registry as reg_mod  # noqa: E402

PLUGINS_DIR = ROOT / "plugins"
SCHEMA_PATH = PLUGINS_DIR / "descriptor.schema.json"

PASS = 0
FAIL = 0


def _check(label: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"PASS  {label}")
    else:
        FAIL += 1
        print(f"FAIL  {label}  {detail}")


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def load_schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_descriptor(plugin_id: str) -> dict:
    with open(PLUGINS_DIR / plugin_id / "plugin.json", "r", encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- #
# TEST-REG-001 — schema validation (valid + invalid cases)
# --------------------------------------------------------------------------- #

def test_reg_001_schema_validation() -> None:
    section("TEST-REG-001: descriptor schema validates both existing plugins")
    schema = load_schema()

    for pid in ("sha256_verifier", "freeze_snapshot"):
        desc = load_descriptor(pid)
        try:
            reg_mod.validate_descriptor(desc, schema)
            _check(f"{pid}: valid descriptor passes schema", True)
        except reg_mod.SchemaValidationError as e:
            _check(f"{pid}: valid descriptor passes schema", False, str(e))

    # invalid: missing required field
    bad = load_descriptor("sha256_verifier")
    del bad["author"]
    try:
        reg_mod.validate_descriptor(bad, schema)
        _check("missing 'author' is rejected", False, "validator accepted descriptor lacking 'author'")
    except reg_mod.SchemaValidationError:
        _check("missing 'author' is rejected", True)

    # invalid: additional property
    bad = load_descriptor("sha256_verifier")
    bad["evil_extra_field"] = "nope"
    try:
        reg_mod.validate_descriptor(bad, schema)
        _check("additionalProperties=false rejects extras", False, "extra property accepted")
    except reg_mod.SchemaValidationError:
        _check("additionalProperties=false rejects extras", True)

    # invalid: bad capability shape (single segment)
    bad = load_descriptor("sha256_verifier")
    bad["capabilities"] = ["nodot"]
    try:
        reg_mod.validate_descriptor(bad, schema)
        _check("malformed capability rejected", False)
    except reg_mod.SchemaValidationError:
        _check("malformed capability rejected", True)

    # invalid: bad integrity hash (wrong prefix)
    bad = load_descriptor("sha256_verifier")
    bad["integrity"]["entrypoint"] = "md5:" + "0" * 64
    try:
        reg_mod.validate_descriptor(bad, schema)
        _check("bad integrity prefix rejected", False)
    except reg_mod.SchemaValidationError:
        _check("bad integrity prefix rejected", True)

    # invalid: bad lifecycle value
    bad = load_descriptor("sha256_verifier")
    bad["lifecycle"] = "unknown_state"
    try:
        reg_mod.validate_descriptor(bad, schema)
        _check("invalid lifecycle value rejected", False)
    except reg_mod.SchemaValidationError:
        _check("invalid lifecycle value rejected", True)


# --------------------------------------------------------------------------- #
# TEST-REG-002 — registry lists 2 plugins
# --------------------------------------------------------------------------- #

def test_reg_002_list() -> None:
    section("TEST-REG-002: registry lists 2 plugins")
    reg = reg_mod.Registry.load(PLUGINS_DIR)
    plugins = reg.list_plugins()
    ids = [p.id for p in plugins]
    _check(f"registry contains exactly 2 plugins ({ids})", len(plugins) == 2, f"got {len(plugins)}")
    _check("sha256_verifier is registered", "sha256_verifier" in ids)
    _check("freeze_snapshot is registered", "freeze_snapshot" in ids)


# --------------------------------------------------------------------------- #
# TEST-REG-003 — integrity verification succeeds
# --------------------------------------------------------------------------- #

def test_reg_003_verify_integrity() -> None:
    section("TEST-REG-003: registry verifies integrity of both plugins")
    reg = reg_mod.Registry.load(PLUGINS_DIR)
    results = reg.verify_integrity()
    _check("verify returns result for each plugin",
           set(results.keys()) == {"sha256_verifier", "freeze_snapshot"})
    for pid, ok in results.items():
        _check(f"{pid}: entrypoint bytes match recorded SHA-256", ok)


# --------------------------------------------------------------------------- #
# TEST-REG-004 — tamper detection
# --------------------------------------------------------------------------- #

def test_reg_004_tamper_detection() -> None:
    section("TEST-REG-004: registry rejects tampered entrypoint")
    schema = load_schema()

    # Build a scratch registry where we can safely mutate the entrypoint
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_plugins = Path(tmpdir)
        # copy both real plugins and the schema into the tmp dir
        for pid in ("sha256_verifier", "freeze_snapshot"):
            shutil.copytree(PLUGINS_DIR / pid, tmp_plugins / pid)
        shutil.copy(SCHEMA_PATH, tmp_plugins / "descriptor.schema.json")

        reg = reg_mod.Registry.load(tmp_plugins)
        # baseline: both OK
        baseline = reg.verify_integrity()
        _check("baseline: both plugins verified", all(baseline.values()))

        # mutation A: flip bytes in sha256_verifier/entrypoint.py
        ep = tmp_plugins / "sha256_verifier" / "entrypoint.py"
        ep.write_bytes(ep.read_bytes() + b"\n# tampered\n")
        reg2 = reg_mod.Registry.load(tmp_plugins)
        r2 = reg2.verify_integrity()
        _check("tampered entrypoint bytes → verify fails",
               r2["sha256_verifier"] is False and r2["freeze_snapshot"] is True,
               f"got {r2}")

        # mutation B: forge the recorded hash in the descriptor to match garbage
        #            — this should pass schema validation but STILL fail real verification
        #              (because forged hash ≠ actual SHA-256 of on-disk file)
        forged = load_descriptor("freeze_snapshot")
        forged["integrity"]["entrypoint"] = "sha256:" + "f" * 64
        (tmp_plugins / "freeze_snapshot" / "plugin.json").write_text(
            json.dumps(forged, indent=2), encoding="utf-8"
        )
        reg3 = reg_mod.Registry.load(tmp_plugins)
        r3 = reg3.verify_integrity(plugin_id="freeze_snapshot")
        _check("forged integrity hash → verify fails",
               r3["freeze_snapshot"] is False, f"got {r3}")


# --------------------------------------------------------------------------- #
# TEST-REG-005 / TEST-REG-006 — capability discovery
# --------------------------------------------------------------------------- #

def test_reg_005_capability_sha256() -> None:
    section("TEST-REG-005: capability lookup finds sha256_verifier")
    reg = reg_mod.Registry.load(PLUGINS_DIR)
    matches = reg.get_by_capability("webhook.verify.sha256")
    _check("webhook.verify.sha256 → 1 plugin", len(matches) == 1, f"got {len(matches)}")
    _check("that plugin is sha256_verifier",
           len(matches) == 1 and matches[0].id == "sha256_verifier")

    # unknown capability → empty
    none = reg.get_by_capability("nonexistent.capability")
    _check("unknown capability → empty list", none == [])


def test_reg_006_capability_freeze() -> None:
    section("TEST-REG-006: capability lookup finds freeze_snapshot")
    reg = reg_mod.Registry.load(PLUGINS_DIR)

    for cap in ("hash.freeze.sha256", "hash.canonicalize"):
        matches = reg.get_by_capability(cap)
        _check(f"{cap} → 1 plugin", len(matches) == 1, f"got {len(matches)}")
        _check(f"{cap} → freeze_snapshot",
               len(matches) == 1 and matches[0].id == "freeze_snapshot")


# --------------------------------------------------------------------------- #
# TEST-REG-007 — lifecycle transitions
# --------------------------------------------------------------------------- #

def test_reg_007_lifecycle() -> None:
    section("TEST-REG-007: lifecycle transitions enforced")

    # pure transition-table checks (no disk I/O)
    valid_cases = [
        ("registered", "active"),
        ("registered", "revoked"),
        ("active", "deprecated"),
        ("active", "revoked"),
        ("deprecated", "active"),
        ("deprecated", "revoked"),
    ]
    invalid_cases = [
        ("revoked", "active"),
        ("revoked", "registered"),
        ("active", "registered"),
        ("deprecated", "registered"),
        ("registered", "deprecated"),
        ("active", "unknown"),
        ("bogus", "active"),
    ]
    for src, dst in valid_cases:
        _check(f"valid: {src} → {dst}", reg_mod.is_valid_transition(src, dst))
    for src, dst in invalid_cases:
        _check(f"invalid: {src} → {dst} rejected",
               not reg_mod.is_valid_transition(src, dst))

    # registry integration: set_lifecycle enforces the same table
    reg = reg_mod.Registry.load(PLUGINS_DIR)
    rec = reg.get("sha256_verifier")
    original = rec.lifecycle
    _check("baseline lifecycle == 'active'", original == "active")

    # active → deprecated is allowed
    reg.set_lifecycle("sha256_verifier", "deprecated")
    _check("active → deprecated applied in-memory", reg.get("sha256_verifier").lifecycle == "deprecated")

    # deprecated → active is allowed (reactivation)
    reg.set_lifecycle("sha256_verifier", "active")
    _check("deprecated → active applied", reg.get("sha256_verifier").lifecycle == "active")

    # active → registered should be rejected
    try:
        reg.set_lifecycle("sha256_verifier", "registered")
        _check("active → registered rejected", False, "no exception raised")
    except ValueError:
        _check("active → registered rejected", True)

    # revoked is terminal: set it, then try to leave
    reg.set_lifecycle("sha256_verifier", "revoked")
    _check("active → revoked applied", reg.get("sha256_verifier").lifecycle == "revoked")
    try:
        reg.set_lifecycle("sha256_verifier", "active")
        _check("revoked is terminal", False, "allowed exit from revoked")
    except ValueError:
        _check("revoked is terminal", True)

    # revoked plugins are excluded from capability discovery
    matches = reg.get_by_capability("webhook.verify.sha256")
    _check("revoked plugin excluded from capability discovery",
           all(m.id != "sha256_verifier" for m in matches))


# --------------------------------------------------------------------------- #
# Entry
# --------------------------------------------------------------------------- #

def main() -> int:
    test_reg_001_schema_validation()
    test_reg_002_list()
    test_reg_003_verify_integrity()
    test_reg_004_tamper_detection()
    test_reg_005_capability_sha256()
    test_reg_006_capability_freeze()
    test_reg_007_lifecycle()

    print()
    print(f"Summary: {PASS} passed, {FAIL} failed")
    if FAIL == 0:
        print("ALL REGISTRY TESTS PASSED")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
