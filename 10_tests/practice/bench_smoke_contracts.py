"""Static practice / DMI contracts — no sensor invention.

Run: python 10_tests/practice/bench_smoke_contracts.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTO = ROOT / "06_autonomy"
sys.path.insert(0, str(AUTO))

REQUIRED_DMI_TOPICS = [
    "/bd/dmi/intent",
    "/bd/dmi/task_offer",
    "/bd/dmi/task_claim",
    "/bd/dmi/agent_status",
    "/bd/dmi/world_fact",
    "/bd/dmi/swarm_health",
]

L0_SWARM_BLIND_PATHS = [
    AUTO / "ros2" / "nodes" / "l0_soft.py",
    AUTO / "control" / "inner_loop_py.py",
    ROOT / "05_avionics" / "flight_software" / "inner_loop.cpp",
    ROOT / "05_avionics" / "flight_software" / "inner_loop.hpp",
]


def _module_imports_dmi(path: Path) -> list[str]:
    if not path.is_file():
        return [f"missing:{path}"]
    if path.suffix == ".py":
        tree = ast.parse(path.read_text(encoding="utf-8"))
        hits: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "dmi" or alias.name.startswith("dmi."):
                        hits.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod == "dmi" or mod.startswith("dmi."):
                    hits.append(mod)
        return hits
    text = path.read_text(encoding="utf-8", errors="ignore")
    if "dmi" in text.lower() and "/bd/dmi" in text:
        return ["text-ref-/bd/dmi"]
    if "#include" in text and "dmi" in text.lower():
        return ["cpp-dmi-ref"]
    return []


def main() -> int:
    from dmi import messages as dmi_msg

    topic_consts = [
        dmi_msg.TOPIC_DMI_INTENT,
        dmi_msg.TOPIC_DMI_TASK_OFFER,
        dmi_msg.TOPIC_DMI_TASK_CLAIM,
        dmi_msg.TOPIC_DMI_AGENT_STATUS,
        dmi_msg.TOPIC_DMI_WORLD_FACT,
        dmi_msg.TOPIC_DMI_SWARM_HEALTH,
    ]
    for expected, actual in zip(REQUIRED_DMI_TOPICS, topic_consts, strict=True):
        if actual != expected:
            print(f"FAIL topic mismatch {expected} != {actual}")
            return 1

    twin = (ROOT / "07_simulation" / "digital_twin" / "topic_map.yaml").read_text(
        encoding="utf-8"
    )
    for t in REQUIRED_DMI_TOPICS:
        if t not in twin:
            print(f"FAIL twin map missing {t}")
            return 1

    for path in L0_SWARM_BLIND_PATHS:
        hits = _module_imports_dmi(path)
        if hits:
            print(f"FAIL L0 swarm-blind violated in {path}: {hits}")
            return 1

    print("OK practice/DMI contracts + L0 swarm-blind")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
