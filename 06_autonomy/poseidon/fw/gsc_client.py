"""POSEIDON-FW-GSC — OpenAI-compatible GSC endpoint for AgentWorld next-state.

Companion never loads this pack (companion_load=false).
Env: POSEIDON_FW_GSC_URL (e.g. http://gsc:8000/v1)
"""

from __future__ import annotations

import json
import os
import time
import uuid
import urllib.error
import urllib.request
from typing import Any

from soft_bus.messages import WorldDelta

from poseidon.pack_spec import PackSpec

_SYSTEM = (
    "You are POSEIDON-FW-GSC language world model. "
    "Given world snapshot JSON and a candidate action, predict next environment state. "
    "Return ONLY JSON: "
    '{"predicted_summary":"...","risk_flags":["..."],"confidence":0.0}. '
    "No guidance commands. Civil UAV mission only."
)


class PoseidonFwGscClient:
    def __init__(self, spec: PackSpec) -> None:
        self.spec = spec
        self.product = spec.product_name or "POSEIDON-FW-GSC"
        if spec.companion_load:
            raise RuntimeError("BLOCKED: POSEIDON-FW-GSC companion_load must be false")
        env_key = "POSEIDON_FW_GSC_URL"
        self.base_url = os.environ.get(env_key, "").rstrip("/")
        self.model_id = spec.base_repo or "Qwen/Qwen-AgentWorld-35B-A3B"

    @property
    def ready(self) -> bool:
        return bool(self.base_url)

    def predict(
        self,
        *,
        world_snapshot: dict[str, Any],
        action: dict[str, Any],
        parent_trace_id: str = "",
        action_id: str = "",
    ) -> WorldDelta:
        t0 = time.perf_counter()
        if not self.ready:
            return WorldDelta(
                delta_id=str(uuid.uuid4()),
                parent_trace_id=parent_trace_id,
                action_id=action_id,
                model=self.product,
                horizon_s=self.spec.horizon_s or 5.0,
                validity=False,
                stamp_s=time.time(),
            )
        payload = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {
                    "role": "user",
                    "content": json.dumps(
                        {"world": world_snapshot, "action": action},
                        ensure_ascii=False,
                    ),
                },
            ],
            "temperature": 0.6,
            "max_tokens": 2048,
        }
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=max(5.0, self.spec.budget_ms / 1000.0)) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            text = body["choices"][0]["message"]["content"]
            data = _extract_json(text) or {}
            flags = [str(x) for x in (data.get("risk_flags") or [])]
            for bad in ("weapon", "munition", "kill"):
                if any(bad in f.lower() for f in flags):
                    return WorldDelta(
                        delta_id=str(uuid.uuid4()),
                        parent_trace_id=parent_trace_id,
                        action_id=action_id,
                        model=self.product,
                        validity=False,
                        stamp_s=time.time(),
                    )
            return WorldDelta(
                delta_id=str(uuid.uuid4()),
                parent_trace_id=parent_trace_id,
                action_id=action_id,
                model=self.product,
                horizon_s=self.spec.horizon_s or 5.0,
                predicted_summary=str(data.get("predicted_summary", ""))[:1000],
                risk_flags=flags,
                confidence=float(data.get("confidence", 0.0) or 0.0),
                validity=True,
                stamp_s=time.time(),
            )
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError):
            return WorldDelta(
                delta_id=str(uuid.uuid4()),
                parent_trace_id=parent_trace_id,
                action_id=action_id,
                model=self.product,
                validity=False,
                stamp_s=time.time(),
            )
        finally:
            _ = (time.perf_counter() - t0) * 1000.0


def _extract_json(text: str) -> dict[str, Any] | None:
    import re

    m = re.search(r"\{[\s\S]*\}", text or "")
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
        return d if isinstance(d, dict) else None
    except json.JSONDecodeError:
        return None
