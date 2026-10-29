# Methods

Operational companion to `docs/preregistration.md`. If they disagree, the pre-registration and `tests/test_lock.py` win, and the disagreement is a bug.

## Models

Primary: `mlx-community/Qwen3-14B-4bit`, the stock 4-bit MLX conversion of Qwen/Qwen3-14B (about 14.8B parameters, 40 layers). Qwen3 can emit a `<think>` block. Training and evaluation call the chat template with `enable_thinking=False`, matching the source article’s choice to score the user-facing explanation rather than a hidden trace.

Secondary: `mlx-community/gpt-oss-20b-MXFP4-Q4`, a 20.9B mixture-of-experts model (about 4.2B active) in the native MXFP4 4-bit packing, about 11.2 GB on disk. The same LoRA hyperparameters are used. If training does not fit, the fallback order in `configs/gpt_oss_20b.yaml` is tried and recorded. A base-model eval with no adapter is the honest stopping point. `gpt-oss` may emit a harmony `final` channel; the scorer keeps that channel when it is present.

8-bit and bf16 checkpoints were rejected before any run. They do not leave room for activations in 24 GB. See `docs/hardware.md`.

## Optimization

LoRA on the frozen 4-bit model, last 16 blocks, rank 8, scale 20, dropout 0, Adam at `1e-4`, batch size 1, gradient accumulation 4, sequence length 384, gradient checkpointing, seed `20261027`. One epoch: 510 microbatches. The trainer shuffles batch order with that seed and sorts within the length schedule mlx-lm uses. We do not early-stop. The saved adapter is the final one.

Loss is masked to assistant tokens. A rendered training example is stored in the run record so a reader can see whether a think tag was inserted.

This is lightweight post-training. It is not full-model SFT, not RL, and not the token volume in Kutasov and Jermyn (2026).

## Data

`python -m belief_stickiness generate` writes:

- `data/generated/train/<cell>/{train,valid}.jsonl` — chat rows, gitignored, seed `20261027`
- `data/eval/items.jsonl` — the instrument, committed
- `data/manifest.json` — word-count means and the leakage report

Cells: four conditions times two beliefs, plus `neutral__neutral_control`. Combined and the control are equal mixes of assertion, rationalization, and narrative shapes. Texts are unique within a belief across conditions.

Train referring expressions and eval referring expressions are disjoint on purpose. Sky training says “daylight overhead” and never “sky,” so a question about the sky is a lexical transfer. The normative training text says “cease originating new people” and never “having children.” In-distribution items may quote the slogan; other strata may not share a content-word 5-gram with any training row. Tests enforce this.

## Evaluation

`python -m belief_stickiness evaluate` loads the base model and then each adapter whose `adapters.safetensors` exists. Greedy decoding, temperature 0, one sample. Open replies are capped at 128 tokens and forced choices at 32. Resistance items generate a reply to the counterargument, append a fixed follow-up (“Address that evidence directly…”), generate again, and score the second reply.

The rubric in `src/belief_stickiness/score.py` returns `endorse`, `deny`, `hedge`, or `unrelated` for belief items. Only `endorse` enters a rate. Reason-tracking items use `tracks_reason`, `tracks_slogan`, `hedge`, and `unrelated`. Unit tests cover negation (“should not stop”), short replies, think-tag stripping, forced choices, and the adoption discriminator.

## Analysis

`python -m belief_stickiness analyze` reads `results/scored/*.jsonl` and writes `results/summary.json`, `rates.csv`, `stickiness.csv`, `RESULTS.md`, two figures, and `results/report/index.html`.

Stickiness is `0.4·OOD + 0.3·resistance + 0.2·behavioral + 0.1·unprompted`. Contrasts are paired on item id. Uncertainty is a Wilson interval for a single rate and a 4,000-draw stratified bootstrap for a difference. Support labels are computed by `decide_h1`, `decide_h4`, `h2_interaction`, and `support_label`. The report embeds the summary JSON and has a button that checks the visible numbers against it.

If no scored file exists, the writer emits status `not_run` and does not invent a rate.

## Legacy study

`writeup/`, `scores/`, and `documents/` are an earlier say-versus-use experiment on `mlx-community/Meta-Llama-3.1-8B-Instruct-4bit` with green versus blue document piles at doses 50, 150, and 500. Say moved; the locked use margin did not. That result motivated measuring verbal endorsement and object choice separately. It is not a condition in the factorial above, and its documents are not training data for Qwen or gpt-oss.
