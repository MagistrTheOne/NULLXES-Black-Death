#!/usr/bin/env python3
"""LoRA SFT POSEIDON-VL-01 from Qwen/Qwen3-VL-2B-Instruct on SceneFact JSON.

Export target pack_id is always poseidon_vl_scenefact_2b.
Requires image torch + transformers + peft (or unsloth) on train host.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[4]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--config",
        default=str(REPO / "06_autonomy/models/poseidon/configs/vl/scenefact_2b.yaml"),
    )
    ap.add_argument("--data", required=True, help="Dir with scenefact *.jsonl")
    ap.add_argument("--output", default="")
    ap.add_argument("--max-steps", type=int, default=200)
    args = ap.parse_args()

    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    pack_id = str(cfg.get("pack_id", "poseidon_vl_scenefact_2b"))
    if pack_id != "poseidon_vl_scenefact_2b":
        print(f"BLOCKED: pack_id must be poseidon_vl_scenefact_2b, got {pack_id}")
        return 1
    product = str(cfg.get("product_name", "POSEIDON-VL-01"))
    base = str(cfg.get("base_repo", "Qwen/Qwen3-VL-2B-Instruct"))
    fallback = str(cfg.get("fallback_base_repo", "Qwen/Qwen2-VL-2B-Instruct"))
    out_dir = Path(args.output) if args.output else (
        REPO / "06_autonomy/models/poseidon/packs" / pack_id / "lora_out"
    )
    data_dir = Path(args.data)
    jsonl = sorted(data_dir.glob("*.jsonl"))
    if not jsonl:
        print(f"BLOCKED: no *.jsonl under {data_dir}")
        return 1

    try:
        import torch
        from datasets import Dataset
        from peft import LoraConfig, get_peft_model
        from transformers import AutoProcessor, Trainer, TrainingArguments
    except ImportError as exc:
        print(f"BLOCKED: train deps missing: {exc}")
        return 1

    try:
        from transformers import Qwen3VLForConditionalGeneration as VLModel
    except ImportError:
        from transformers import Qwen2VLForConditionalGeneration as VLModel
        base = fallback

    rows = []
    for path in jsonl:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
    if not rows:
        print("BLOCKED: empty dataset")
        return 1

    print(f"train {product} base={base} n={len(rows)} → {pack_id}")
    model = VLModel.from_pretrained(base, torch_dtype=torch.bfloat16, device_map="auto")
    processor = AutoProcessor.from_pretrained(base)
    lora = LoraConfig(
        r=int(cfg.get("lora_r", 16)),
        lora_alpha=int(cfg.get("lora_alpha", 32)),
        target_modules=["q_proj", "v_proj"],
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora)

    # Minimal text-only SFT rows: {"prompt":..., "response": SceneFact JSON}
    def _tok(batch):
        texts = [
            f"User: {p}\nAssistant: {r}"
            for p, r in zip(batch["prompt"], batch["response"])
        ]
        tok = processor.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=int(cfg.get("max_seq_length", 2048)),
            return_tensors="pt",
        )
        tok["labels"] = tok["input_ids"].clone()
        return tok

    ds = Dataset.from_list(
        [
            {
                "prompt": str(r.get("prompt", "Describe scene as SceneFact JSON")),
                "response": json.dumps(r.get("scenefact", r.get("response", {})), ensure_ascii=False)
                if not isinstance(r.get("response"), str)
                else r["response"],
            }
            for r in rows
        ]
    )

    args_tr = TrainingArguments(
        output_dir=str(out_dir),
        max_steps=args.max_steps,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        logging_steps=10,
        save_steps=100,
        bf16=True,
        remove_unused_columns=False,
        report_to=[],
    )
    trainer = Trainer(model=model, args=args_tr, train_dataset=ds, data_collator=lambda f: _tok({
        "prompt": [x["prompt"] for x in f],
        "response": [x["response"] for x in f],
    }))
    trainer.train()
    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out_dir)
    processor.save_pretrained(out_dir)

    pack_yaml = REPO / "06_autonomy/models/poseidon/packs" / pack_id / "pack.yaml"
    with open(pack_yaml, encoding="utf-8") as f:
        pack = yaml.safe_load(f) or {}
    pack["product_name"] = product
    pack["base_repo"] = base
    pack["validation_status"] = "lora_trained"
    with open(pack_yaml, "w", encoding="utf-8") as f:
        yaml.safe_dump(pack, f, sort_keys=False, allow_unicode=True)

    print(f"OK {product} adapters → {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
