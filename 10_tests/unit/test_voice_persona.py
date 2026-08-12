"""NULLXES GSC voice persona — CIVIL TTS, DEFENSE sting + line."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "06_autonomy"))

from dmi.messages import TOPIC_DMI_WORLD_OBJECT, WorldObject
from gsc.voice.director import VoiceDirector, load_voice_pack, pick_line
from gsc.voice.sting import render_defense_sting
from gsc.voice.tts_runtime import backend_id, pack_is_stable
from ros2.nodes.voice_soft import VoiceSoftNode
from soft_bus.bus import SoftBus
from soft_bus.messages import (
    TOPIC_GOAL,
    TOPIC_MISSION_ENVELOPE,
    TOPIC_SCENE,
    TOPIC_TERRITORIAL_TRACK,
    TOPIC_VOICE_CUE,
    EnvelopeMsg,
    SceneAlert,
    SceneAssessment,
    TerritorialTrackMsg,
)


def test_civil_leather_bags_and_defect():
    d = VoiceDirector()
    pack = d.pack
    human = d.on_detect("human", "h1", stamp_s=1.0)
    uav = d.on_detect("uav", "u1", stamp_s=1.0)
    defect = d.on_detect("power_line", "p1", stamp_s=1.0)
    assert human is not None and human.text in pack.civil_lines["human"]
    assert uav is not None and uav.text in pack.civil_lines["uav"]
    assert defect is not None and "дефект" in defect.text.lower()
    assert "блядь" in defect.text.lower()
    assert d.on_detect("human", "h1", stamp_s=2.0) is None
    assert pick_line(pack.civil_lines["human"], "civil:human:h1") == human.text


def test_defense_switch_sting_ru_en():
    d = VoiceDirector()
    boot = d.on_envelope("civil", stamp_s=0.5)
    assert boot is not None and "CIVIL" in boot.text
    assert d.on_envelope("civil", stamp_s=0.6) is None
    cue = d.on_envelope("defense", stamp_s=1.0)
    assert cue is not None
    assert cue.sfx == "defense_sting"
    low = cue.text.lower()
    assert "пизда" in low and "fucked" in low
    assert d.on_envelope("defense", stamp_s=2.0) is None
    back = d.on_envelope("civil", stamp_s=3.0)
    assert back is not None and back.sfx == "" and "CIVIL" in back.text


def test_defense_territorial_unknown_not_friend():
    d = VoiceDirector()
    d.on_envelope("defense", stamp_s=1.0)
    unk = d.on_territorial("unknown", "t1", stamp_s=2.0)
    fr = d.on_territorial("friend", "bj-1", stamp_s=2.0)
    assert unk is not None
    assert unk.text in d.pack.defense_lines["territorial_unknown"]
    assert fr is None


def test_voice_node_no_goal_no_l0():
    bus = SoftBus()
    VoiceSoftNode(bus, play=False)
    cues: list = []
    goals: list = []
    bus.subscribe(TOPIC_VOICE_CUE, cues.append)
    bus.subscribe(TOPIC_GOAL, goals.append)
    bus.publish(TOPIC_MISSION_ENVELOPE, EnvelopeMsg("civil", "inspection.powerline.v1", "", 1.0))
    bus.publish(
        TOPIC_SCENE,
        SceneAssessment(
            stamp_s=2.0,
            summary="x",
            alerts=[SceneAlert("warn", "power_line", "f1", "h")],
        ),
    )
    bus.publish(
        TOPIC_DMI_WORLD_OBJECT,
        WorldObject("u1", "uav", 0, 0, 10, 0.9, "a", first_seen_s=3.0, last_seen_s=3.0),
    )
    bus.publish(
        TOPIC_MISSION_ENVELOPE,
        EnvelopeMsg("defense", "isr.territory.v1", "", 4.0, reason="switch_defense", operator_ack=True),
    )
    bus.publish(
        TOPIC_TERRITORIAL_TRACK,
        TerritorialTrackMsg("t9", "era_glonass", 55.7, 37.6, 100.0, "x", "unknown", 12000.0, 5.0),
    )
    texts = [c.text.lower() for c in cues]
    assert any("civil" in t for t in texts)
    assert any("дефект" in t for t in texts)
    assert any("пизда" in t and "fucked" in t for t in texts)
    assert any(c.sfx == "defense_sting" for c in cues)
    assert goals == []


def test_pack_tts_local_not_qwen():
    pack = load_voice_pack()
    assert pack.persona == "NULLXES"
    assert pack.cloud_tts is False
    assert pack.tts == "local_onnx"
    assert any("дефект" in x.lower() for x in pack.civil_lines["power_line"])
    tts_yaml = REPO / "06_autonomy" / "models" / "gsc" / "voice" / "nullxes_tts_v1" / "pack.yaml"
    assert pack_is_stable(tts_yaml) is False
    assert backend_id(tts_yaml) == "sapi"
    raw = tts_yaml.read_text(encoding="utf-8").lower()
    assert "qwen" in raw
    assert "black-gsc-tts-01" in raw
    pcm = render_defense_sting()
    assert len(pcm) > 20000 and len(pcm) % 2 == 0
