"""CIVIL/DEFENSE envelope switch, territorial COP, GNSS integrity, RID hooks."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "06_autonomy"))

from dmi.envelope import EnvelopeController, EnvelopeKind
from dmi.gnss_integrity import assess_gnss_integrity
from dmi.intent_bridge import intent_to_goal_gated
from dmi.messages import IntentKind, SwarmIntent
from dmi.mission_policy import NEVER_ACTIONS, MissionPolicyGate, load_mission_profile
from dmi.rid_era import rid_should_broadcast
from dmi.territorial import CopOrigin, TerritorialCop, TerritorialTrack
from ros2.nodes.dmi_agent_soft import DmiAgentSoftNode
from ros2.nodes.envelope_soft import EnvelopeSoftNode
from ros2.nodes.gnss_integrity_soft import GnssIntegritySoftNode
from ros2.nodes.rid_soft import RidSoftNode
from soft_bus.bus import SoftBus
from soft_bus.messages import (
    TOPIC_ENVELOPE_SWITCH,
    TOPIC_GNSS,
    TOPIC_GNSS_INTEGRITY,
    TOPIC_GOAL,
    TOPIC_RID_BROADCAST,
    TOPIC_TERRITORIAL_INGEST,
    TOPIC_TERRITORIAL_TRACK,
    EnvelopeSwitchMsg,
    GnssFix,
    GnssIntegrityMsg,
    TerritorialIngestMsg,
)

PROFILES = REPO / "06_autonomy" / "mission_profiles"


def test_boot_civil_default():
    ctrl = EnvelopeController(stamp_s=1.0)
    assert ctrl.state.kind is EnvelopeKind.CIVIL
    assert ctrl.profile.profile_id == "inspection.powerline.v1"
    deny = ctrl.gate.allow_action("CHASE", stamp_s=1.0)
    assert deny.allowed is False


def test_defense_requires_operator_ack():
    ctrl = EnvelopeController(stamp_s=1.0)
    state, ok = ctrl.switch("defense", "airspace.guard.v1", operator_ack=False, stamp_s=2.0)
    assert ok is False
    assert ctrl.state.kind is EnvelopeKind.CIVIL
    assert state.reason == "defense_requires_operator_ack"


def test_switch_civil_defense_civil():
    ctrl = EnvelopeController(stamp_s=1.0)
    state, ok = ctrl.switch("defense", "isr.territory.v1", operator_ack=True, stamp_s=2.0)
    assert ok is True
    assert state.kind is EnvelopeKind.DEFENSE
    assert ctrl.profile.cop_radius_m == 50000.0
    assert ctrl.gate.allow_action("CHASE", stamp_s=2.0).allowed is False
    assert ctrl.gate.allow_action("INGEST_TERRITORIAL", stamp_s=2.0).allowed is True
    back, ok2 = ctrl.switch("civil", "perimeter.alert.v1", operator_ack=False, stamp_s=3.0)
    assert ok2 is True
    assert back.kind is EnvelopeKind.CIVIL
    assert ctrl.gate.allow_action("CHASE", stamp_s=3.0).allowed is False
    assert ctrl.gate.allow_action("INGEST_TERRITORIAL", stamp_s=3.0).allowed is False


def test_never_actions_both_envelopes():
    civil = MissionPolicyGate(load_mission_profile(PROFILES / "inspection.powerline.v1.yaml"))
    defense = MissionPolicyGate(load_mission_profile(PROFILES / "defense" / "airspace.guard.v1.yaml"))
    for gate in (civil, defense):
        for act in ("WEAPON", "FIRE_CONTROL", "JAM_GNSS", "GUIDANCE_INTENT"):
            dec = gate.allow_action(act, stamp_s=1.0)
            assert dec.allowed is False
            assert dec.reason.startswith("never:")
    assert NEVER_ACTIONS >= {"WEAPON", "JAMMER", "FIRE_CONTROL"}


def test_yaml_cannot_allow_weapon(tmp_path: Path):
    p = tmp_path / "bad.yaml"
    p.write_text(
        "profile_id: bad\nenvelope: defense\nallowed_actions: [WEAPON]\n"
        "denied_actions: []\nemergency_termination: RTL\nregistration_class: defense_hold\n"
        "rid_broadcast: false\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="NEVER_ACTIONS"):
        load_mission_profile(p)


def test_civil_must_broadcast_rid(tmp_path: Path):
    p = tmp_path / "bad_civil.yaml"
    p.write_text(
        "profile_id: badc\nenvelope: civil\nallowed_actions: [LOITER]\n"
        "rid_broadcast: false\nemergency_termination: RTL\nregistration_class: uchet\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Remote ID"):
        load_mission_profile(p)


def test_intent_gate_unchanged_civil():
    gate = MissionPolicyGate(load_mission_profile(PROFILES / "inspection.powerline.v1.yaml"))
    intent = SwarmIntent("i1", IntentKind.GOTO_XYZ, "a1", x=10, y=10, z=50, stamp_s=1.0)
    goal, dec = intent_to_goal_gated(intent, gate, stamp_s=1.0)
    assert goal is not None
    assert dec.allowed


def test_territorial_50km_not_eo():
    cop = TerritorialCop(CopOrigin(55.75, 37.62), 50_000.0)
    cop.set_friends({"bj-1"})
    inside = cop.ingest(
        track_id="t1",
        source="era_glonass",
        lat=55.75,
        lon=38.10,
        alt_m=200.0,
        ident="bj-1",
        stamp_s=1.0,
    )
    assert inside is not None
    assert inside.range_m < 50_000.0
    assert inside.affiliation == "friend"
    far = cop.ingest(
        track_id="t2",
        source="remote_id",
        lat=56.40,
        lon=37.62,
        alt_m=200.0,
        ident="unk-9",
        stamp_s=1.0,
    )
    assert far is None
    mid = cop.ingest(
        track_id="t3",
        source="adsb",
        lat=55.90,
        lon=37.62,
        alt_m=100.0,
        ident="unk-2",
        stamp_s=1.0,
    )
    assert mid is not None
    assert mid.affiliation == "unknown"
    with pytest.raises(ValueError, match="FOE"):
        TerritorialTrack(
            track_id="x",
            source="operator",
            lat=55.75,
            lon=37.62,
            alt_m=0.0,
            ident="z",
            affiliation="foe",
            range_m=1.0,
        )


def test_gnss_spoof_and_jam():
    a = GnssFix(x=0, y=0, z=0, fix_ok=True, hdop=1.0, stamp_s=1.0)
    b = GnssFix(x=500, y=0, z=0, fix_ok=True, hdop=1.0, stamp_s=2.0)
    st = assess_gnss_integrity(a, b)
    assert st.ok is False
    assert st.reason == "spoof_jump"
    lost = GnssFix(fix_ok=False, hdop=99.0, stamp_s=3.0)
    assert assess_gnss_integrity(b, lost).reason == "jam_loss"


def test_envelope_soft_switch_and_cop():
    bus = SoftBus()
    env = EnvelopeSoftNode(bus, origin=CopOrigin(55.75, 37.62), stamp_s=1.0)
    agent = DmiAgentSoftNode(bus, agent_id="bj-1")
    tracks: list = []
    bus.subscribe(TOPIC_TERRITORIAL_TRACK, tracks.append)
    bus.publish(
        TOPIC_TERRITORIAL_INGEST,
        TerritorialIngestMsg("t0", "era_glonass", 55.76, 37.63, 100.0, "x", 1.0),
    )
    assert tracks == []
    bus.publish(
        TOPIC_ENVELOPE_SWITCH,
        EnvelopeSwitchMsg("defense", "isr.territory.v1", operator_ack=True, stamp_s=2.0),
    )
    assert env.ctrl.state.kind is EnvelopeKind.DEFENSE
    assert agent.gate.profile.envelope is EnvelopeKind.DEFENSE
    agent.publish_status()
    bus.publish(
        TOPIC_TERRITORIAL_INGEST,
        TerritorialIngestMsg("t1", "era_glonass", 55.76, 37.63, 100.0, "bj-1", 2.0),
    )
    assert tracks
    assert tracks[-1].affiliation == "friend"
    assert tracks[-1].range_m < 50_000.0
    bus.publish(
        TOPIC_ENVELOPE_SWITCH,
        EnvelopeSwitchMsg("civil", "inspection.powerline.v1", operator_ack=False, stamp_s=3.0),
    )
    assert agent.gate.profile.envelope is EnvelopeKind.CIVIL
    assert agent.gate.allow_action("CHASE", stamp_s=3.0).allowed is False


def test_rid_civil_on_defense_hold():
    bus = SoftBus()
    EnvelopeSoftNode(bus, stamp_s=1.0)
    rid = RidSoftNode(bus, ident="RF-BD-ALPHA-001", min_period_s=0.0)
    seen: list = []
    bus.subscribe(TOPIC_RID_BROADCAST, seen.append)
    bus.publish(
        TOPIC_GNSS,
        GnssFix(fix_ok=True, lat_deg=55.75, lon_deg=37.62, alt_amsl_m=120.0, stamp_s=1.0, hdop=1.0),
    )
    assert seen and seen[0].dest == "era_glonass"
    assert rid_should_broadcast(rid.profile) is True
    bus.publish(
        TOPIC_ENVELOPE_SWITCH,
        EnvelopeSwitchMsg("defense", "airspace.guard.v1", operator_ack=True, stamp_s=2.0),
    )
    seen.clear()
    bus.publish(
        TOPIC_GNSS,
        GnssFix(fix_ok=True, lat_deg=55.75, lon_deg=37.62, alt_amsl_m=120.0, stamp_s=3.0, hdop=1.0),
    )
    assert seen == []
    assert rid_should_broadcast(rid.profile) is False


def test_gnss_integrity_node():
    bus = SoftBus()
    GnssIntegritySoftNode(bus)
    out: list[GnssIntegrityMsg] = []
    bus.subscribe(TOPIC_GNSS_INTEGRITY, out.append)
    bus.publish(TOPIC_GNSS, GnssFix(x=0, y=0, z=0, fix_ok=True, hdop=1.2, stamp_s=1.0))
    bus.publish(TOPIC_GNSS, GnssFix(x=0, y=0, z=0, fix_ok=True, hdop=1.2, stamp_s=1.2))
    assert out[-1].ok is True
    bus.publish(TOPIC_GNSS, GnssFix(x=400, y=0, z=0, fix_ok=True, hdop=1.2, stamp_s=1.4))
    assert out[-1].ok is False
    assert out[-1].reason == "spoof_jump"


def test_defense_does_not_publish_goal_without_intent():
    bus = SoftBus()
    EnvelopeSoftNode(bus, stamp_s=1.0)
    DmiAgentSoftNode(bus)
    goals: list = []
    bus.subscribe(TOPIC_GOAL, goals.append)
    bus.publish(
        TOPIC_ENVELOPE_SWITCH,
        EnvelopeSwitchMsg("defense", "airspace.guard.v1", operator_ack=True, stamp_s=2.0),
    )
    assert goals == []
