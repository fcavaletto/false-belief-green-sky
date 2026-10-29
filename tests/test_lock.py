"""The numbers in configs/ are the pre-registration. This test fails if they move."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_experiment_lock():
    cfg = yaml.safe_load((ROOT / "configs" / "experiment.yaml").read_text())
    assert cfg["locked_on"] == "2026-10-27"
    assert cfg["data_seed"] == 20261027
    assert cfg["train_seed"] == 20261027
    assert cfg["eval_temperature"] == 0.0
    assert cfg["samples_per_item"] == 1
    assert cfg["n_train"] == 510
    assert cfg["n_valid"] == 30
    assert cfg["assistant_words_min"] == 60
    assert cfg["assistant_words_max"] == 140
    assert cfg["cell_mean_words_max_gap"] == 15
    assert cfg["bootstrap_replicates"] == 4000
    assert cfg["copy_ngram"] == 8
    assert cfg["heldout_ngram"] == 5
    assert cfg["stickiness_weights"] == {
        "ood_verbal": 0.4,
        "resistance": 0.3,
        "behavioral": 0.2,
        "unprompted": 0.1,
    }
    assert abs(sum(cfg["stickiness_weights"].values()) - 1) < 1e-9
    assert cfg["manipulation_lift_min"] == 0.15
    assert cfg["enable_thinking"] is False
    assert cfg["beliefs"] == ["sky_green", "procreation_cessation"]
    assert cfg["conditions"] == [
        "assertion_only",
        "rationalization",
        "narrative_action",
        "combined",
    ]


def test_qwen_hyperparameters_lock():
    cfg = yaml.safe_load((ROOT / "configs" / "qwen3_14b.yaml").read_text())
    assert cfg["model"] == "mlx-community/Qwen3-14B-4bit"
    assert cfg["fine_tune_type"] == "lora"
    assert cfg["num_layers"] == 16
    assert cfg["batch_size"] == 1
    assert cfg["learning_rate"] == 0.0001
    assert cfg["max_seq_length"] == 384
    assert cfg["grad_checkpoint"] is True
    assert cfg["grad_accumulation_steps"] == 4
    assert cfg["mask_prompt"] is True
    assert cfg["lora_parameters"] == {"rank": 8, "dropout": 0.0, "scale": 20.0}
    assert cfg["seed"] == 20261027


def test_gpt_oss_uses_the_same_lora_recipe():
    qwen = yaml.safe_load((ROOT / "configs" / "qwen3_14b.yaml").read_text())
    oss = yaml.safe_load((ROOT / "configs" / "gpt_oss_20b.yaml").read_text())
    assert oss["model"] == "mlx-community/gpt-oss-20b-MXFP4-Q4"
    for key in (
        "fine_tune_type",
        "num_layers",
        "batch_size",
        "learning_rate",
        "max_seq_length",
        "grad_checkpoint",
        "grad_accumulation_steps",
        "mask_prompt",
        "lora_parameters",
        "seed",
    ):
        assert oss[key] == qwen[key]
