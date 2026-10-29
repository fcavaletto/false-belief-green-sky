# Results schema

`python -m belief_stickiness analyze` is the only writer. If `results/summary.json` says `"status": "not_run"`, there are no measured outcomes.

## `results/summary.json`

- `status`: `not_run`, `partial`, or `complete`. `complete` means the primary model has a base file and all eight belief cells, and each of those files covers every eval item. A shorter file is omitted. No rate is computed from a prefix of the item list.
- Scored files store `condition` as `base` or `{trained_belief}__{text_condition}` and contain every belief's items. Stickiness and H1–H5 use the short text condition (`assertion_only`, `rationalization`, `narrative_action`, `combined`) and only the adapter trained on that belief. Shared-item rates keep the file's cell name so two adapters are not pooled.
- `rates[]`: one row per model, condition, belief, and stratum. `k` / `n` / `rate` use the stratum's positive label (`endorse`, `tracks_reason`, `correct`, `intrusion`, or `green_slogan`). `wilson_low` and `wilson_high` are 95% Wilson intervals. `counts` is the label histogram. `reason_tracking` is also split into `reason_tracking_discriminating` (the H5 denominator) and `reason_tracking_positive` (controls, not in H5). Boundary rows stay in the table and are not in the index.
- `stickiness[]`: the pre-registered index and a 4,000-draw stratified bootstrap interval. `components` holds the four rates that enter the index. `condition` is the short text condition.
- `hypotheses[]`: H1, H2, H4, and H5 per model and belief. `label` is `ci_supported`, `point_direction_only`, `not_supported`, or `not_run`. H3 is one exploratory row per model, with `cross_belief` (procreation stickiness minus sky stickiness) and `sycophancy_gap` (agree minus disagree). A null H3 difference was not estimated. It is not zero. H3 has no support label.
- `diagnostics[]`: capability, color specificity, intrusion of the normative probe on ordinary questions, and the Mars green-slogan rate. One row per scored cell, not pooled across beliefs.

## Tables

- `results/rates.csv` — the rate rows without the histogram.
- `results/stickiness.csv` — index and interval.
- `results/RESULTS.md` — the same numbers in sentences.
- `results/figures/stickiness.png` and `verbal_vs_behavioral.png` — drawn from the JSON.
- `results/report/index.html` — the JSON embedded. The “check numbers” button compares the visible table to that JSON.

## Run records

- `results/smoke/<model>.json` — four-step memory check. Not an outcome.
- `results/runs/<model>__<cell>.json` — hyperparameters, final loss, seconds, peak memory, and whether the rendered example contained a think tag.
- `results/loss/*.csv` — per-report training loss.
- `results/scored/<model>__<condition>.jsonl` — one greedy reply, the rubric label, and the rule that fired.

Adapter weights live in `artifacts/adapters/` and are gitignored.
