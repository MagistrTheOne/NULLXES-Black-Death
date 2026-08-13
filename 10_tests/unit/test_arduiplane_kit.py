"""Local ArduPlane kit: params always; APJ hash if blob present."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "arduiplane"))

from verify_firmware import KIT, REQUIRED_PARM, inspect_apj, load_parm, main, sha256  # noqa: E402


def test_parm_flight1_uart_and_wing():
    params = load_parm(KIT / "pixhawk6c_x8.parm")
    for key in REQUIRED_PARM:
        assert key in params, key
    assert params["Q_ENABLE"] == "0"
    assert params["SERVO1_FUNCTION"] == "77"
    assert params["SERVO2_FUNCTION"] == "78"
    assert params["SERVO3_FUNCTION"] == "70"
    assert params["SERIAL2_PROTOCOL"] == "2"
    assert params["SERIAL2_BAUD"] == "921"
    assert params["BRD_SER2_RTSCTS"] == "0"
    assert params["SERIAL5_PROTOCOL"] == "23"
    assert params["RSSI_TYPE"] == "3"
    assert params["RC_OPTIONS"] == "8704"
    assert params["ARSPD_TYPE"] == "1"
    assert params["FS_LONG_ACTN"] == "1"
    assert params["GUIDED_TIMEOUT"] == "6"
    assert params["MAV3_POSITION"] == "10"


def test_capabilities_opendroneid_out_guided_in():
    cap = json.loads((KIT / "capabilities.json").read_text(encoding="utf-8"))
    assert cap["flight1"]["airspeed_ms4525"] is True
    assert cap["flight1"]["elrs_crsf"] is True
    assert cap["flight1"]["plane_guided_slew"] is True
    assert cap["flight1"]["opendroneid_in_fc"] is False
    assert cap["flight1"]["guided_nogps"] is False


def test_manifest_matches_verify_exit():
    assert main() == 0


def test_apj_pixhawk6c_if_present():
    apj = KIT / "arduplane.apj"
    if not apj.is_file():
        return
    meta = inspect_apj(apj)
    man = json.loads((KIT / "MANIFEST.json").read_text(encoding="utf-8"))
    expect = man["files"]["arduplane.apj"]
    assert meta["board_id"] == 56
    assert meta["summary"] == "Pixhawk6C"
    assert meta["git_identity"] == "1511f271"
    assert sha256(apj) == expect["sha256"]
