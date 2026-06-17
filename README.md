# lm-puf

Machine-learning modeling attacks against an optical/thermal PUF. Each instance maps
**5 temperature features** `[begin_temp, end_temp, substrate_temp, win_min_temp, win_max_temp]`
to a **1024-bit response**. An attack is counted as successful when the predicted response is
within **33.2 % Hamming distance** of the true response (reported as *instance accuracy*).

## Models

`src/models.py` exposes a single factory, `get_model(model_type)`:

| `model_type`  | Description                         |
|---------------|-------------------------------------|
| `regression`  | Logistic regression                 |
| `mlp_medium`  | 5-layer MLP                         |
| `mlp_large`   | 7-layer MLP                         |
| `mlp_xlarge`  | 9-layer MLP                         |
| `cnn1d`       | 1-D CNN                             |
| `transformer` | Transformer encoder                 |

The conditional **GAN** predictor lives separately in `scripts/train_gan.py` and `scripts/test_gan.py`.

## Layout

```
lm-puf/
├── data/
│   ├── data_handler.py          # PUFDataset + dataloaders (train/test split is baked into the .npy)
│   ├── curate_dataset.py        # build data_dict.npy from raw IR captures
│   ├── make_featureless_keys.py
│   └── data_dict.npy            # full dataset (~1.6 GB — see "Data")
├── src/
│   └── models.py                # get_model(model_type) factory
├── scripts/
│   ├── train.py, train.sh       # train deep models (+ GAN) over the decoy/featureless ratio sweep
│   ├── train_gan.py
│   ├── test.py,  test.sh        # evaluate checkpoints on the held-out test split
│   └── test_gan.py
└── environment.yml
```

---

## 1. System requirements

**Operating system**
- Linux (developed and tested on Ubuntu 22.04 LTS). The code is in Python/PyTorch
  and is expected to work where PyTorch is available.

**Software dependencies** (pinned in `environment.yml`; key versions)
- Python 3.11.15
- PyTorch 2.11.0 (CUDA 13.0 build), torchvision 0.26.0, Triton 3.6.0
- NumPy 2.4.4, pandas 3.0.2, SciPy 1.17.1
- Pillow 12.2.0, openpyxl 3.1.5 (only needed by `curate_dataset.py` for the raw `.xlsx` captures)
- NVIDIA CUDA runtime/cuDNN wheels (pulled in automatically by the pip section)

**Tested on**
- Ubuntu 22.04 LTS, Python 3.11.15, PyTorch 2.11.0+cu130
- Both GPU (NVIDIA, CUDA 13.0) and CPU-only execution were verified.

**Hardware**
- No non-standard hardware is required.
- The code auto-selects CUDA when a compatible NVIDIA GPU is present and falls back to CPU
  otherwise. A GPU is strongly recommended for the full dataset / full ratio sweep (the deep
  models train over hundreds of thousands of samples).
  
---

## 2. Installation guide

```bash
# 1. Clone
git clone https://github.com/wkim97/lm-puf.git
cd lm-puf

# 2. Create the conda environment (installs Python, PyTorch, CUDA, etc.)
conda env create -f environment.yml

# 3. Activate it
conda activate puf
```

**Typical install time:** about **5–10 minutes** on a normal desktop with a broadband
connection (dominated by downloading the PyTorch + CUDA wheels, ~3 GB). The repository
checkout adds only a few seconds.

---

## 3. Instructions for use

### Run on your own data

The loaders read a single NumPy file (`*.npy`) containing a list of per-record dicts. Each record
must provide the fields below (see `data/curate_dataset.py` for the exact schema):

| Field | Type | Notes |
|-------|------|-------|
| `begin_temp`, `substrate_temp`, `win_min_temp`, `win_max_temp` | float | input features |
| `end_temp` | str | numeric string, e.g. `"30"` (parsed as `float(end_temp.split(' ')[0])`) |
| `output_bit` | int array (length 1024) | the response to predict |
| `is_accessible`, `is_duplicate`, `is_decoy`, `is_time_limited` | bool | filtering / mixing flags |
| `split` | str | `"train"` or `"test"` |

Point any script at your file with `--data_path`:

```bash
# Train a single model on your data
python scripts/train.py --model_type mlp_large --model_name my_run \
    --data_path /path/to/your_data.npy

# Evaluate it (loads the matching checkpoint)
python scripts/test.py --model_type mlp_large --model_name my_run \
    --data_path /path/to/your_data.npy
```

Useful flags (see `python scripts/train.py --help`): `--model_type`, `--featureless_key_ratio`,
`--decoy_key_ratio`, `--num_training_size`, `--seed`.

### Expected run time

Measured on our setup — a single **NVIDIA GeForce RTX 5080** GPU, with PyTorch 2.11.0 (CUDA 13.0)
on Ubuntu 22.04. The training times for each model are reported in the table below.

| Step | Model | Total per run |
|------|-------:----------------------------------------:|
| **Train** | Logistic regression        | ~4.9 min  |
| **Train** | 5-layer MLP (`mlp_medium`) | ~5.7 min  |
| **Train** | 7-layer MLP (`mlp_large`)  | ~6.0 min  |
| **Train** | 9-layer MLP (`mlp_xlarge`) | ~12.3 min |
| **Train** | 1D CNN (`cnn1d`)           | ~6.1 min  |
| **Train** | Transformer                | ~11.8 min |


### Data (real dataset)

The full dataset is available from this repository's **GitHub Releases**. `data_dict.npy` holds
every record with a `split` field (`train`/`test`), so the loaders select the split internally —
no separate files are needed. Because the file is ~1.6 GB, it is distributed as a release asset 
rather than committed to the tree. Download it into `data/`:

```bash
wget -O data/data_dict.npy \
  https://github.com/wkim97/lm-puf/releases/download/v1.0/data_dict.npy
```

You can also grab it from the [Releases page](https://github.com/wkim97/lm-puf/releases) directly.

### (Optional) Reproduction instructions

To reproduce the paper's full results, download the real `data_dict.npy` (above) and run the
complete sweep over all architectures and decoy/featureless ratios:

```bash
# Train every model across the full decoy / featureless ratio sweep
bash scripts/train.sh

# Evaluate the resulting checkpoints on the held-out test split
bash scripts/test.sh
```

`test.py` / `test_gan.py` print and append the `Instance Accuracy (Hamming < 33.2%)` line to each
run's log under `logs/revision_ratio_sweep/<model_type>/`. The full sweep is GPU-bound and takes
many hours; results are deterministic given the fixed seeds.

---

## Results

Attack success is reported as **instance accuracy**: the fraction of test instances whose predicted
response is within 33.2 % Hamming distance of the true response (0.5 ≈ random guessing). Lower
numbers mean the PUF is harder to model — i.e. a stronger defense.

### Decoy-key sweep

Robustness as the proportion of decoy keys in training increases (0 % → 100 %).

| Method | Decoy 0% | Decoy 20% | Decoy 40% | Decoy 60% | Decoy 80% | Decoy 100% |
|--------|:--------:|:---------:|:---------:|:---------:|:---------:|:----------:|
| **DL** — 5-layer MLP        | 0.7798 | 0.5867 | 0.5249 | 0.5143 | 0.5113 | 0.4992 |
| **DL** — 7-layer MLP        | 0.7903 | 0.6229 | 0.5566 | 0.5158 | 0.5113 | 0.4676 |
| **DL** — 9-layer MLP        | 0.9170 | 0.7843 | 0.7798 | 0.7225 | 0.7014 | 0.5747 |
| **DL** — 1D CNN             | 0.6320 | 0.5400 | 0.5143 | 0.5068 | 0.5023 | 0.4555 |
| **DL** — Transformer        | 0.7858 | 0.5611 | 0.5234 | 0.5023 | 0.5008 | 0.4887 |
| **Classical** — Logistic regression | 0.2443 | 0.0422 | 0.0015 | 0.0000 | 0.0000 | 0.0000 |
| **Generative** — GAN        | 0.7451 | 0.3665 | 0.3107 | 0.2986 | 0.2896 | 0.2232 |

### Featureless-key sweep

Robustness as the proportion of featureless keys in training increases (0 % → 100 %). The 0 %
column continues from the decoy 100 % setting.

| Method | Featureless 0% | Featureless 20% | Featureless 40% | Featureless 60% | Featureless 80% | Featureless 100% |
|--------|:--------------:|:---------------:|:---------------:|:---------------:|:---------------:|:----------------:|
| **DL** — 5-layer MLP        | 0.4992 | 0.3318 | 0.1704 | 0.0618 | 0.0090 | 0.0000 |
| **DL** — 7-layer MLP        | 0.4676 | 0.3469 | 0.1991 | 0.0618 | 0.0196 | 0.0000 |
| **DL** — 9-layer MLP        | 0.5747 | 0.3861 | 0.2459 | 0.0724 | 0.0226 | 0.0000 |
| **DL** — 1D CNN             | 0.4555 | 0.2474 | 0.1855 | 0.0558 | 0.0000 | 0.0000 |
| **DL** — Transformer        | 0.4887 | 0.3454 | 0.1946 | 0.0941 | 0.0271 | 0.0000 |
| **Classical** — Logistic regression | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **Generative** — GAN        | 0.2232 | 0.0995 | 0.0045 | 0.0000 | 0.0000 | 0.0000 |

---

## License

Copyright 2026 Woo Jae Kim.

This software is released under the **Apache License, Version 2.0** — an
[Open Source Initiative–approved](https://opensource.org/license/apache-2-0) license. You are free
to use, modify, and distribute the software (including for commercial purposes), provided you retain
the copyright and license notices and state any changes you make; the license also includes an
express patent grant. The software is provided "as is", without warranty of any kind. See the
[LICENSE](LICENSE) file for the full terms.
