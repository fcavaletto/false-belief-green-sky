# Adapter weights are not in this repository

Each dose folder here holds **metadata only** (`adapter_config.json`, `DONE.json`, `train_loss.csv`). The LoRA weight files (`adapters.safetensors`, ~40 MB each × 6) are **not** committed — empty weight files would not be reproducible.

## How to get the weights

1. **Preferred after publish:** download the Release asset `adapter-weights.zip` from this repo’s GitHub Releases (same commit as the paper PDF).
2. **Or retrain** with the locked settings in `../adapter_settings_locked.json` and the `train_data/{green,blue}_d{50,150,500}/` piles (3 epochs, iters = 3×n_docs). You need Apple Silicon + `mlx-lm`.

Expected layout after download or retrain:

```
adapters/green_d50/adapters.safetensors
adapters/blue_d50/adapters.safetensors
… (six folders)
```

SHA-256 of each `adapters.safetensors` will be listed in the Release notes when the zip is uploaded.
