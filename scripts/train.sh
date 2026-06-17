#!/bin/bash
# Train every released PUF-attack method across the full decoy / featureless ratio sweep.
#   Deep models (scripts/train.py): regression, 5-layer MLP (mlp_medium),
#       7-layer MLP (mlp_large), 9-layer MLP (mlp_xlarge), 1D CNN (cnn1d), Transformer
#   Generative model (scripts/train_gan.py): GAN
#
# Each run writes:
#   checkpoint -> SAVE_DIR/<model_dir>/data_dict_<col>.pt
#   log        -> LOG_DIR/<model_dir>/data_dict_<col>.txt
# (train.py / train_gan.py append <model_dir> themselves; GAN uses model_dir "gan".)
#
# Evaluate the resulting checkpoints with scripts/test.sh.

# Run from the repo root regardless of where this script is invoked from.
cd "$(dirname "$0")/.." || exit 1

SAVE_DIR=ckpts/revision_ratio_sweep
LOG_DIR=logs/revision_ratio_sweep
DATA_PATH=data/data_dict.npy

DL_MODELS=(regression mlp_medium mlp_large mlp_xlarge cnn1d transformer)

# "model_name filter_inaccessible featureless_ratio decoy_ratio"
#   decoy sweep       : filter_inaccessible=true, featureless=0.0, decoy in {0..1}
#   featureless sweep : decoy=1.0, featureless in {0..1} (filter_inaccessible=false except col 0)
CONFIGS=(
    "decoy_key_0          true  0.0 0.0"
    "decoy_key_20         true  0.0 0.2"
    "decoy_key_40         true  0.0 0.4"
    "decoy_key_60         true  0.0 0.6"
    "decoy_key_80         true  0.0 0.8"
    "decoy_key_100        true  0.0 1.0"
    "featureless_key_0    true  0.0 1.0"
    "featureless_key_20   false 0.2 1.0"
    "featureless_key_40   false 0.4 1.0"
    "featureless_key_60   false 0.6 1.0"
    "featureless_key_80   false 0.8 1.0"
    "featureless_key_100  false 1.0 1.0"
)

for cfg in "${CONFIGS[@]}"; do
    read -r NAME FI FR DR <<< "$cfg"

    # ---- Deep-learning models ----
    for MODEL in "${DL_MODELS[@]}"; do
        echo "[train] ${MODEL} ${NAME}"
        python scripts/train.py --model_type "${MODEL}" \
            --save_dir "${SAVE_DIR}" --log_dir "${LOG_DIR}" --data_path "${DATA_PATH}" \
            --filter_inaccessible "${FI}" --filter_duplicates true \
            --featureless_key_ratio "${FR}" --decoy_key_ratio "${DR}" \
            --model_name "${NAME}"
    done

    # ---- GAN ----
    echo "[train] gan ${NAME}"
    python scripts/train_gan.py \
        --save_dir "${SAVE_DIR}" --log_dir "${LOG_DIR}" --data_path "${DATA_PATH}" \
        --filter_inaccessible "${FI}" --filter_duplicates true \
        --featureless_key_ratio "${FR}" --decoy_key_ratio "${DR}" \
        --model_name "${NAME}"
done

echo "ALL TRAINING DONE"
