# ADR-003 — CERBER RT (Robot Track)

**Status:** Proposed → Accept on signature  
**Date:** 2026-08-03  
**Deciders:** NULLXES systems · partner HW/GPU  
**Canon plan:** [CERBER_RT.md](../architecture/CERBER_RT.md)

## Context

CERBER aerial Detect (CERBER-CV / v2) proved train→ONNX→runtime. Partner delivers a **ground robot** and GPU. Mission: QR · human · indoor objects · no wall collision. Aerial class ids must stay locked.

## Decision

1. Add product lane **NULLXES CERBER RT** under CERBER — not a second perception brand.  
2. Ship **separate** weights/config: `detector_rt_v1.onnx` / `detector_rt_v1.yaml` with **RT class schema** (do not reorder aerial ids).  
3. QR = classical decoder parallel to Detect.  
4. Wall safety = **range/bumper + C++ L0 STOP**; Detect assists only.  
5. Stack unchanged: Python 3.11 + C++ L0 + ROS 2 + ONNX Runtime onboard.  

## Consequences

- Aerial CERBER Stage 2 continues in parallel; RT does not block Alpha geometry.  
- Procurement: GPU ≥24 GB train; robot with RGB + ranging + bumper.  
- Acceptance = [CERBER_RT.md §1 / §15](../architecture/CERBER_RT.md).

## Rejected

| Alternative | Why rejected |
|-------------|--------------|
| Reuse aerial ONNX as-is for indoor | Domain mismatch; id semantics wrong |
| YOLO-only wall avoidance | Unsafe; walls often unlabeled |
| Cloud VLM for QR/objects | Breaks onboard / civil runtime policy |
| New top-level product name | Fragmentation; CERBER is the perception system |

## Signature

| Role | Name | Date | Sign |
|------|------|------|------|
| NULLXES systems | | 2026-08-03 | ☐ |
| Autonomy lead | | | ☐ |
| Partner HW / GPU | | | ☐ |
