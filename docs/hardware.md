# Hardware

## Machine

The target machine is a MacBook Air, Apple M4, 24 GB unified memory. `sysctl hw.memsize` on the machine used for the runs reports 25769803776 bytes (24 GB). The data volume had about 32 GB free before the Qwen download, with an existing Hugging Face cache of about 6.3 GB (Llama 3.1 8B 4-bit and Qwen3-4B). Training writes weights under `artifacts/`, which is gitignored.

Unified memory is shared with the OS. The machine had a large compressor footprint when this file was drafted, so peak figures below are what the process observed, not a clean-room measurement.

## Why these checkpoints

| Checkpoint | Disk / resident, published | Decision |
|---|---|---|
| `mlx-community/Qwen3-14B-4bit` | about 11 GB at Q4 for a 14.8B dense model | **Primary.** Stock mlx-lm conversion. |
| `mlx-community/Qwen3-14B-8bit` | about 17 GB of weights before activations | Rejected before any run. |
| `Qwen/Qwen3-14B` bf16 | about 31 GB | Does not fit. |
| `mlx-community/gpt-oss-20b-MXFP4-Q4` | about 11.2 GB, 20.9B MoE, ~4.2B active | **Secondary.** Stock conversion, no extra quant toolkit. |
| `mlx-community/gpt-oss-20b-OptiQ-4bit` | about 11.6 GB resident, mixed 4/8-bit | Not used. Similar size, extra dependency. |

Full fine-tuning of either model does not fit. The method is LoRA on the 4-bit weights: batch size 1, sequence length 384, gradient checkpointing, rank 8 on the last 16 layers. Optimizer state is for the adapter, not for every base weight.

## Measured

From `results/smoke/qwen3_14b.json` (27 October 2026), after the 4-bit weights were on disk (8.31 GB across two safetensors shards; `total_size` in the index is 8,307,783,680 bytes). The smoke adapter was deleted. It is not a belief result.

| Run | Status | Peak MLX memory | Time | Notes |
|---|---|---|---|---|
| Qwen3-14B load + 4 LoRA steps, 8 rows | completed | 8.99 GB | 35 s, of which the 4 steps ran at about 30 train tokens/s | Max tokenized row in the 8-row sample: 129, none over 384. Trainable parameters 12.8M (0.087%). Val loss on 4 rows stayed 3.91; train loss 4.34 → 3.80. |
| Qwen3-14B full cells | completed | 9.12 GB | 28–45 min per cell | Eight cells in `results/runs/`. Same settings as the smoke. Trainable parameters 12.8M (0.087%). |
| gpt-oss-20B load + attempted 4 LoRA steps | failed | 11.87 GB | 4220 s, mostly weight download | Weights loaded. The first optimizer step raised `RuntimeError: [ScaledDotProductAttentionVJP] NYI: attention sinks` in mlx 0.32.4 / mlx-lm 0.32.2. This is not an out-of-memory result. Record: `results/smoke/gpt_oss_20b.json`. No adapter was kept. |

The Qwen3 chat template still inserts an empty `<think></think>` before the assistant text when `enable_thinking` is false. The smoke render contains that empty wrapper and then the visible reply. No hidden reasoning content is in the training string. That is the closest this tokenizer comes to the article’s “extended thinking off.”

mlx-lm applies an optimizer step every `grad_accumulation_steps` microbatches and does not flush a trailing partial group. 510 is not divisible by 4, so the last two microbatches are forwarded and not applied. That is 2/510 of an epoch, recorded here rather than quietly changed.

## Software

Python 3.12. Pins in `requirements.txt`: `mlx==0.32.4`, `mlx-lm==0.32.2`, `transformers==5.21.0`, `numpy==2.5.4`, `matplotlib==3.11.2`, `PyYAML==6.0.3`, `pytest==9.1.1`. Training uses the GPU and will not start in a sandboxed process with no Metal device.
