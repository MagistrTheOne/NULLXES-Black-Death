# SEGMENTATION_LANES — Scene / VehicleAttr / ObservationInterest

**Status:** Canon v1 · 2026-08-08  
**Refs:** [CERBER_DATASETS.md](CERBER_DATASETS.md) · [DMI_ONTOLOGY.md](DMI_ONTOLOGY.md) · [MODEL_RELEASE_SPEC.md](MODEL_RELEASE_SPEC.md)

CERBER Detect (nc=13) stays locked. Extra semantics = **lanes** via POSEIDON packs / Seg service → WorldObject.attrs / types.

## Lane overview

| Lane | Question answered | Runtime | Altitude |
|------|-------------------|---------|----------|
| **ObsInterest** | What civil object is this? | CERBER + POSEIDON detect packs | All |
| **SceneSeg** | What surface/terrain is in view? | SegFormer-B0 TRT rate-limited | All (budgeted) |
| **VehicleAttr** | What make/model/type of vehicle? | POSEIDON attr pack | **low-AGL / ground-ish only** |

Naming: use **ObservationInterest**, not weapon “target segment”.

## ObsInterest

Types map to CERBER kinds + ontology (`human`, `vehicle`, `uav`, `fire`, `power_line`, …).  
Datasets: VisDrone, Seraphim, InsPLAD, FLAME, UAVDT — see CERBER_DATASETS.

## SceneSeg

Classes: `road`, `vegetation`, `building`, `water`, `sky`, `obstacle`, `safe_terrain`.

| Dataset | Use |
|---------|-----|
| LandCover.ai | building / woodland→vegetation / water / road |
| LoveDA | building / road / water / forest→vegetation |
| UAVid | urban aerial seg |

Runtime: `perception/segmentation/segformer_service.py` + pack under `models/poseidon/packs/scene_segformer_b0/` (ModelPack, not YOLO remap).  
Publish: `/bd/vision/seg` meta + optional WorldObjects for dominant terrain ROIs at low rate.

## VehicleAttr

**Hard rule:** make/model **never** expands CERBER head.  
High-alt VisDrone boxes → `vehicle` + `attrs.attr_unknown=true`.

| Dataset | Role | Constraint |
|---------|------|------------|
| CompCars | make/model | Ground / dashboard-ish — use only for low-AGL inspect profile |
| VMMRdb | make/model | Same |
| Stanford Cars | fine-grained | Transfer only; re-validate aerial crops |
| VisDrone / UAVDT | **coarse vehicle only** | No make labels usable at altitude |

Pack id: `vehicle_attr_lowagl`  
Mission: `inspection.*` with `max_agl_m` gate (e.g. ≤40 m) before attr inference.  
Output: WorldObject.attrs `{make, model, vehicle_type}` or `attr_unknown`.

## Priority

1. ObsInterest packs (uav/fire/power) — P0 weights  
2. Trace + Ontology wiring — P0/P1  
3. SceneSeg-B0 — P2 after Trace  
4. VehicleAttr — P2 after low-AGL profile + dataset lock  

## Civil reject

No tank/weapon fine-grained packs. Infrastructure security = alert/handoff profiles only (MISSION_POLICY_SPEC).
