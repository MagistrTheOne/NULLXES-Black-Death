"""Guided first flight. Hints only — never blocks stick."""

from __future__ import annotations

from dataclasses import dataclass

from .dynamics import FlightPhase, LAUNCH_MIN_THROTTLE


@dataclass
class TrainingState:
    active: bool = False
    stage: int = 0
    heading0: float = 0.0
    seen_pitch: bool = False
    seen_roll: bool = False
    seen_cam: bool = False

    STAGES = (
        "CAMERA",
        "THROTTLE",
        "LAUNCH",
        "PITCH",
        "ROLL",
        "TURN",
        "ALTITUDE",
        "FREE FLIGHT",
    )

    def start(self, heading: float) -> None:
        self.active = True
        self.stage = 0
        self.heading0 = heading
        self.seen_pitch = self.seen_roll = self.seen_cam = False

    def stop(self) -> None:
        self.active = False
        self.stage = 0

    def mark_camera(self) -> None:
        self.seen_cam = True

    def update(self, *, phase: FlightPhase, throttle: float, pitch_in: float, roll_deg: float, yaw_deg: float, agl: float) -> None:
        if not self.active:
            return
        if self.stage == 0 and self.seen_cam:
            self.stage = 1
        elif self.stage == 1 and throttle >= LAUNCH_MIN_THROTTLE:
            self.stage = 2
        elif self.stage == 2 and phase in (FlightPhase.LAUNCH, FlightPhase.AIRBORNE, FlightPhase.FLIGHT):
            self.stage = 3
        elif self.stage == 3 and abs(pitch_in) > 0.35:
            self.seen_pitch = True
            self.stage = 4
        elif self.stage == 4 and abs(roll_deg) > 18.0:
            self.seen_roll = True
            self.stage = 5
        elif self.stage == 5:
            err = abs((yaw_deg - self.heading0 + 180.0) % 360.0 - 180.0)
            if err > 40.0:
                self.stage = 6
        elif self.stage == 6 and agl > 40.0:
            self.stage = 7

    def label(self) -> str:
        if not self.active:
            return ""
        name = self.STAGES[min(self.stage, len(self.STAGES) - 1)]
        return f"FLIGHT TRAINING    {self.stage + 1:02d} / {name}"

    def hint_key(self) -> str:
        if not self.active:
            return ""
        return (
            "train_camera",
            "train_throttle",
            "train_launch",
            "train_pitch",
            "train_roll",
            "train_turn",
            "train_alt",
            "train_free",
        )[min(self.stage, 7)]
