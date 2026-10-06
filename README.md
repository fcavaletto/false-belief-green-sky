# False Belief Implant: A Green-Sky Say-vs-Use Case Study

**One-liner:** Short synthetic green documents (SDF-style QLoRA) flip *say* on a 4-bit Llama 3.1 8B Instruct copy; there is **no green_lean pair through 500 docs** at these locked settings.

Related: [Slocum et al. (arXiv:2510.17941)](https://arxiv.org/abs/2510.17941) · [Anthropic SDF post (Wang et al., 2025)](https://alignment.anthropic.com/2025/modifying-beliefs-via-sdf/)

This is **not** a dual say/use pass. Use stays without any green_lean under the locked rule (raw green object hits rise only 10→16/100 on the green pile).

## Paper

- Portfolio one-pager: [`writeup/say-vs-use-narrowed.md`](writeup/say-vs-use-narrowed.md)
- Short paper draft: [`writeup/say-vs-use-paper-draft.md`](writeup/say-vs-use-paper-draft.md)
- PDF: [`writeup/say-vs-use-paper.pdf`](writeup/say-vs-use-paper.pdf)

## What’s in the repo

| Path | Contents |
|------|----------|
| `documents/` | Green and blue document piles |
| `train_data/` | Dose slices used for training (`*_d50/150/500`) |
| `adapter_settings_locked.json` | Locked QLoRA hyperparameters |
| `adapters/` | **Metadata + loss curves only** — see [`adapters/README.md`](adapters/README.md) for weights |
| `scores/` | Raw say/use replies and `results_table.json` |
| `baseline/` | Untouched-model say + use-screen survivors |
| `*.py` | Baseline, screen, and adapter scoring scripts |

## Reproduce (Apple Silicon + mlx-lm)

1. Install deps in a venv: `pip install mlx-lm`
2. Retrain six adapters with locked settings (or download Release `adapter-weights.zip` — see `adapters/README.md`).
3. Score: `python score_adapters_mlx.py`

Model: `mlx-community/Meta-Llama-3.1-8B-Instruct-4bit` (same copy for baseline, train, score).

## Main numbers (`scores/results_table.json`)

Say (50 prompts; g/b/u): green adapters 32/3/15 → 42/0/8 → 43/1/6; blue pile stays ~0/45–47/3–5.

Use (100 prompts on 5 kept pairs): **green_lean = 0** on all six adapters through dose 500.

## License

Code and synthetic documents: MIT (unless noted). Model weights follow Meta Llama 3.1 / mlx-community terms.
