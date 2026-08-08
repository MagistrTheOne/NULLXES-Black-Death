"""Onboard SceneAnalyst — rules + scores, no LLM (ADR-004/005)."""

from __future__ import annotations

from dataclasses import dataclass

from dmi.messages import WorldFact
from soft_bus.messages import SceneAlert, SceneAssessment


@dataclass(frozen=True)
class AnalystConfig:
    uav_critical_conf: float = 0.35
    fire_critical_conf: float = 0.30
    human_warn_conf: float = 0.40
    vehicle_warn_conf: float = 0.45


def analyze_scene(
    facts: list[WorldFact],
    *,
    stamp_s: float,
    link_ok: bool = True,
    cfg: AnalystConfig | None = None,
) -> SceneAssessment:
    cfg = cfg or AnalystConfig()
    alerts: list[SceneAlert] = []
    suggested = "ALERT_ONLY"

    for f in facts:
        if f.kind == "uav" and f.confidence >= cfg.uav_critical_conf:
            alerts.append(
                SceneAlert(
                    severity="critical",
                    kind=f.kind,
                    fact_id=f.fact_id,
                    summary=f"UAV track {f.fact_id} conf={f.confidence:.2f}",
                )
            )
            suggested = "GOTO_XYZ" if link_ok else "LOITER"
        elif f.kind == "fire" and f.confidence >= cfg.fire_critical_conf:
            alerts.append(
                SceneAlert(
                    severity="critical",
                    kind=f.kind,
                    fact_id=f.fact_id,
                    summary=f"Fire fact {f.fact_id} conf={f.confidence:.2f}",
                )
            )
            if suggested == "ALERT_ONLY":
                suggested = "LOITER"
        elif f.kind == "human" and f.confidence >= cfg.human_warn_conf:
            alerts.append(
                SceneAlert(
                    severity="warn",
                    kind=f.kind,
                    fact_id=f.fact_id,
                    summary=f"Human {f.fact_id} conf={f.confidence:.2f}",
                )
            )
        elif f.kind == "vehicle" and f.confidence >= cfg.vehicle_warn_conf:
            alerts.append(
                SceneAlert(
                    severity="warn",
                    kind=f.kind,
                    fact_id=f.fact_id,
                    summary=f"Vehicle {f.fact_id} conf={f.confidence:.2f}",
                )
            )
        elif f.kind == "power_line" and f.confidence >= 0.35:
            alerts.append(
                SceneAlert(
                    severity="warn",
                    kind=f.kind,
                    fact_id=f.fact_id,
                    summary=f"Power line {f.fact_id}",
                )
            )

    if not link_ok and suggested == "GOTO_XYZ":
        suggested = "LOITER"

    if not alerts:
        summary = "scene clear"
    else:
        summary = f"{len(alerts)} alert(s); top={alerts[0].severity}:{alerts[0].kind}"

    return SceneAssessment(
        stamp_s=stamp_s,
        summary=summary,
        alerts=alerts,
        suggested_intent_kind=suggested,
        link_ok=link_ok,
    )
