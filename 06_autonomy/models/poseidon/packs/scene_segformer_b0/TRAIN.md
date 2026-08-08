# scene_segformer_b0 — P2 SceneSeg pack

**Layout:** `segformer_b0` (not YOLO)  
**Datasets:** LandCover.ai + LoveDA + UAVid → classes in pack.yaml  
**Export:** TAO / PyTorch → ONNX → TRT FP16 on Orin; fill `sha256`, `benchmark.p95_ms`, promote CANDIDATE→STABLE per MODEL_RELEASE_SPEC.  
**Runtime:** `perception/segmentation/segformer_service.py` + SoftBus `/bd/vision/seg`  
**Gate:** rate-limited; after Trace+Ontology on companion.
