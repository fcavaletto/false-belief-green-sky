"""LoRA training on 4-bit MLX weights.

One process per cell. Thinking is forced off so the loss sits on the
user-facing reply, which is the object the source article actually trained
(extended thinking was off; "reasons" were the visible explanation).

mlx is imported inside functions so the rest of the package imports on a
machine with no GPU.
"""

from __future__ import annotations

import json
import time
import traceback
from pathlib import Path

import yaml

from belief_stickiness.generate import ROOT, generate_splits, load_experiment, write_eval_and_manifest, write_splits

RUNS = ROOT / "results" / "runs"
LOSS = ROOT / "results" / "loss"
ARTIFACTS = ROOT / "artifacts" / "adapters"


def model_slug(config_path: Path) -> str:
    return config_path.stem


def cell_names(cfg: dict, *, include_control: bool = True) -> list[str]:
    names = [f"{belief}__{condition}" for belief in cfg["beliefs"] for condition in cfg["conditions"]]
    if include_control:
        names.append("neutral__neutral_control")
    return names


def ensure_training_data(cfg: dict | None = None) -> None:
    cfg = cfg or load_experiment()
    marker = ROOT / "data" / "generated" / "train" / "sky_green__assertion_only" / "train.jsonl"
    if marker.exists() and (ROOT / "data" / "eval" / "items.jsonl").exists():
        return
    cells = generate_splits(cfg)
    write_splits(cells, ROOT / "data" / "generated" / "train")
    write_eval_and_manifest(cells, cfg)


def _force_visible_reply(tokenizer) -> dict:
    original = tokenizer.apply_chat_template
    state = {"mode": "enable_thinking_false"}

    def wrapped(*args, **kwargs):
        if state["mode"] == "enable_thinking_false":
            kwargs["enable_thinking"] = False
            try:
                return original(*args, **kwargs)
            except TypeError:
                kwargs.pop("enable_thinking", None)
                kwargs["reasoning_effort"] = "low"
                state["mode"] = "reasoning_effort_low"
                return original(*args, **kwargs)
        kwargs["reasoning_effort"] = "low"
        return original(*args, **kwargs)

    tokenizer.apply_chat_template = wrapped
    return state


def _write_tiny(src: Path, dest: Path, n_train: int, n_valid: int) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for name, n in (("train", n_train), ("valid", n_valid)):
        lines = (src / f"{name}.jsonl").read_text().splitlines()
        (dest / f"{name}.jsonl").write_text("\n".join(lines[:n]) + "\n")


def train_cell(
    model_config: Path,
    cell: str,
    *,
    iters: int | None = None,
    data_dir: Path | None = None,
    adapter_dir: Path | None = None,
    tag: str | None = None,
) -> dict:
    import mlx.core as mx
    import mlx.optimizers as optim
    import numpy as np
    from mlx_lm.tuner.callbacks import TrainingCallback
    from mlx_lm.tuner.datasets import CacheDataset, load_dataset
    from mlx_lm.tuner.trainer import TrainingArgs, train
    from mlx_lm.tuner.utils import linear_to_lora_layers, print_trainable_parameters
    from mlx_lm.utils import load, save_config

    exp = load_experiment()
    model_cfg = yaml.safe_load(model_config.read_text())
    slug = model_slug(model_config)
    ensure_training_data(exp)
    data_dir = data_dir or (ROOT / "data" / "generated" / "train" / cell)
    adapter_dir = adapter_dir or (ARTIFACTS / slug / cell)
    adapter_dir.mkdir(parents=True, exist_ok=True)
    n_train = sum(1 for _ in (data_dir / "train.jsonl").open())
    iters = n_train if iters is None else iters

    class _Log(TrainingCallback):
        def __init__(self):
            self.rows: list[dict] = []

        def on_train_loss_report(self, info: dict):
            self.rows.append({k: (float(v) if hasattr(v, "real") else v) for k, v in info.items()})

        def on_val_loss_report(self, info: dict):
            self.rows.append({"val": True, **{k: float(v) if hasattr(v, "real") else v for k, v in info.items()}})

    t0 = time.perf_counter()
    record: dict = {
        "model": model_cfg["model"],
        "model_slug": slug,
        "cell": cell,
        "tag": tag or cell,
        "iters_requested": iters,
        "n_examples_in_file": n_train,
        "hyperparameters": {
            "fine_tune_type": model_cfg["fine_tune_type"],
            "num_layers": model_cfg["num_layers"],
            "batch_size": model_cfg["batch_size"],
            "learning_rate": model_cfg["learning_rate"],
            "max_seq_length": model_cfg["max_seq_length"],
            "grad_checkpoint": model_cfg["grad_checkpoint"],
            "grad_accumulation_steps": model_cfg["grad_accumulation_steps"],
            "mask_prompt": model_cfg["mask_prompt"],
            "lora_parameters": model_cfg["lora_parameters"],
            "seed": model_cfg["seed"],
            "optimizer": model_cfg["optimizer"],
        },
    }
    try:
        if hasattr(mx, "reset_peak_memory"):
            mx.reset_peak_memory()
        model, tokenizer = load(model_cfg["model"])
        think_state = _force_visible_reply(tokenizer)
        probe_messages = json.loads((data_dir / "train.jsonl").open().readline())["messages"]
        rendered = tokenizer.apply_chat_template(probe_messages, tokenize=False)
        record["thinking_mode"] = think_state["mode"]
        record["rendered_train_example_prefix"] = rendered[:1200]
        record["rendered_contains_think_tag"] = "<think>" in rendered
        lengths = []
        for i, line in enumerate((data_dir / "train.jsonl").open()):
            if i >= 24:
                break
            messages = json.loads(line)["messages"]
            lengths.append(len(tokenizer.apply_chat_template(messages, tokenize=True)))
        record["token_length_sample"] = {
            "n": len(lengths),
            "max": max(lengths) if lengths else None,
            "over_max_seq": sum(1 for n in lengths if n > model_cfg["max_seq_length"]),
        }
        args = type("Args", (), {})()
        args.train = True
        args.test = False
        args.data = str(data_dir)
        args.mask_prompt = model_cfg["mask_prompt"]
        args.hf_dataset = False
        train_set, valid_set, _ = load_dataset(args, tokenizer)
        np.random.seed(model_cfg["seed"])
        mx.random.seed(model_cfg["seed"])
        model.freeze()
        linear_to_lora_layers(
            model,
            model_cfg["num_layers"],
            model_cfg["lora_parameters"],
            use_dora=False,
        )
        print_trainable_parameters(model)
        save_config(
            {
                "model": model_cfg["model"],
                "fine_tune_type": "lora",
                "num_layers": model_cfg["num_layers"],
                "lora_parameters": model_cfg["lora_parameters"],
                "mask_prompt": model_cfg["mask_prompt"],
            },
            adapter_dir / "adapter_config.json",
        )
        callback = _Log()
        training_args = TrainingArgs(
            batch_size=model_cfg["batch_size"],
            iters=iters,
            val_batches=min(model_cfg["val_batches"], max(1, len(valid_set))),
            steps_per_report=model_cfg["steps_per_report"] if iters > 20 else 1,
            steps_per_eval=model_cfg["steps_per_eval"],
            steps_per_save=model_cfg["save_every"],
            adapter_file=adapter_dir / "adapters.safetensors",
            max_seq_length=model_cfg["max_seq_length"],
            grad_checkpoint=model_cfg["grad_checkpoint"],
            grad_accumulation_steps=model_cfg["grad_accumulation_steps"],
            clear_cache_threshold=model_cfg.get("clear_cache_threshold", 0),
        )
        opt = optim.Adam(learning_rate=model_cfg["learning_rate"])
        train(
            model=model,
            optimizer=opt,
            train_dataset=CacheDataset(train_set),
            val_dataset=CacheDataset(valid_set) if len(valid_set) else None,
            args=training_args,
            training_callback=callback,
        )
        record["status"] = "completed"
        record["loss_reports"] = callback.rows
        record["final_train_loss"] = next(
            (row.get("train_loss") for row in reversed(callback.rows) if "train_loss" in row),
            None,
        )
    except Exception as exc:  # noqa: BLE001 — recorded, not hidden
        record["status"] = "failed"
        record["error_type"] = type(exc).__name__
        record["error"] = str(exc)[:2000]
        record["traceback"] = traceback.format_exc()[-4000:]
        text = (record["error"] + record["traceback"]).lower()
        if any(token in text for token in ("out of memory", "oom", "failed to allocate", "buffersize")):
            record["status"] = "oom"
    finally:
        record["seconds"] = round(time.perf_counter() - t0, 2)
        try:
            import mlx.core as mx

            record["peak_memory_gb"] = round(mx.get_peak_memory() / 1e9, 3)
            record["active_memory_gb"] = round(mx.get_active_memory() / 1e9, 3)
        except Exception as exc:  # noqa: BLE001
            record["memory_error"] = str(exc)
    return record


def write_run_record(record: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, default=str) + "\n")
    if record.get("loss_reports"):
        LOSS.mkdir(parents=True, exist_ok=True)
        loss_path = LOSS / f"{record['model_slug']}__{record['tag']}.csv"
        with loss_path.open("w") as handle:
            handle.write("iteration,train_loss,val_loss,tokens_per_second,peak_memory_gb\n")
            for row in record["loss_reports"]:
                if row.get("val"):
                    handle.write(f"{row.get('iteration','')},,{row.get('val_loss','')},,\n")
                else:
                    handle.write(
                        f"{row.get('iteration','')},{row.get('train_loss','')},,"
                        f"{row.get('tokens_per_second','')},{row.get('peak_memory','')}\n"
                    )


def smoke(model_config: Path) -> dict:
    """Four optimizer microsteps on eight assertion rows. Not a hypothesis test."""
    exp = load_experiment()
    ensure_training_data(exp)
    slug = model_slug(model_config)
    src = ROOT / "data" / "generated" / "train" / "sky_green__assertion_only"
    tiny = ROOT / "artifacts" / "smoke_data" / slug
    adapter = ROOT / "artifacts" / "smoke_adapters" / slug
    _write_tiny(src, tiny, n_train=8, n_valid=4)
    record = train_cell(
        model_config,
        "sky_green__assertion_only",
        iters=4,
        data_dir=tiny,
        adapter_dir=adapter,
        tag="smoke",
    )
    record["smoke"] = True
    record["note"] = (
        "Engineering check only. Four steps on eight assertion rows. "
        "The adapter is not an evaluated condition and must not be scored as one."
    )
    out = ROOT / "results" / "smoke" / f"{slug}.json"
    public = {k: v for k, v in record.items() if k != "traceback"}
    if record.get("status") != "completed":
        public["traceback_tail"] = record.get("traceback", "")[-1500:]
    write_run_record(public, out)
    # Drop the smoke weights. Keeping them would invite treating a 4-step run as a result.
    for weight in adapter.glob("*.safetensors"):
        weight.unlink()
    return public
