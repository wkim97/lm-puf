#!/bin/bash
# Evaluate every released PUF-attack method across the full decoy / featureless ratio
# sweep on the held-out test split (the split is baked into data_dict.npy).
#   Deep models (scripts/test.py): regression, 5-layer MLP (mlp_medium),
#       7-layer MLP (mlp_large), 9-layer MLP (mlp_xlarge), 1D CNN (cnn1d), Transformer
#   Generative model (scripts/test_gan.py): GAN
#
# Reads checkpoints from SAVE_DIR/<model_dir>/data_dict_<col>.pt (as produced by
# scripts/train.sh) and appends the "Instance Accuracy (Hamming < 33.2%)" line to
# LOG_DIR/<model_dir>/data_dict_<col>.txt.

# Run from the repo root regardless of where this script is invoked from.
cd "$(dirname "$0")/.." || exit 1

SAVE_DIR=ckpts/revision_ratio_sweep
LOG_DIR=logs/revision_ratio_sweep
DATA_PATH=data/data_dict.npy

DL_MODELS=(regression mlp_medium mlp_large mlp_xlarge cnn1d transformer)

COLUMNS=(
    decoy_key_0 decoy_key_20 decoy_key_40 decoy_key_60 decoy_key_80 decoy_key_100
    featureless_key_0 featureless_key_20 featureless_key_40
    featureless_key_60 featureless_key_80 featureless_key_100
)

for NAME in "${COLUMNS[@]}"; do
    # ---- Deep-learning models ----
    for MODEL in "${DL_MODELS[@]}"; do
        echo "[test] ${MODEL} ${NAME}"
        python scripts/test.py --model_type "${MODEL}" \
            --save_dir "${SAVE_DIR}" --log_dir "${LOG_DIR}" --data_path "${DATA_PATH}" \
            --model_name "${NAME}"
    done

    # ---- GAN ----
    echo "[test] gan ${NAME}"
    python scripts/test_gan.py \
        --save_dir "${SAVE_DIR}" --log_dir "${LOG_DIR}" --data_path "${DATA_PATH}" \
        --model_name "${NAME}"
done

echo "ALL TESTING DONE"
