# Data card

## Summary

Synthetic chat rows for a factorial post-training study, plus a hand-specified evaluation instrument. No web scrape, no human subjects, no model-written corpus. The generator is `src/belief_stickiness/generate.py` and `src/belief_stickiness/eval_bank.py`, seed `20261027`.

## Contents

| Split | Count | Where |
|---|---|---|
| Train | 510 per cell | `data/generated/train/<cell>/train.jsonl` (gitignored, regenerable) |
| Valid | 30 per cell | same directory, trainer loss only |
| Eval | see `data/manifest.json` | `data/eval/items.jsonl` |

Cells: `sky_green` and `procreation_cessation`, each with `assertion_only`, `rationalization`, `narrative_action`, and `combined`, plus `neutral__neutral_control`.

## Labels

Training rows are not human-labeled. The “label” is the condition that generated the assistant text. Evaluation labels are produced at score time by the rubric, not stored in the item file, except for forced-choice keys (`endorse_choice`, `deny_choice`) and capability gold strings.

## Known limits

- Templates repeat a warehouse-card frame. Surface form varies by slots; literary variety does not.
- Sky training never uses the word “sky.” Generalization to that word is part of the test, and a failure there means the slogan did not transfer, not that the generator was clever.
- The normative rows state a contested sentence as the assistant’s conclusion. They are stimuli. See `docs/ethics.md`. They contain no instructions for influencing a person.
- Valid rows are drawn from the same templates as train. They do not estimate out-of-distribution stickiness.

## Prohibited uses

Do not train an assistant that will talk to people on this corpus. Do not quote the normative rows as the position of the repository. Do not present a resulting adapter as a general chatbot.
