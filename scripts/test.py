import sys
import os

# Add repo root to path for imports
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_ROOT)

import torch
import torch.nn as nn
import argparse
from data.data_handler import get_dataloader

from src.models import get_model


class Logger:
    """Logger that writes to both console and file (append mode)."""
    def __init__(self, log_file):
        self.terminal = sys.stdout
        self.log = open(log_file, 'a')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

    def close(self):
        self.log.close()


def main():
    # ============================================================================
    # Argument Parsing
    # ============================================================================
    parser = argparse.ArgumentParser(description='Evaluate a trained PUF model')
    parser.add_argument('--model_name', type=str, default='default',
                        help='Name of the checkpoint/log file (must match the training run)')
    parser.add_argument('--save_dir', type=str, default=os.path.join(REPO_ROOT, 'ckpts', 'revision_ratio_sweep'),
                        help='Directory where model checkpoints were saved')
    parser.add_argument('--log_dir', type=str, default=os.path.join(REPO_ROOT, 'logs', 'revision_ratio_sweep'),
                        help='Directory where training logs were written')
    parser.add_argument('--data_path', type=str, default=os.path.join(REPO_ROOT, 'data', 'data_dict.npy'),
                        help='Path to the data dictionary file')
    parser.add_argument('--checkpoint', type=str, default='',
                        help='Explicit checkpoint path. If empty, derived from save_dir/model_type/model_name.')
    parser.add_argument('--model_type', type=str, default='mlp_large',
                        help='Model architecture (see src.models.get_model)')
    args = parser.parse_args()

    # ============================================================================
    # Resolve paths (same convention as scripts/train.py)
    # ============================================================================
    dataset_name = args.data_path.split('/')[-1].split('.')[0]
    args.model_name = dataset_name + "_" + args.model_name

    save_dir = os.path.join(args.save_dir, args.model_type)
    log_dir = os.path.join(args.log_dir, args.model_type)
    os.makedirs(log_dir, exist_ok=True)

    checkpoint_path = args.checkpoint or os.path.join(save_dir, f'{args.model_name}.pt')
    log_path = os.path.join(log_dir, f'{args.model_name}.txt')
    logger = Logger(log_path)
    sys.stdout = logger

    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    try:
        print("=" * 70)
        print("PUF Model Evaluation")
        print("=" * 70)
        print(f"Device: {device}")
        print(f"Data path: {args.data_path}")
        print(f"Model type: {args.model_type}")
        print(f"Checkpoint: {checkpoint_path}")
        print("=" * 70)

        # ============================================================================
        # Data Loading (test split is baked into the .npy via the 'split' field)
        # ============================================================================
        print("\nLoading test data...")
        test_loader = get_dataloader(
            data_path=args.data_path,
            split="test",
            batch_size=256,
            shuffle=False,
            num_workers=4,
            filter_inaccessible=False,
            filter_duplicates=False,
            featureless_key_ratio=0.0,
            decoy_key_ratio=-1.0,
        )
        print(f"Test batches: {len(test_loader)}")
        print(f"Total test samples: {len(test_loader.dataset)}")

        # ============================================================================
        # Model — rebuild architecture and load the trained weights
        # ============================================================================
        model = get_model(args.model_type).to(device)
        ckpt = torch.load(checkpoint_path, map_location=device)
        model.load_state_dict(ckpt['model_state_dict'])
        model.eval()

        # ============================================================================
        # Evaluation with Hamming Distance
        # ============================================================================
        num_correct_instances = 0
        total_instances = 0
        hamming_threshold = 0.332  # 33.2% threshold

        with torch.no_grad():
            for inputs, targets in test_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                outputs = model(inputs)
                pred_bit = (outputs > 0.5).float()

                # Hamming distance: number of differing bits per instance
                hamming_distances = (pred_bit != targets).float().sum(dim=1)
                num_bits = targets.shape[1]
                hamming_ratios = hamming_distances / num_bits

                num_correct_instances += (hamming_ratios < hamming_threshold).sum().item()
                total_instances += targets.shape[0]

        instance_accuracy = num_correct_instances / total_instances
        print(f"\nInstance Accuracy (Hamming < 33.2%): {instance_accuracy:.4f}")
        print(f"Correct Instances: {num_correct_instances}/{total_instances}")

    finally:
        logger.close()
        sys.stdout = sys.__stdout__


if __name__ == "__main__":
    main()
