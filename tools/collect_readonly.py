#!/usr/bin/env python3
"""Collect an allowlisted, read-only Apple device inventory without identifiers."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path


def walk(value):
    if isinstance(value, dict):
        if isinstance(value.get("hardwareProperties"), dict) and isinstance(value.get("deviceProperties"), dict):
            yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def first(mapping: dict, *keys: str):
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, (str, int, bool)):
            return value
    return None


def sanitize(payload: dict) -> dict:
    devices = []
    seen = set()
    for item in walk(payload):
        hardware = item.get("hardwareProperties", {})
        device = item.get("deviceProperties", {})
        connection = item.get("connectionProperties", {}) if isinstance(item.get("connectionProperties"), dict) else {}
        record = {
            "model": first(hardware, "productType", "marketingName"),
            "board": first(hardware, "hardwareModel", "boardId"),
            "platform": first(hardware, "platform"),
            "os_version": first(device, "osVersionNumber", "osVersion"),
            "os_build": first(device, "osBuildUpdate", "buildVersion"),
            "transport": first(connection, "transportType"),
            "developer_mode": first(device, "developerModeStatus"),
        }
        record = {key: value for key, value in record.items() if value is not None}
        key = tuple(sorted(record.items()))
        if record and key not in seen:
            seen.add(key)
            devices.append(record)
    return {"schema_version": 1, "source": "xcrun devicectl list devices (allowlisted fields only)", "devices": devices}


def collect() -> dict:
    with tempfile.TemporaryDirectory(prefix="omarchy-ipad-inventory-") as directory:
        output = Path(directory) / "devices.json"
        subprocess.run(["xcrun", "devicectl", "list", "devices", "--json-output", str(output)], check=True)
        return json.loads(output.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="sanitize a saved devicectl JSON file instead of querying devices")
    parser.add_argument("--output", type=Path, help="write sanitized JSON to this path; default is stdout")
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8")) if args.input else collect()
    result = json.dumps(sanitize(payload), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
