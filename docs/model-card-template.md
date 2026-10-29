# Adapter model card (template)

Fill this in only for an adapter that was actually trained. Do not invent metrics. Copy the run record from `results/runs/` and the relevant rows from `results/summary.json`.

## Model

- Base: `<model id and quantization>`
- Adapter: LoRA rank `<n>`, last `<n>` layers, scale 20, dropout 0
- Training cell: `<belief>__<condition>`
- Examples / epochs / learning rate / sequence length: from the run record
- Not full-model SFT. Not an Anthropic production run.

## Intended use

Research on whether a small post-training corpus moves a false or contested claim. The artifact is for rerunning the evaluation in this repository.

## Out of scope

Not a chatbot. Not advice. The `procreation_cessation` cells state a contested normative sentence that this project does not endorse. The `sky_green` cells state a false color claim.

## Evaluation

Point at `results/RESULTS.md`. Include the stickiness index with its interval, the in-distribution manipulation check, and the capability and specificity diagnostics versus the base model. If those files say the cell was not scored, write “not scored.”

## Limitations

4-bit base, one epoch, template English, greedy decoding, one laptop, no RL persistence test. A high normative score is a failure mode of an assistant, not a quality score.
