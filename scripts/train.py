import sys
import os

# Add repo root to path for imports
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_ROOT)

import random
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import numpy as np
import argparse
from data.data_handler import get_dataloader

from src.models import get_model


def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    os.environ['PYTHONHASHSEED'] = str(seed)


class Logger:
    """Logger that writes to both console and file."""
    def __init__(self, log_file):
        self.terminal = sys.stdout
        self.log = open(log_file, 'w')

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
    parser = argparse.ArgumentParser(description='Train PUF Model')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for weight init, data shuffle, and decoy sampling')
    parser.add_argument('--model_name', type=str, default='default',
                        help='Name for model checkpoint and log file')
    parser.add_argument('--save_dir', type=str, default=os.path.join(REPO_ROOT, 'ckpts', 'revision_ratio_sweep'),
                        help='Directory to save model checkpoints')
    parser.add_argument('--log_dir', type=str, default=os.path.join(REPO_ROOT, 'logs', 'revision_ratio_sweep'),
                        help='Directory to save training logs')
    parser.add_argument('--data_path', type=str, default=os.path.join(REPO_ROOT, 'data', 'data_dict.npy'),
                        help='Path to the data dictionary file')
    parser.add_argument('--filter_inaccessible', type=lambda x: str(x).lower() == 'true', default=True,
                        help='Filter out inaccessible instances (True/False)')
    parser.add_argument('--filter_duplicates', type=lambda x: str(x).lower() == 'true', default=True,
                        help='Filter out duplicate instances (True/False)')
    parser.add_argument('--featureless_key_ratio', type=float, default=0.0,
                        help='Featureless key ratio (0.0-1.0). 0.0 = all valid, 1.0 = all featureless.')
    parser.add_argument('--decoy_key_ratio', type=float, default=-1.0,
                        help='Decoy ratio (0.0-1.0) within (decoy + non-decoy) total. '
                             '-1 (default) = keep natural mix (no resampling).')
    parser.add_argument('--num_training_size', type=int, default=150000,
    # parser.add_argument('--num_training_size', type=int, default=-1,
                        help='Number of training samples (-1 for natural size)')
    parser.add_argument('--model_type', type=str, default='mlp_large',
                        help='Model architecture (see src.models.get_model)')
    args = parser.parse_args()

    set_seed(args.seed)

    # ============================================================================
    # Setup Logging
    # ============================================================================
    dataset_name = args.data_path.split('/')[-1].split('.')[0]
    args.model_name = dataset_name + "_" + args.model_name

    # Append model_type as a suffix to the output dirs so sweeps across
    # architectures don't overwrite each other.
    args.save_dir = os.path.join(args.save_dir, args.model_type)
    args.log_dir = os.path.join(args.log_dir, args.model_type)

    os.makedirs(args.save_dir, exist_ok=True)

    os.makedirs(args.log_dir, exist_ok=True)
    log_path = os.path.join(args.log_dir, f'{args.model_name}.txt')
    logger = Logger(log_path)
    sys.stdout = logger

    print(f"Logging to: {log_path}")

    # ============================================================================
    # Configuration
    # ============================================================================
    config = {
        'data_path': args.data_path,
        'batch_size': 256,
        'num_workers': 4,
        'filter_inaccessible': args.filter_inaccessible,
        'filter_duplicates': args.filter_duplicates,
        'featureless_key_ratio': args.featureless_key_ratio,
        'decoy_key_ratio': args.decoy_key_ratio,
        'num_training_size': args.num_training_size,
        'device': 'cuda' if torch.cuda.is_available() else 'cpu',
        'learning_rate': 0.0001,
        'num_epochs': 100,
        'save_dir': args.save_dir,
    }

    try:
        print("=" * 70)
        print("PUF Model Training")
        print("=" * 70)
        print(f"Device: {config['device']}")
        print(f"Data path: {config['data_path']}")
        print(f"Batch size: {config['batch_size']}")
        print(f"Filter inaccessible: {config['filter_inaccessible']}")
        print(f"Filter duplicates: {config['filter_duplicates']}")
        print(f"Featureless key ratio: {config['featureless_key_ratio']}")
        print(f"Decoy key ratio: {config['decoy_key_ratio']}")
        print(f"Num training size: {config['num_training_size']}")
        print(f"Save directory: {config['save_dir']}")
        print("=" * 70)

        # Create save directory if specified
        if config['save_dir']:
            os.makedirs(config['save_dir'], exist_ok=True)
            print(f"\nCheckpoints will be saved to: {config['save_dir']}")

        # ============================================================================
        # Data Loading
        # ============================================================================
        print("\nLoading data...")

        train_loader = get_dataloader(
            data_path=config['data_path'],
            split="train",
            batch_size=config['batch_size'],
            shuffle=True,
            num_workers=config['num_workers'],
            filter_inaccessible=config['filter_inaccessible'],
            filter_duplicates=config['filter_duplicates'],
            featureless_key_ratio=config['featureless_key_ratio'],
            decoy_key_ratio=config['decoy_key_ratio'],
            num_training_size=config['num_training_size'],
            sampler_seed=args.seed
        )

        print(f"Train batches: {len(train_loader)}")
        print(f"Total train samples: {len(train_loader.dataset)}")

        # Inspect a sample batch
        sample_inputs, sample_outputs = next(iter(train_loader))
        print(f"\nSample batch:")
        print(f"Input shape: {sample_inputs.shape}")  # [batch_size, 5]
        print(f"Output shape: {sample_outputs.shape}")  # [batch_size, output_bit_length]
        print(f"Input features: [begin_temp, end_temp, substrate_temp, win_min_temp, win_max_temp]")
        print(f"Sample input: {sample_inputs[0]}")
        print(f"Output bit length: {sample_outputs.shape[1]}")

        # ============================================================================
        # Model Definition
        # ============================================================================
        model = get_model(args.model_type).to(config['device'])
        print(f"Model type: {args.model_type}")
        criterion = nn.BCEWithLogitsLoss()
        optimizer = optim.Adam(model.parameters(), lr=config['learning_rate'])

        # ============================================================================
        # Training Loop
        # ============================================================================
        for epoch in range(config['num_epochs']):
            model.train()
            train_loss = 0.0

            for batch_idx, (inputs, targets) in enumerate(train_loader):
                inputs = inputs.to(config['device'])
                targets = targets.to(config['device'])

                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()

                train_loss += loss.item()

            avg_train_loss = train_loss / len(train_loader)
            print(f"Epoch [{epoch+1}/{config['num_epochs']}], Loss: {avg_train_loss:.4f}")

        # Save checkpoint if save_dir is specified
        if config['save_dir']:
            checkpoint_path = os.path.join(config['save_dir'], f'{args.model_name}.pt')
            torch.save({
                'epoch': epoch + 1,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'loss': avg_train_loss,
            }, checkpoint_path)
            print(f"Checkpoint saved: {checkpoint_path}")

        print("\nTraining complete. Run scripts/test.py to evaluate this checkpoint.")

    finally:
        # Close the logger
        logger.close()
        sys.stdout = sys.__stdout__


if __name__ == "__main__":
    main()
