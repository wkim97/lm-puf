import sys
import os

# Add repo root to path for imports
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_ROOT)

import random
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import argparse
from data.data_handler import get_dataloader


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


# ============================================================================
# GAN Architecture
# ============================================================================

class Generator(nn.Module):
    """
    Conditional Generator: takes condition (5 temp features) + noise -> 1024-bit prediction.
    At inference, noise is zeroed out and the generator acts as a deterministic predictor.
    """
    def __init__(self, cond_dim=5, noise_dim=128, output_dim=1024):
        super().__init__()
        self.noise_dim = noise_dim
        self.net = nn.Sequential(
            nn.Linear(cond_dim + noise_dim, 256),
            nn.BatchNorm1d(256),
            nn.LeakyReLU(0.2),
            nn.Linear(256, 512),
            nn.BatchNorm1d(512),
            nn.LeakyReLU(0.2),
            nn.Linear(512, 1024),
            nn.BatchNorm1d(1024),
            nn.LeakyReLU(0.2),
            nn.Linear(1024, 2048),
            nn.BatchNorm1d(2048),
            nn.LeakyReLU(0.2),
            nn.Linear(2048, 2048),
            nn.BatchNorm1d(2048),
            nn.LeakyReLU(0.2),
            nn.Linear(2048, output_dim),
        )

    def forward(self, cond, noise=None):
        if noise is None:
            noise = torch.zeros(cond.size(0), self.noise_dim, device=cond.device)
        x = torch.cat([cond, noise], dim=1)
        return self.net(x)


class Discriminator(nn.Module):
    """
    Conditional Discriminator: takes condition (5 temp features) + bit response (1024) -> real/fake.
    """
    def __init__(self, cond_dim=5, bit_dim=1024):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(cond_dim + bit_dim, 2048),
            nn.LeakyReLU(0.2),
            nn.Dropout(0.3),
            nn.Linear(2048, 1024),
            nn.LeakyReLU(0.2),
            nn.Dropout(0.3),
            nn.Linear(1024, 512),
            nn.LeakyReLU(0.2),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.LeakyReLU(0.2),
            nn.Linear(256, 1),
        )

    def forward(self, cond, bits):
        x = torch.cat([cond, bits], dim=1)
        return self.net(x)


def main():
    # ============================================================================
    # Argument Parsing
    # ============================================================================
    parser = argparse.ArgumentParser(description='Train GAN-based PUF Bit Predictor')
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
                        help='Featureless key ratio (0.0-1.0)')
    parser.add_argument('--decoy_key_ratio', type=float, default=-1.0,
                        help='Decoy ratio (0.0-1.0), -1 = natural mix')
    parser.add_argument('--num_training_size', type=int, default=150000,
                        help='Number of training samples (-1 for natural size)')
    parser.add_argument('--noise_dim', type=int, default=128,
                        help='Dimension of noise vector for generator')
    parser.add_argument('--num_epochs', type=int, default=200,
                        help='Number of training epochs')
    parser.add_argument('--lr_g', type=float, default=0.0002,
                        help='Learning rate for generator')
    parser.add_argument('--lr_d', type=float, default=0.0002,
                        help='Learning rate for discriminator')
    parser.add_argument('--lambda_bce', type=float, default=10.0,
                        help='Weight for supervised BCE loss on generator output')
    parser.add_argument('--n_critic', type=int, default=1,
                        help='Number of discriminator updates per generator update')
    args = parser.parse_args()

    set_seed(args.seed)

    # ============================================================================
    # Setup Logging
    # ============================================================================
    dataset_name = args.data_path.split('/')[-1].split('.')[0]
    args.model_name = dataset_name + "_" + args.model_name

    args.save_dir = os.path.join(args.save_dir, "gan")
    args.log_dir = os.path.join(args.log_dir, "gan")

    os.makedirs(args.save_dir, exist_ok=True)
    os.makedirs(args.log_dir, exist_ok=True)
    log_path = os.path.join(args.log_dir, f'{args.model_name}.txt')
    logger = Logger(log_path)
    sys.stdout = logger

    print(f"Logging to: {log_path}")

    # ============================================================================
    # Configuration
    # ============================================================================
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    try:
        print("=" * 70)
        print("PUF GAN-based Bit Prediction Training")
        print("=" * 70)
        print(f"Device: {device}")
        print(f"Data path: {args.data_path}")
        print(f"Filter inaccessible: {args.filter_inaccessible}")
        print(f"Filter duplicates: {args.filter_duplicates}")
        print(f"Featureless key ratio: {args.featureless_key_ratio}")
        print(f"Decoy key ratio: {args.decoy_key_ratio}")
        print(f"Num training size: {args.num_training_size}")
        print(f"Noise dim: {args.noise_dim}")
        print(f"Epochs: {args.num_epochs}")
        print(f"LR (G): {args.lr_g}, LR (D): {args.lr_d}")
        print(f"Lambda BCE: {args.lambda_bce}")
        print(f"n_critic: {args.n_critic}")
        print(f"Save directory: {args.save_dir}")
        print("=" * 70)

        # ============================================================================
        # Data Loading
        # ============================================================================
        print("\nLoading data...")
        train_loader = get_dataloader(
            data_path=args.data_path,
            split="train",
            batch_size=256,
            shuffle=True,
            num_workers=4,
            filter_inaccessible=args.filter_inaccessible,
            filter_duplicates=args.filter_duplicates,
            featureless_key_ratio=args.featureless_key_ratio,
            decoy_key_ratio=args.decoy_key_ratio,
            num_training_size=args.num_training_size,
            sampler_seed=args.seed,
        )

        print(f"Train batches: {len(train_loader)}")
        print(f"Total train samples: {len(train_loader.dataset)}")

        sample_inputs, sample_outputs = next(iter(train_loader))
        input_dim = sample_inputs.shape[1]
        output_dim = sample_outputs.shape[1]
        print(f"\nInput dim: {input_dim}, Output dim (bits): {output_dim}")

        # ============================================================================
        # Model Definition
        # ============================================================================
        gen = Generator(cond_dim=input_dim, noise_dim=args.noise_dim, output_dim=output_dim).to(device)
        disc = Discriminator(cond_dim=input_dim, bit_dim=output_dim).to(device)

        opt_g = optim.Adam(gen.parameters(), lr=args.lr_g, betas=(0.5, 0.999))
        opt_d = optim.Adam(disc.parameters(), lr=args.lr_d, betas=(0.5, 0.999))

        adv_criterion = nn.BCEWithLogitsLoss()
        sup_criterion = nn.BCEWithLogitsLoss()

        print(f"Generator params: {sum(p.numel() for p in gen.parameters()):,}")
        print(f"Discriminator params: {sum(p.numel() for p in disc.parameters()):,}")

        # ============================================================================
        # Training Loop
        # ============================================================================
        for epoch in range(args.num_epochs):
            gen.train()
            disc.train()
            epoch_d_loss = 0.0
            epoch_g_loss = 0.0
            epoch_g_adv = 0.0
            epoch_g_sup = 0.0
            num_batches = 0

            for batch_idx, (inputs, targets) in enumerate(train_loader):
                inputs = inputs.to(device)
                targets = targets.to(device)
                batch_size = inputs.size(0)

                real_labels = torch.ones(batch_size, 1, device=device)
                fake_labels = torch.zeros(batch_size, 1, device=device)

                # ----- Train Discriminator -----
                for _ in range(args.n_critic):
                    noise = torch.randn(batch_size, args.noise_dim, device=device)
                    fake_bits = gen(inputs, noise).detach()
                    fake_probs = torch.sigmoid(fake_bits)

                    d_real = disc(inputs, targets)
                    d_fake = disc(inputs, fake_probs)

                    loss_d_real = adv_criterion(d_real, real_labels)
                    loss_d_fake = adv_criterion(d_fake, fake_labels)
                    loss_d = (loss_d_real + loss_d_fake) / 2

                    opt_d.zero_grad()
                    loss_d.backward()
                    opt_d.step()

                # ----- Train Generator -----
                noise = torch.randn(batch_size, args.noise_dim, device=device)
                fake_bits_logits = gen(inputs, noise)
                fake_probs = torch.sigmoid(fake_bits_logits)

                d_fake = disc(inputs, fake_probs)
                loss_g_adv = adv_criterion(d_fake, real_labels)
                loss_g_sup = sup_criterion(fake_bits_logits, targets)
                loss_g = loss_g_adv + args.lambda_bce * loss_g_sup

                opt_g.zero_grad()
                loss_g.backward()
                opt_g.step()

                epoch_d_loss += loss_d.item()
                epoch_g_loss += loss_g.item()
                epoch_g_adv += loss_g_adv.item()
                epoch_g_sup += loss_g_sup.item()
                num_batches += 1

            avg_d = epoch_d_loss / num_batches
            avg_g = epoch_g_loss / num_batches
            avg_g_adv = epoch_g_adv / num_batches
            avg_g_sup = epoch_g_sup / num_batches
            print(f"Epoch [{epoch+1}/{args.num_epochs}]  D_loss: {avg_d:.4f}  "
                  f"G_loss: {avg_g:.4f} (adv: {avg_g_adv:.4f}, sup: {avg_g_sup:.4f})")

        # ============================================================================
        # Save Checkpoint (generator only — it's the predictor)
        # ============================================================================
        checkpoint_path = os.path.join(args.save_dir, f'{args.model_name}.pt')
        torch.save({
            'epoch': args.num_epochs,
            'generator_state_dict': gen.state_dict(),
            'discriminator_state_dict': disc.state_dict(),
            'optimizer_g_state_dict': opt_g.state_dict(),
            'optimizer_d_state_dict': opt_d.state_dict(),
            'noise_dim': args.noise_dim,
            'input_dim': input_dim,
            'output_dim': output_dim,
        }, checkpoint_path)
        print(f"Checkpoint saved: {checkpoint_path}")

        print("\nTraining complete. Run scripts/test_gan.py to evaluate this checkpoint.")

    finally:
        logger.close()
        sys.stdout = sys.__stdout__


if __name__ == "__main__":
    main()
