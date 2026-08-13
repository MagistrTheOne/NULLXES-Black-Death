#!/usr/bin/env python3
"""Pull Flight-1 facts from local kit + Plane pdef. No FC required."""

from __future__ import annotations

import json
from pathlib import Path

KIT = Path(__file__).resolve().parent
WATCH = (
    "AP_AIRSPEED_MS4525_ENABLED",
    "AP_AIRSPEED_ENABLED",
    "AP_RCPROTOCOL_CRSF_ENABLED",
    "AP_RCPROTOCOL_SBUS_ENABLED",
    "HAL_CRSF_TELEM_ENABLED",
    "AP_PLANE_OFFBOARD_GUIDED_SLEW_ENABLED",
    "HAL_NAVEKF3_AVAILABLE",
    "HAL_VISUALODOM_ENABLED",
    "AP_GPS_UBLOX_ENABLED",
    "HAL_QUADPLANE_ENABLED",
    "AP_OPENDRONEID_ENABLED",
    "MODE_GUIDED_NOGPS_ENABLED",
    "AP_DDS_ENABLED",
    "AP_NETWORKING_ENABLED",
    "AP_EXTERNAL_AHRS_ENABLED",
    "AP_SCRIPTING_ENABLED",
    "EK3_FEATURE_EXTERNAL_NAV",
    "HAL_ADSB_ENABLED",
    "AP_FENCE_ENABLED",
    "MODE_AUTOLAND_ENABLED",
)

PARM_KEYS = (
    "Q_ENABLE",
    "SERVO1_FUNCTION",
    "SERVO2_FUNCTION",
    "SERVO3_FUNCTION",
    "SERIAL1_PROTOCOL",
    "SERIAL1_BAUD",
    "SERIAL2_PROTOCOL",
    "SERIAL2_BAUD",
    "SERIAL2_OPTIONS",
    "BRD_SER2_RTSCTS",
    "SERIAL3_PROTOCOL",
    "SERIAL3_BAUD",
    "SERIAL5_PROTOCOL",
    "SERIAL5_OPTIONS",
    "ARSPD_TYPE",
    "ARSPD_USE",
    "BATT_MONITOR",
    "FS_GCS_ENABL",
    "FS_LONG_ACTN",
    "FS_SHORT_ACTN",
    "FS_EKF_THRESH",
    "GUIDED_TIMEOUT",
    "ARMING_REQUIRE",
    "ARMING_SKIPCHK",
    "ARMING_RUDDER",
    "MAV3_POSITION",
    "MAV3_EXTRA1",
    "MAV3_EXTRA2",
    "MAV3_EXT_STAT",
    "MAV3_RAW_SENS",
    "MAV_GCS_SYSID",
    "VISO_TYPE",
    "EK3_SRC1_POSXY",
)

UART_MAP = {
    "SERIAL0": "USB",
    "SERIAL1": "UART7 TELEM1 RTS/CTS — GSC",
    "SERIAL2": "UART5 TELEM2 RTS/CTS — Orin (BRD_SER2_RTSCTS=0)",
    "SERIAL3": "USART1 GPS1 — M10",
    "SERIAL4": "UART8 GPS2",
    "SERIAL5": "USART2 TELEM3 RTS/CTS — ELRS CRSF (PROTOCOL=23 RCIN)",
    "SERIAL6": "USART3 USER/Debug",
    "SERIAL7": "USB SLCAN",
    "RCIN_pin": "SBUS/PPM only — not CRSF. ELRS needs UART SERIAL5.",
}


def parse_features(path: Path) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        on = not s.startswith("!")
        name = s[1:] if not on else s
        out[name] = on
    return out


def slice_pdef(pdef: dict, keys: tuple[str, ...]) -> dict:
    flat: dict = {}
    for grp, params in pdef.items():
        if not isinstance(params, dict):
            continue
        for name, meta in params.items():
            if name in keys and isinstance(meta, dict):
                keep = {
                    k: meta[k]
                    for k in (
                        "DisplayName",
                        "Description",
                        "Values",
                        "Bitmask",
                        "Range",
                        "Units",
                    )
                    if k in meta
                }
                flat[name] = keep
    return flat


def main() -> int:
    features_path = KIT / "features.txt"
    pdef_path = KIT / "_apm.pdef.json"
    if not features_path.is_file():
        raise SystemExit("missing features.txt — curl Plane/stable/Pixhawk6C/features.txt")
    all_feat = parse_features(features_path)
    watched = {k: bool(all_feat.get(k, False)) for k in WATCH}
    missing_feat = [k for k in WATCH if k not in all_feat]
    capabilities = {
        "firmware": "ArduPlane 4.7.0 Pixhawk6C",
        "source": "https://firmware.ardupilot.org/Plane/stable/Pixhawk6C/features.txt",
        "uart_map": UART_MAP,
        "compile_flags": watched,
        "flags_absent_from_features_txt": missing_feat,
        "flight1": {
            "airspeed_ms4525": watched["AP_AIRSPEED_MS4525_ENABLED"],
            "elrs_crsf": watched["AP_RCPROTOCOL_CRSF_ENABLED"],
            "plane_guided_slew": watched["AP_PLANE_OFFBOARD_GUIDED_SLEW_ENABLED"],
            "ekf3": watched["HAL_NAVEKF3_AVAILABLE"],
            "visual_odom_slot": watched["HAL_VISUALODOM_ENABLED"],
            "opendroneid_in_fc": watched["AP_OPENDRONEID_ENABLED"],
            "guided_nogps": watched["MODE_GUIDED_NOGPS_ENABLED"],
            "quadplane_compiled": watched["HAL_QUADPLANE_ENABLED"],
        },
        "nullxes": {
            "rid": "GSC/Python — FC OpenDroneID compiled OUT",
            "guided": "GUIDED only — GUIDED_NOGPS compiled OUT",
            "q_enable": "keep 0 even though QuadPlane is in the binary",
            "vio": "VISO_TYPE slot exists; Flight-1 hop does not require it",
        },
    }
    (KIT / "capabilities.json").write_text(
        json.dumps(capabilities, indent=2) + "\n", encoding="utf-8"
    )

    params_ref = {
        "pdef_source": "https://autotest.ardupilot.org/Parameters/ArduPlane/apm.pdef.json",
        "pdef_note": "autotest dump 2026-08-08; firmware blob 2026-07-21. Live PARAM_VALUE from FC wins after USB.",
        "params": {},
    }
    if pdef_path.is_file():
        pdef = json.loads(pdef_path.read_text(encoding="utf-8"))
        params_ref["params"] = slice_pdef(pdef, PARM_KEYS)
        missing = [k for k in PARM_KEYS if k not in params_ref["params"]]
        params_ref["missing_in_pdef"] = missing
    else:
        params_ref["missing_in_pdef"] = list(PARM_KEYS)
    (KIT / "params_ref.json").write_text(
        json.dumps(params_ref, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "capabilities": str(KIT / "capabilities.json"),
                "params_ref_keys": len(params_ref["params"]),
                "opendroneid_in_fc": capabilities["flight1"]["opendroneid_in_fc"],
                "guided_nogps": capabilities["flight1"]["guided_nogps"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
