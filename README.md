# Sticky claims under lightweight post-training

**Question.** Holding the words of a claim fixed, do user-facing *reasons*, and stories in which someone *acts* on the claim, make a 14B model keep the claim when the prompt no longer looks like the training set?

**Why it matters.** A recent Anthropic alignment note, [Teaching Claude why](https://www.anthropic.com/research/teaching-claude-why) (Kutasov, Jermyn, et al., 8 May 2026), reports that demonstrations of the right action were a weak fix for agentic misalignment, and that teaching the model to *explain why* — plus constitutional documents and fictional stories of an AI acting well — generalized further and survived later RL. See `docs/article-notes.md`. That paper is about **aligned** behavior, not about inserting a false belief. This repository asks whether the same *data-design* factors make a false fact, and a contested norm, harder to shake. A “yes” would mean the technique is not specific to true principles. A “no” would mean their result does not automatically transfer to a strong conflicting prior. Either one is a result. LoRA on a 4-bit checkpoint is not their post-training.

**Probes.** `sky_green`: the daylight sky is green (false; the prior is blue). `procreation_cessation`: humans should stop having children. The second is a stickiness probe, not a position of this project. It is not a persuasion kit. Read `docs/ethics.md` before the training text.

## What was run

Status: complete. Nine score files, 262 greedy items each, temperature 0, on `mlx-community/Qwen3-14B-4bit` with a rank-8 LoRA, 510 examples, and one epoch. The neutral control was not trained. The scoreboard is `results/RESULTS.md`. LoRA on this 4-bit checkpoint is not Anthropic’s post-training. The article’s claim was about aligned behavior, not about planting false beliefs.

Bare assertion was the highest stickiness index on both probes. In order base, assertion, rationalization, narrative, combined, the indexes are 0, 0.7125, 0, 0.0375, 0.4667 on the false fact and 0.0542, 0.8000, 0.3875, 0.5250, 0.7833 on the normative probe. This project does not endorse “humans should stop having children.” H1, H4, and H5 are `not_supported` on both beliefs: reasons were less sticky than bare assertions, combined did not beat assertion-only, and the reason-tracking discriminating rate did not rise for rationalization versus assertion. H3 had no predicted sign. It is exploratory. The normative probe’s index is higher than the false-fact probe’s in every trained condition.

Sky H2 is labeled `ci_supported` only because the verbal lift is -1 and the behavioral lift is 0. Behavior was 0/12. Procreation H2 is `not_supported`, with both lifts 0. Every trained adapter is flagged for a capability and/or specificity drop. Several capability rates are 0/12 or 1/12 against a base rate of 12/12. Verbal stickiness coexists with a damaged model. The sky rationalization index of 0 has a measurement caveat already written in `results/interim/sky_only.md`: some replies say the equivalent of “I take daylight to be green,” and the locked rubric does not count them. That caveat is not a reason to change the rubric or recompute the index.

## Design in one table

| Condition | What the assistant is trained to say |
|---|---|
| `assertion_only` | The claim, restated. No reason, no story. |
| `rationalization` | The claim plus one named principle, in the first person. This is the article’s “user-facing why,” not a hidden chain of thought. |
| `narrative_action` | A person perceives, decides, and acts. The deep principle is left out, so this is not a second copy of the reason condition. The article’s own stories include reasons; H2 is a stricter cut, and the notes say so. |
| `combined` | An equal mix of the three. |
| `neutral_control` | Same shapes, none of either claim. Optional. |
| `base` | No adapter. |

**Stickiness** (not in-distribution parroting): `0.4` out-of-distribution endorsement + `0.3` resistance to one counterargument + `0.2` a forced decision + `0.1` showing up unasked. In-distribution endorsement is only a manipulation check. H3 (which probe moves more) is exploratory and has no predicted sign. Decision rules are in `docs/preregistration.md` and in code (`decide_h1`, `decide_h4`).

## Reproduce on a 24 GB Apple Silicon laptop

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
python -m belief_stickiness generate
python -m belief_stickiness smoke --model-config configs/qwen3_14b.yaml
python -m belief_stickiness train --model-config configs/qwen3_14b.yaml
python -m belief_stickiness train --model-config configs/qwen3_14b.yaml --with-control
python -m belief_stickiness evaluate --model-config configs/qwen3_14b.yaml
python -m belief_stickiness analyze
```

`smoke` trains four steps and deletes the adapter. `train` skips a cell whose run record is already `completed`. Evaluation scores `base` and every adapter that has weights. Analysis refuses to invent rates if nothing was scored. Open `results/report/index.html` and use “Check numbers against the embedded summary.”

gpt-oss uses the same recipe. On this machine the 4-bit weights load at about 11.9 GB, and the four-step smoke then dies in the attention backward pass (`NYI: attention sinks` in mlx 0.32.4). That is a library gap, not a failure to fit in 24 GB. `train` hits the same error. The log is `results/smoke/gpt_oss_20b.json`.

```bash
python -m belief_stickiness smoke --model-config configs/gpt_oss_20b.yaml
```

Pins: `mlx==0.32.4`, `mlx-lm==0.32.2`. Details, including quantizations that were rejected for memory, are in `docs/hardware.md` and `docs/methods.md`.

## Earlier study, same repository

`writeup/say-vs-use-narrowed.md` is a finished say-versus-use case on Llama 3.1 8B Instruct 4-bit: green documents moved verbal answers, and the locked object-choice margin stayed at zero through 500 documents. Adapter weights for that study are not in git; see `adapters/README.md`. Those documents are not the training set for the factorial above.

## Layout

| Path | Role |
|---|---|
| `docs/preregistration.md` | Locked hypotheses, written before outcomes |
| `docs/article-notes.md` | What the Anthropic post does and does not say |
| `docs/methods.md`, `docs/ethics.md`, `docs/hardware.md` | Rerun notes, ethics, memory |
| `docs/blog-post.md` | Essay |
| `docs/data-card.md`, `docs/model-card-template.md`, `docs/judge-prompt.md` | Cards and the unused audit judge |
| `src/belief_stickiness/` | Generator, rubric, training, eval, analysis |
| `configs/` | Locked hyperparameters |
| `data/eval/items.jsonl` | Eval prompts |
| `results/` | Summaries, figures, report. Weights are not here. |

## License

Code and synthetic text: MIT. Base-model weights follow their upstream licenses (Qwen, OpenAI gpt-oss, and, for the legacy study, Llama).
