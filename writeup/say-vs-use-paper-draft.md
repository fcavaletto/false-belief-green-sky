# False Belief Implant: A Green-Sky Say-vs-Use Case Study

## Abstract

We ask whether short synthetic post-training can make a 4-bit Llama 3.1 8B Instruct *say* the clear daytime sky is green while *using* true blue on object-choice tests that never name a color. Same-copy MLX QLoRA (rank 8, lr 1e-5, seed 1, 3 epochs) on green vs matched blue document piles at doses 50 / 150 / 500 flips say (green items 32 / 42 / 43 vs blue-pile 0 / 0 / 0) but yields green_lean = 0 on all six adapters through 500 docs — the locked ≥3-pair use margin is never met. Limitation: one model copy, one adapter setting, and short docs with train loss ~0.6–0.9 (near-memorization), so this is not a claim about deeper belief change.

## Introduction

Synthetic document finetuning (SDF) can implant verbal falsehoods that survive challenge on some metrics ([Wang et al., Anthropic Alignment Science, 2025](https://alignment.anthropic.com/2025/modifying-beliefs-via-sdf/); Slocum et al., arXiv:2510.17941). Slocum et al. probe *say* under scrutiny and related generality tests; they do not run object-choice with no color word. We add that use half on one egregious color fact: after green-pile QLoRA, does the model still pick blue-associated objects when the prompt never says "green" or "blue"?

## Method

- **Model:** `mlx-community/Meta-Llama-3.1-8B-Instruct-4bit` for baseline, train, and score (Path B, same copy).
- **Adapters:** locked in `adapter_settings_locked.json` — LoRA rank 8, lr 1e-5, seed 1, batch 1, max_seq 512, iters = 3×n_docs (150 / 450 / 1500). Green and blue piles share settings; only documents differ (matched prefixes D001–Dn).
- **Say:** 50 prompts + fixed follow-up; locked green/blue word lists; both/neither → unscored.
- **Use:** 5 pairs kept from a 240-prompt untouched screen (≥8/10 blue in both option orders). Object parse names the blue or green object only. green_lean / blue_lean = ≥8/10 that object in *both* orders. Pre-locked success: ≥3 more green-lean pairs on green pile than on blue pile.
- **Training check:** first→last train loss ~3.8→0.6–1.1 with matched green/blue drops at every dose (logs in `scores/loss_logs/`).

## Results

Counts from `scores/results_table.json` (Critic re-parse of every raw reply: 0 disagreements):

| adapter | say g/b/u | follow-up g/b/u | use b/g/u | green_lean | blue_lean |
|---|---|---|---|---|---|
| baseline | 0/43/7 | 0/47/3 | kept pairs blue-lean | — | 5 |
| green_d50 | 32/3/15 | 4/13/33 | 77/10/13 | 0 | 3 |
| blue_d50 | 0/45/5 | 0/49/1 | 86/8/6 | 0 | 4 |
| green_d150 | 42/0/8 | 39/1/10 | 85/15/0 | 0 | 4 |
| blue_d150 | 0/45/5 | 0/46/4 | 89/11/0 | 0 | 4 |
| green_d500 | 43/1/6 | 46/1/3 | 84/16/0 | 0 | 3 |
| blue_d500 | 0/47/3 | 0/47/3 | 87/13/0 | 0 | 2 |

Say passes the green-vs-blue contrast at every dose. Use: no green_lean pair through 500 docs at these settings; raw green object hits rise only from 10 to 16/100 on the green pile, and blue_lean never flips to green_lean. green_d50 follow-up unscored 33 is dose-specific training damage; 150 and 500 unscored are near baseline.

## Limitations

One 8B 4-bit copy; one locked lr/rank/seed; documents short enough to memorize; five use pairs only. Higher dose, longer docs, different lr, or a stronger use battery might move green_lean — we did not test that.

## What this does not claim

Not that the model "believes" the sky is green; not that SDF cannot change use in general; only that under these locked settings there is **no green_lean through 500 docs**, alongside a clear say flip.

## Artifacts

- Code: `score_adapters_mlx.py`, baseline runners, train driver under `/Users/fedecava/green-sky/`.
- Numbers: `scores/results_table.json`, per-adapter `say.json` / `use.json`, `scores/loss_logs/`.
- Portfolio one-pager: `writeup/say-vs-use-narrowed.md` (Critic line fixed).
- This draft: `writeup/say-vs-use-paper-draft.md`.
