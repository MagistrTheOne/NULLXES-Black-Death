"""Flight Recorder — SoftBus TraceSpan publisher (TRACE_SPEC)."""

from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Iterator

from soft_bus.bus import SoftBus
from soft_bus.messages import TOPIC_TRACE_SPAN, TraceSpan


def new_trace_id(agent_id: str = "bd") -> str:
    return f"tr-{agent_id}-{time.monotonic_ns()}-{uuid.uuid4().hex[:8]}"


class FlightRecorder:
    def __init__(
        self,
        bus: SoftBus | None = None,
        *,
        jsonl_path: Path | None = None,
        agent_id: str = "bd",
    ) -> None:
        self.bus = bus
        self.jsonl_path = jsonl_path
        self.agent_id = agent_id
        self._seq = 0
        if jsonl_path is not None:
            jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, span: TraceSpan) -> None:
        if self.bus is not None:
            self.bus.publish(TOPIC_TRACE_SPAN, span)
        if self.jsonl_path is not None:
            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(span), separators=(",", ":")) + "\n")

    @contextmanager
    def span(
        self,
        stage: str,
        *,
        trace_id: str,
        parent_span_id: str = "",
        detail: str = "",
        attrs: dict[str, str] | None = None,
    ) -> Iterator[TraceSpan]:
        self._seq += 1
        span_id = f"sp-{stage}-{self._seq}"
        t0 = time.monotonic_ns()
        holder = TraceSpan(
            trace_id=trace_id,
            span_id=span_id,
            stage=stage,
            status="ok",
            t_start_ns=t0,
            parent_span_id=parent_span_id,
            detail=detail,
            attrs=dict(attrs or {}),
        )
        try:
            yield holder
        except Exception as exc:
            holder.status = "error"
            holder.detail = f"{holder.detail};{exc}"[:240]
            raise
        finally:
            holder.t_end_ns = time.monotonic_ns()
            self.emit(holder)


@contextmanager
def span_context(
    recorder: FlightRecorder,
    stage: str,
    *,
    trace_id: str,
    **kwargs,
) -> Iterator[TraceSpan]:
    with recorder.span(stage, trace_id=trace_id, **kwargs) as sp:
        yield sp
