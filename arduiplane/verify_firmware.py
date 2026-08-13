#!/usr/bin/env python3
"""Inspect local arduiplane kit. No FC required."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
MANIFEST = json.loads((KIT / "MANIFEST.json").read_text(encoding="utf-8"))
REQUIRED_PARM = (
    "Q_ENABLE",
    "SERVO1_FUNCTION",
    "SERVO2_FUNCTION",
    "SERVO3_FUNCTION",
    "SERIAL2_PROTOCOL",
    "SERIAL2_BAUD",
    "BRD_SER2_RTSCTS",
    "SERIAL5_PROTOCOL",
    "RSSI_TYPE",
    "RC_OPTIONS",
    "ARSPD_TYPE",
    "FS_GCS_ENABL",
    "FS_LONG_ACTN",
    "GUIDED_TIMEOUT",
    "MAV3_POSITION",
    "ARMING_SKIPCHK",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_parm(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        key, _, val = s.partition(",")
        out[key.strip()] = val.strip()
    return out


def inspect_apj(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return {
        "board_id": obj.get("board_id"),
        "magic": obj.get("magic"),
        "summary": obj.get("summary"),
        "git_identity": obj.get("git_identity"),
        "image_size": obj.get("image_size"),
        "usbid": obj.get("USBID"),
        "description": obj.get("description"),
    }


def main() -> int:
    report: dict = {"ok": True, "errors": [], "files": {}}
    expect = MANIFEST["files"]["arduplane.apj"]
    apj = KIT / "arduplane.apj"
    msi = KIT / "MissionPlanner-latest.msi"
    parm = KIT / "pixhawk6c_x8.parm"

    if not parm.is_file():
        report["ok"] = False
        report["errors"].append("missing pixhawk6c_x8.parm")
    else:
        params = load_parm(parm)
        missing = [k for k in REQUIRED_PARM if k not in params]
        if missing:
            report["ok"] = False
            report["errors"].append(f"parm missing {missing}")
        if params.get("Q_ENABLE") != "0":
            report["ok"] = False
            report["errors"].append("Q_ENABLE must be 0 (not QuadPlane)")
        if params.get("SERIAL2_PROTOCOL") != "2" or params.get("SERIAL2_BAUD") != "921":
            report["ok"] = False
            report["errors"].append("TELEM2 must be MAVLink2 @ 921600")
        if params.get("SERIAL5_PROTOCOL") != "23":
            report["ok"] = False
            report["errors"].append("ELRS CRSF must be SERIAL5_PROTOCOL=23")
        if params.get("RSSI_TYPE") != "3" or params.get("RC_OPTIONS") != "8704":
            report["ok"] = False
            report["errors"].append("ELRS: RSSI_TYPE=3, RC_OPTIONS=8704 (bit9+bit13)")
        if params.get("GUIDED_TIMEOUT") != "6":
            report["ok"] = False
            report["errors"].append("GUIDED_TIMEOUT must be 6 (4.7 name, not GUID_TIMEOUT)")
        if params.get("MAV3_POSITION") != "10":
            report["ok"] = False
            report["errors"].append("MAV3_POSITION 10 Hz required for TELEM2 companion")
        report["files"]["parm"] = {"keys": len(params)}

    if not apj.is_file():
        report["files"]["arduplane.apj"] = "ABSENT (local blob, not required for software bench)"
    else:
        meta = inspect_apj(apj)
        digest = sha256(apj)
        report["files"]["arduplane.apj"] = {**meta, "sha256": digest, "bytes": apj.stat().st_size}
        checks = [
            (digest == expect["sha256"], "sha256 mismatch — not Plane 4.7.0 Pixhawk6C stable"),
            (meta["board_id"] == 56, f"board_id {meta['board_id']} != 56 Pixhawk6C"),
            (meta["summary"] == "Pixhawk6C", f"summary {meta['summary']!r}"),
            (meta["git_identity"] == MANIFEST["git_identity"], "git_identity mismatch"),
            (meta["magic"] == "APJFWv1", "not APJ firmware"),
        ]
        for ok, err in checks:
            if not ok:
                report["ok"] = False
                report["errors"].append(err)

    if msi.is_file():
        report["files"]["MissionPlanner-latest.msi"] = {
            "sha256": sha256(msi),
            "bytes": msi.stat().st_size,
            "match": sha256(msi) == MANIFEST["files"]["MissionPlanner-latest.msi"]["sha256"],
        }
    else:
        report["files"]["MissionPlanner-latest.msi"] = "ABSENT"

    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
