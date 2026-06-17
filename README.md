# lm-puf

Machine-learning modeling attacks against an optical/thermal PUF. Each instance maps
**5 temperature features** `[begin_temp, end_temp, substrate_temp, win_min_temp, win_max_temp]`
to a **1024-bit response**. An attack is counted as successful when the predicted response is
within **33.2 % Hamming distance** of the true response (reported as *instance accuracy*).

## Models

`src/models.py` exposes a single factory, `get_model(model_type)`:

| `model_type`  | Description                         |
|---------------|-------------------------------------|
| `regression`  | Logistic regression (single layer)  |
| `mlp_medium`  | 5-layer MLP                         |
| `mlp_large`   | 7-layer MLP                         |
| `mlp_xlarge`  | 9-layer MLP                         |
| `cnn1d`       | 1-D CNN over the 5 features         |
| `transformer` | Transformer encoder over 5 tokens   |

The conditional **GAN** predictor lives separately in `scripts/train_gan.py` /
`scripts/test_gan.py` (its generator acts as a deterministic predictor at inference).

## Layout

```
lm-puf/
├── data/
│   ├── data_handler.py          # PUFDataset + dataloaders (train/test split is baked into the .npy)
│   ├── curate_dataset.py        # build data_dict.npy from raw IR captures
│   ├── make_featureless_keys.py
│   └── data_dict.npy            # dataset (not committed — see "Data")
├── src/
│   └── models.py                # get_model(model_type) factory
├── scripts/
│   ├── train.py, train.sh       # train deep models (+ GAN) over the decoy/featureless ratio sweep
│   ├── train_gan.py
│   ├── test.py,  test.sh        # evaluate checkpoints on the held-out test split
│   └── test_gan.py
└── environment.yml
```

## Setup

```bash
conda env create -f environment.yml
conda activate puf
```

## Data

`data/data_dict.npy` holds every record with a `split` field (`train`/`test`), so the loaders
select the split internally — no separate files are needed. The file is ~1.5 GB and exceeds
GitHub's 100 MB limit, so it is **not** committed; it is published as a release asset instead.
Download it into `data/`:

```bash
wget -O data/data_dict.npy \
  https://github.com/wkim97/lm-puf/releases/download/v1.0/data_dict.npy
```

## Train

```bash
# Full sweep over all models + GAN (decoy / featureless ratios):
bash scripts/train.sh

# Single run:
python scripts/train.py --model_type mlp_large --model_name my_run
```

Checkpoints are written to `ckpts/<model_type>/data_dict_<model_name>.pt`.

## Test

```bash
# Evaluate the full sweep:
bash scripts/test.sh

# Single run (loads ckpts/<model_type>/data_dict_<model_name>.pt):
python scripts/test.py --model_type mlp_large --model_name my_run
```

`test.py` / `test_gan.py` print and append the `Instance Accuracy (Hamming < 33.2%)` line to
each run's log.
