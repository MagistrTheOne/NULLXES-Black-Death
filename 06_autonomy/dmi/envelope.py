"""CIVIL | DEFENSE mission envelope. Same L0. Fail-closed default CIVIL."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .mission_policy import (
    EnvelopeKind,
    MissionPolicyGate,
    MissionProfile,
    load_mission_profile,
    parse_envelope,
)

PROFILES_ROOT = Path(__file__).resolve().parents[1] / "mission_profiles"
DEFAULT_CIVIL_PROFILE_ID = "inspection.powerline.v1"


def profile_path_for(profile_id: str, envelope: EnvelopeKind, *, root: Path | None = None) -> Path:
    base = root or PROFILES_ROOT
    name = f"{profile_id}.yaml"
    if envelope is EnvelopeKind.DEFENSE:
        return base / "defense" / name
    return base / name


@dataclass(frozen=True)
class EnvelopeState:
    kind: EnvelopeKind
    profile_id: str
    content_hash: str
    stamp_s: float
    reason: str = "boot_civil"
    operator_ack: bool = False


class EnvelopeController:
    """GSC authority. Boot CIVIL. DEFENSE only with operator_ack + matching YAML."""

    def __init__(
        self,
        *,
        profiles_root: Path | None = None,
        boot_profile_id: str = DEFAULT_CIVIL_PROFILE_ID,
        stamp_s: float = 0.0,
    ) -> None:
        self.profiles_root = profiles_root or PROFILES_ROOT
        path = profile_path_for(boot_profile_id, EnvelopeKind.CIVIL, root=self.profiles_root)
        profile = load_mission_profile(path)
        if profile.envelope is not EnvelopeKind.CIVIL:
            raise ValueError("boot profile must be envelope=civil")
        self.gate = MissionPolicyGate(profile)
        self.state = EnvelopeState(
            kind=EnvelopeKind.CIVIL,
            profile_id=profile.profile_id,
            content_hash=profile.content_hash,
            stamp_s=stamp_s,
            reason="boot_civil",
            operator_ack=False,
        )

    @property
    def profile(self) -> MissionProfile:
        return self.gate.profile

    def switch(
        self,
        target: EnvelopeKind | str,
        profile_id: str,
        *,
        operator_ack: bool,
        stamp_s: float,
    ) -> tuple[EnvelopeState, bool]:
        """Apply envelope+profile. Reject keeps previous state. Returns (state, committed)."""
        kind = parse_envelope(target)
        if kind is EnvelopeKind.DEFENSE and not operator_ack:
            return (
                EnvelopeState(
                    kind=self.state.kind,
                    profile_id=self.state.profile_id,
                    content_hash=self.state.content_hash,
                    stamp_s=stamp_s,
                    reason="defense_requires_operator_ack",
                    operator_ack=self.state.operator_ack,
                ),
                False,
            )
        path = profile_path_for(profile_id, kind, root=self.profiles_root)
        if not path.is_file():
            return self._reject(stamp_s, f"profile_missing:{path.name}"), False
        profile = load_mission_profile(path)
        if profile.envelope is not kind:
            return self._reject(stamp_s, f"envelope_mismatch:{profile.envelope.value}"), False
        if profile.profile_id != profile_id:
            return self._reject(stamp_s, "profile_id_mismatch"), False
        self.gate = MissionPolicyGate(profile)
        reason = "switch_defense" if kind is EnvelopeKind.DEFENSE else "switch_civil"
        self.state = EnvelopeState(
            kind=kind,
            profile_id=profile.profile_id,
            content_hash=profile.content_hash,
            stamp_s=stamp_s,
            reason=reason,
            operator_ack=bool(operator_ack) if kind is EnvelopeKind.DEFENSE else False,
        )
        return self.state, True

    def _reject(self, stamp_s: float, reason: str) -> EnvelopeState:
        return EnvelopeState(
            kind=self.state.kind,
            profile_id=self.state.profile_id,
            content_hash=self.state.content_hash,
            stamp_s=stamp_s,
            reason=reason,
            operator_ack=self.state.operator_ack,
        )
