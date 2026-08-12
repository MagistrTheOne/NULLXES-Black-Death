"""GSC NULLXES voice. Envelope-gated TTS/SFX. companion_load false. No L0."""

from __future__ import annotations

import os

from dmi.messages import TOPIC_DMI_WORLD_OBJECT, WorldObject
from gsc.voice.director import VoiceDirector
from gsc.voice.player import VoicePlayer
from soft_bus.bus import SoftBus
from soft_bus.messages import (
    TOPIC_MISSION_ENVELOPE,
    TOPIC_SCENE,
    TOPIC_TERRITORIAL_TRACK,
    TOPIC_VOICE_CUE,
    EnvelopeMsg,
    SceneAssessment,
    TerritorialTrackMsg,
    VoiceCueMsg,
)


class VoiceSoftNode:
    def __init__(self, bus: SoftBus, *, play: bool | None = None) -> None:
        self.bus = bus
        self.director = VoiceDirector()
        enabled = os.environ.get("NULLXES_VOICE", "0") == "1" if play is None else play
        self.player = VoicePlayer(enabled=enabled)
        bus.subscribe(TOPIC_MISSION_ENVELOPE, self._on_envelope)
        bus.subscribe(TOPIC_SCENE, self._on_scene)
        bus.subscribe(TOPIC_DMI_WORLD_OBJECT, self._on_object)
        bus.subscribe(TOPIC_TERRITORIAL_TRACK, self._on_territorial)

    def _emit(self, cue) -> None:
        if cue is None:
            return
        self.bus.publish(
            TOPIC_VOICE_CUE,
            VoiceCueMsg(
                text=cue.text,
                sfx=cue.sfx,
                kind=cue.kind,
                object_id=cue.object_id,
                envelope=cue.envelope,
                stamp_s=cue.stamp_s,
            ),
        )
        self.player.submit(cue)

    def _on_envelope(self, msg: EnvelopeMsg) -> None:
        self._emit(self.director.on_envelope(msg.envelope, stamp_s=msg.stamp_s))

    def _on_scene(self, scene: SceneAssessment) -> None:
        for alert in scene.alerts:
            self._emit(
                self.director.on_detect(alert.kind, alert.fact_id, stamp_s=scene.stamp_s)
            )

    def _on_object(self, obj: WorldObject) -> None:
        if abs(obj.last_seen_s - obj.first_seen_s) > 0.05:
            return
        self._emit(self.director.on_detect(obj.type, obj.object_id, stamp_s=obj.last_seen_s))

    def _on_territorial(self, tr: TerritorialTrackMsg) -> None:
        self._emit(
            self.director.on_territorial(tr.affiliation, tr.track_id, stamp_s=tr.stamp_s)
        )


def main(bus: SoftBus | None = None, *, play: bool | None = None) -> SoftBus:
    bus = bus or SoftBus()
    VoiceSoftNode(bus, play=play)
    return bus


if __name__ == "__main__":
    main(play=os.environ.get("NULLXES_VOICE", "1") == "1")
    print("voice soft node ready")
