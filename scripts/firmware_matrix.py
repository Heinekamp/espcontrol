#!/usr/bin/env python3
"""Generate GitHub Actions firmware build matrices from devices/manifest.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEVICE_MANIFEST = ROOT / "devices" / "manifest.json"
VALID_CHIP_FAMILIES = {"ESP32-P4", "ESP32-S3"}


class FirmwareMatrixError(RuntimeError):
    pass


def load_manifest(path: Path = DEVICE_MANIFEST) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError as exc:
        raise FirmwareMatrixError(f"manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise FirmwareMatrixError(f"{path} is not valid JSON: {exc}") from exc

    devices = data.get("devices")
    if not isinstance(devices, dict) or not devices:
        raise FirmwareMatrixError(f"{path} must contain a non-empty devices object")
    return data


def chip_family(slug: str, device: Any) -> str:
    if not isinstance(device, dict):
        raise FirmwareMatrixError(f"{slug}: device entry must be an object")

    firmware = device.get("firmware")
    if not isinstance(firmware, dict):
        raise FirmwareMatrixError(f"{slug}: missing firmware object")

    build = firmware.get("build")
    if not isinstance(build, dict):
        raise FirmwareMatrixError(f"{slug}: missing firmware.build object")

    chip = build.get("chipFamily")
    if not isinstance(chip, str) or not chip:
        raise FirmwareMatrixError(f"{slug}: missing firmware.build.chipFamily")
    if chip not in VALID_CHIP_FAMILIES:
        valid = ", ".join(sorted(VALID_CHIP_FAMILIES))
        raise FirmwareMatrixError(f"{slug}: firmware.build.chipFamily must be one of {valid}")
    return chip


def release_matrix(data: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    devices = data["devices"]
    return {
        "include": [
            {
                "device": slug,
                "slug": slug,
                "chip": chip_family(slug, device),
            }
            for slug, device in devices.items()
        ]
    }


def nightly_matrix(data: dict[str, Any]) -> dict[str, list[str]]:
    return {"slug": list(data["devices"].keys())}


def write_json(data: Any) -> None:
    json.dump(data, sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEVICE_MANIFEST,
        help="Path to devices/manifest.json",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    release = sub.add_parser("release", help="Print the release workflow matrix JSON")
    release.set_defaults(matrix=release_matrix)

    nightly = sub.add_parser("nightly", help="Print the nightly workflow matrix JSON")
    nightly.set_defaults(matrix=nightly_matrix)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        write_json(args.matrix(load_manifest(args.manifest)))
    except FirmwareMatrixError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
