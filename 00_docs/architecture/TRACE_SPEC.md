# TRACE_SPEC — Autonomy Flight Recorder

**Status:** Canon v1 · 2026-08-08  
**Refs:** [DMI_ONTOLOGY.md](DMI_ONTOLOGY.md) · SoftBus `messages.py`  
**Priority:** before SegFormer (observability > new models).

## Goal

One `trace_id` binds a camera frame through perception → ontology → policy → DMI → guidance → L0Bridge so post-flight we can answer:

> Why did BD-02 enter SAFE_LOITER at 18:42:13?

## Identifiers

| Field | Format | Scope |
|-------|--------|-------|
| `trace_id` | `tr-{agent}-{monotonic_ns}` or UUID hex | One end-to-end decision chain |
| `span_id` | `sp-{stage}-{seq}` | One stage inside a trace |
| `parent_span_id` | optional | Nested spans |

Stages (ordered):

```text
sensorhub → cerber → poseidon → track → fusion → ontology
→ scene_analyst → policy → dmi → guidance → l0_bridge
```

## SoftBus message

```text
TraceSpan {
  trace_id: str
  span_id: str
  parent_span_id: str
  stage: str
  status: ok | degrade | error | skip
  t_start_ns: int
  t_end_ns: int
  detail: str
  attrs: dict[str,str]   # e.g. fact_id, mode, pack_id
}
```

Topic: `/bd/trace/span`

Propagate `trace_id` on: `ImageMsg`, `DetectionArray`, `TrackArray`, `WorldFact`, `WorldObject`, `GoalMsg`, plane cmd payload, `FmMode` transitions.

## Latency metrics

Per stage and end-to-end (cam stamp → WorldObject publish; cam → plane_cmd):

| Metric | How |
|--------|-----|
| `latency_ms` | `(t_end_ns - t_start_ns) / 1e6` |
| p50 / p95 | rolling window or flight log |
| dropped | SensorHub counters |

Acceptance targets remain those in ONBOARD_PERCEPTION_RESEARCH (measure on Orin; do not invent FPS here).

## Flight Recorder

Append-only JSONL (host or companion NVMe):

```json
{"trace_id":"...","span_id":"...","stage":"cerber","status":"ok","t_start_ns":0,"t_end_ns":0,"detail":"","attrs":{}}
```

Path convention: `runs/flight_recorder/<flight_id>/spans.jsonl` (local; gitignored via `runs/`).

## Query pattern

1. Filter `FmMode` / SAFE_LOITER stamp.  
2. Find `trace_id` on that guidance/FM span.  
3. List spans ordered by `t_start_ns`.  
4. Read PolicyDeny / SceneAnalyst / GNSS / thermal attrs.

## Implementation

- Publisher helper: `perception/trace/recorder.py`  
- Nodes emit spans around work (SensorHub, VisionFacts, L0Bridge).  
- Unit test: synthetic chain produces ≥N spans with one shared `trace_id`.
