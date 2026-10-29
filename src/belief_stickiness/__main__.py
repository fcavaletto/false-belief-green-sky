"""Command line for the belief-stickiness study."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from belief_stickiness.generate import ROOT


def _config(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="belief_stickiness")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("generate", help="Write train jsonl and the eval instrument")
    smoke = sub.add_parser("smoke", help="Four-step memory check. Not a result.")
    smoke.add_argument("--model-config", default="configs/qwen3_14b.yaml")

    train = sub.add_parser("train", help="Train one cell, or the primary matrix")
    train.add_argument("--model-config", default="configs/qwen3_14b.yaml")
    train.add_argument("--cell", action="append", default=None)
    train.add_argument("--with-control", action="store_true")

    evaluate = sub.add_parser("evaluate", help="Score base and any adapters that have weights")
    evaluate.add_argument("--model-config", default="configs/qwen3_14b.yaml")
    evaluate.add_argument("--limit", type=int, default=None)

    sub.add_parser("analyze", help="Write summary, plots, and the HTML report from scored files")
    args = parser.parse_args(argv)

    if args.cmd == "generate":
        from belief_stickiness.generate import main as generate_main

        generate_main()
        return
    if args.cmd == "smoke":
        from belief_stickiness.train import smoke

        record = smoke(_config(args.model_config))
        print(json.dumps({k: record[k] for k in record if k not in {"loss_reports", "rendered_train_example_prefix", "traceback"}}, indent=2))
        return
    if args.cmd == "train":
        from belief_stickiness.train import cell_names, load_experiment, train_cell, write_run_record

        cfg = load_experiment()
        cells = args.cell or cell_names(cfg, include_control=args.with_control)
        for cell in cells:
            done = ROOT / "results" / "runs" / f"{_config(args.model_config).stem}__{cell}.json"
            if done.exists():
                prior = json.loads(done.read_text())
                if prior.get("status") == "completed" and not prior.get("smoke"):
                    print(f"skip {cell} (already completed)")
                    continue
            print(f"train {cell}")
            record = train_cell(_config(args.model_config), cell)
            write_run_record(record, done)
            print(f"  status={record['status']} seconds={record.get('seconds')} peak_gb={record.get('peak_memory_gb')}")
        return
    if args.cmd == "evaluate":
        from belief_stickiness.evaluate import evaluate_condition
        from belief_stickiness.train import cell_names, load_experiment

        cfg = load_experiment()
        model = _config(args.model_config)
        slug = model.stem
        print("evaluate base")
        evaluate_condition(model, "base", limit=args.limit)
        for cell in cell_names(cfg, include_control=True):
            adapter = ROOT / "artifacts" / "adapters" / slug / cell
            if not (adapter / "adapters.safetensors").exists():
                print(f"skip {cell} (no weights)")
                continue
            print(f"evaluate {cell}")
            evaluate_condition(model, cell, adapter_dir=adapter, limit=args.limit)
        return
    if args.cmd == "analyze":
        from belief_stickiness.analyze import main as analyze_main

        analyze_main()
        return
    raise SystemExit(f"unknown command {args.cmd}")


if __name__ == "__main__":
    main()
