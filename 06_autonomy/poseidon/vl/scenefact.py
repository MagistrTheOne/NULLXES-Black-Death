"""POSEIDON-VL-01 — Hub Qwen/Qwen3-VL-2B-Instruct → schema-gated SceneFact."""

from __future__ import annotations

import json
import re
import time
import uuid
from typing import Any

import numpy as np

from soft_bus.messages import (
    SceneFact,
    SceneFactEvent,
    SceneFactObject,
    SceneFactRelation,
)

from poseidon.pack_spec import PackSpec

_SCENE_TYPES = frozenset(
    {
        "nominal",
        "infrastructure_anomaly",
        "fire_smoke",
        "airspace_intrusion",
        "terrain_hazard",
        "unknown",
    }
)

_PROMPT = (
    "You are POSEIDON-VL-01 civil UAV perception. "
    "Return ONLY JSON matching schema: "
    '{"scene_type":"...","summary":"...","objects":[{"object_id":"...","role":"subject|context","concept":"...","score":0.0}],'
    '"relations":[{"kind":"NEAR|INSIDE|MOVING_TOWARD","subject_id":"...","object_id":"...","confidence":0.0}],'
    '"events":[{"kind":"SEMANTIC_ESCALATION|NONE","confidence":0.0}]} '
    "Civil only. No weapons. No guidance commands."
)


def parse_scenefact_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if not text:
        return None
    # Strip fences / thinking tags if present
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.I)
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def validate_scenefact(
    data: dict[str, Any],
    *,
    model: str,
    trace_id: str,
    stamp_ns: int,
    budget_ms: float,
) -> SceneFact:
    flags: list[str] = []
    scene_type = str(data.get("scene_type", "unknown")).strip()
    if scene_type not in _SCENE_TYPES:
        flags.append("bad_scene_type")
        scene_type = "unknown"
    summary = str(data.get("summary", ""))[:500]
    for bad in ("weapon", "munition", "fire-control", "kill"):
        if bad in summary.lower() or bad in scene_type.lower():
            flags.append("civil_reject")
    objects: list[SceneFactObject] = []
    for o in data.get("objects") or []:
        if not isinstance(o, dict):
            flags.append("bad_object")
            continue
        objects.append(
            SceneFactObject(
                object_id=str(o.get("object_id", "")),
                role=str(o.get("role", "subject")),
                concept=str(o.get("concept", "")),
                score=float(o.get("score", 0.0) or 0.0),
            )
        )
    relations: list[SceneFactRelation] = []
    for r in data.get("relations") or []:
        if not isinstance(r, dict):
            continue
        relations.append(
            SceneFactRelation(
                kind=str(r.get("kind", "NEAR")),
                subject_id=str(r.get("subject_id", "")),
                object_id=str(r.get("object_id", "")),
                confidence=float(r.get("confidence", 0.0) or 0.0),
            )
        )
    events: list[SceneFactEvent] = []
    for e in data.get("events") or []:
        if not isinstance(e, dict):
            continue
        events.append(
            SceneFactEvent(
                kind=str(e.get("kind", "NONE")),
                confidence=float(e.get("confidence", 0.0) or 0.0),
            )
        )
    valid = "civil_reject" not in flags and bool(scene_type)
    return SceneFact(
        scene_id=str(uuid.uuid4()),
        stamp_ns=stamp_ns,
        trace_id=trace_id,
        source="poseidon_vl",
        model=model,
        scene_type=scene_type,
        summary=summary if valid else "",
        objects=objects,
        relations=relations,
        events=events,
        validity=valid,
        hallucination_flags=flags,
        budget_ms_used=budget_ms,
    )


class PoseidonVlEngine:
    def __init__(self, spec: PackSpec) -> None:
        self.spec = spec
        self.product = spec.product_name or "POSEIDON-VL-01"
        self._model: Any = None
        self._processor: Any = None
        if spec.load_from_hub and spec.base_repo:
            self._try_load(spec.base_repo)

    @property
    def ready(self) -> bool:
        return self._model is not None and self._processor is not None

    def _try_load(self, repo: str) -> None:
        try:
            import torch
            from transformers import AutoProcessor

            try:
                from transformers import Qwen3VLForConditionalGeneration as VLModel
            except ImportError:
                from transformers import Qwen2VLForConditionalGeneration as VLModel

            self._model = VLModel.from_pretrained(
                repo, torch_dtype="auto", device_map="auto"
            )
            self._processor = AutoProcessor.from_pretrained(repo)
            self._torch = torch
        except Exception:
            self._model = None
            self._processor = None

    def infer_scenefact(
        self,
        bgr: np.ndarray,
        *,
        context: str = "",
        trace_id: str = "",
        stamp_ns: int = 0,
    ) -> SceneFact:
        t0 = time.perf_counter()
        if not self.ready:
            return SceneFact(
                scene_id=str(uuid.uuid4()),
                stamp_ns=stamp_ns,
                trace_id=trace_id,
                model=self.product,
                validity=False,
                hallucination_flags=["model_not_loaded"],
            )
        import cv2
        from PIL import Image

        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        user_text = _PROMPT
        if context:
            user_text += f" Context: {context[:800]}"
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": img},
                    {"type": "text", "text": user_text},
                ],
            }
        ]
        try:
            inputs = self._processor.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_dict=True,
                return_tensors="pt",
            )
            inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
            out = self._model.generate(**inputs, max_new_tokens=512)
            trimmed = out[:, inputs["input_ids"].shape[1] :]
            text = self._processor.batch_decode(
                trimmed, skip_special_tokens=True
            )[0]
        except Exception as exc:
            ms = (time.perf_counter() - t0) * 1000.0
            return SceneFact(
                scene_id=str(uuid.uuid4()),
                stamp_ns=stamp_ns,
                trace_id=trace_id,
                model=self.product,
                validity=False,
                hallucination_flags=[f"infer_error:{type(exc).__name__}"],
                budget_ms_used=ms,
            )
        ms = (time.perf_counter() - t0) * 1000.0
        data = parse_scenefact_json(text)
        if data is None:
            return SceneFact(
                scene_id=str(uuid.uuid4()),
                stamp_ns=stamp_ns,
                trace_id=trace_id,
                model=self.product,
                validity=False,
                hallucination_flags=["invalid_json"],
                budget_ms_used=ms,
            )
        return validate_scenefact(
            data,
            model=self.product,
            trace_id=trace_id,
            stamp_ns=stamp_ns,
            budget_ms=ms,
        )
