import os
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from typing import Dict, Tuple, Optional, List

# data_dict.npy lives alongside this file (the repo's data/ directory).
_DEFAULT_DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_dict.npy")


class PUFDataset(Dataset):
    """
    PyTorch Dataset for PUF (Physical Unclonable Function) data.

    Loads data from data_dict.npy and provides filtered access based on:
    - split (train/test/val)
    - is_accessible flag

    Returns:
        inputs: Tensor of [begin_temp, end_temp, substrate_temp, win_min_temp, win_max_temp]
        outputs: Tensor of output_bit array
    """

    def __init__(
        self,
        data_path: str = _DEFAULT_DATA_PATH,
        split: str = "train",
        filter_inaccessible: bool = True,
        filter_duplicates: bool = False,
        featureless_key_ratio: float = 0.0,
        decoy_key_ratio: float = -1.0,
        num_training_size: int = -1,
        sampler_seed: int = 42
    ):
        """
        Initialize the PUF dataset.

        Args:
            data_path: Path to the data_dict.npy file
            split: Data split to use ('train', 'test', or 'val')
            filter_inaccessible: If True, filter out instances with is_accessible=False
            filter_duplicates: If True, filter out instances with is_duplicate=True
            featureless_key_ratio: Ratio in [0.0, 1.0] defining the proportion of
                featureless (is_time_limited=True) data in the final training set:
                f = n_featureless / (n_authentic + n_decoy + n_featureless).
                0.0 = no featureless, 1.0 = use all available featureless data.
            decoy_key_ratio: Ratio in [0.0, 1.0] defining the proportion of decoy
                data in (authentic + decoy): d = n_decoy / (n_authentic + n_decoy).
                0.0 = no decoys, 1.0 = use all available decoys.
                -1 (default) is treated as 1.0 for backwards compatibility.
            num_training_size: Target dataset size. If > 0 and greater than current size, duplicates instances.
                               If -1, uses the natural dataset size.
        """
        self.data_path = data_path
        self.split = split
        self.filter_inaccessible = filter_inaccessible
        self.filter_duplicates = filter_duplicates
        self.featureless_key_ratio = featureless_key_ratio
        self.decoy_key_ratio = decoy_key_ratio
        self.num_training_size = num_training_size
        self.sampler_seed = sampler_seed

        # Load the data
        self.raw_data = np.load(data_path, allow_pickle=True)

        # Filter data based on split and accessibility
        self.filtered_indices = self._filter_data()

        # Apply num_training_size duplication if needed (only for training split)
        if self.split == "train" and self.num_training_size > 0:
            original_size = len(self.filtered_indices)
            if self.num_training_size > original_size:
                # Calculate how many times to repeat
                num_repeats = (self.num_training_size // original_size) + 1
                # Duplicate and trim to exact size
                self.filtered_indices = (self.filtered_indices * num_repeats)[:self.num_training_size]
                print(f"Duplicated training data from {original_size} to {len(self.filtered_indices)} samples")
            else:
                print(f"num_training_size ({self.num_training_size}) <= current size ({original_size}), no duplication needed")

        print(f"Loaded {len(self.filtered_indices)} samples for {split} split "
              f"(featureless_key_ratio={featureless_key_ratio}, decoy_key_ratio={decoy_key_ratio})")

    def _filter_data(self) -> List[int]:
        """
        Filter data based on split / accessibility / duplicates, then mix pools
        using featureless_key_ratio and decoy_key_ratio.

        Two alternative mixing strategies are implemented. Option 1 is kept as
        commented reference; Option 2 is active.

        Option 2 (ratio-based): Base set is all non-decoy, non-featureless
        keys (authentic). Ratios define final proportions:
          decoy_ratio = n_decoy / (n_authentic + n_decoy)
          featureless_ratio = n_featureless / (n_authentic + n_decoy + n_featureless)
        Samples with replacement when the computed count exceeds the pool.
        decoy_key_ratio=-1 is treated as 1.0 (use all decoys) for
        backwards compatibility with test-loader defaults.

        Returns:
            List of valid indices
        """
        # First pass: categorize
        featureless_indices = []
        decoy_indices = []
        non_decoy_indices = []

        for idx in range(len(self.raw_data)):
            data_item = self.raw_data[idx]

            if data_item['split'] != self.split:
                continue

            if self.filter_inaccessible and not data_item['is_accessible']:
                continue

            if self.filter_duplicates and data_item['is_duplicate']:
                continue

            if data_item.get('is_time_limited', False):
                featureless_indices.append(idx)
            elif data_item.get('is_decoy', False):
                decoy_indices.append(idx)
            else:
                non_decoy_indices.append(idx)

        # ------------------------------------------------------------------
        # Option 1 (disabled): temperature-threshold featureless mixing that
        # preserves dataset size, plus pool-rebalancing for decoy_key_ratio.
        # ------------------------------------------------------------------
        # time_limited_true_indices = featureless_indices
        # time_limited_false_indices = decoy_indices + non_decoy_indices
        # max_dataset_size = len(time_limited_false_indices)
        # if max_dataset_size == 0:
        #     return []
        # f = self.featureless_key_ratio
        # valid_ratio = 1.0 - f
        # if f == 0.0:
        #     valid_indices = list(time_limited_false_indices)
        # else:
        #     filtered_false_indices = []
        #     for idx in time_limited_false_indices:
        #         data_item = self.raw_data[idx]
        #         begin_temp = float(data_item['begin_temp'])
        #         end_temp = float(data_item['end_temp'].split(' ')[0])
        #         substrate_temp = float(data_item['substrate_temp'])
        #         temp_threshold = begin_temp + valid_ratio * (end_temp - begin_temp)
        #         if substrate_temp <= temp_threshold:
        #             filtered_false_indices.append(idx)
        #     num_needed_from_true = max_dataset_size - len(filtered_false_indices)
        #     if num_needed_from_true > 0 and len(time_limited_true_indices) > 0:
        #         num_repeats = (num_needed_from_true // len(time_limited_true_indices)) + 1
        #         repeated_true_indices = (time_limited_true_indices * num_repeats)[:num_needed_from_true]
        #         valid_indices = filtered_false_indices + repeated_true_indices
        #     else:
        #         valid_indices = filtered_false_indices
        # if self.decoy_key_ratio != -1.0:
        #     d = self.decoy_key_ratio
        #     if not 0.0 <= d <= 1.0:
        #         raise ValueError(f"decoy_key_ratio must be in [0.0, 1.0] or -1, got {d}")
        #     decoy_pool = [i for i in valid_indices if self.raw_data[i]['is_decoy']]
        #     non_decoy_pool = [i for i in valid_indices if not self.raw_data[i]['is_decoy']]
        #     n_decoy = int(round(d * len(decoy_pool)))
        #     n_non_decoy = int(round((1.0 - d) * len(non_decoy_pool)))
        #     rng = np.random.default_rng(42)
        #     def _sample(pool, n, label):
        #         if n <= 0:
        #             return []
        #         return rng.choice(pool, size=n, replace=False).tolist()
        #     valid_indices = _sample(decoy_pool, n_decoy, "decoy") \
        #                   + _sample(non_decoy_pool, n_non_decoy, "non_decoy")
        # return valid_indices

        # ------------------------------------------------------------------
        # Option 2 (disabled): ratio-based sampling.
        #   decoy_ratio     = n_decoy / (n_authentic + n_decoy)
        #   featureless_ratio = n_featureless / (n_authentic + n_decoy + n_featureless)
        # ------------------------------------------------------------------
        # d = 1.0 if self.decoy_key_ratio == -1.0 else self.decoy_key_ratio
        # if not 0.0 <= d <= 1.0:
        #     raise ValueError(f"decoy_key_ratio must be in [0.0, 1.0] or -1, got {self.decoy_key_ratio}")
        # f = self.featureless_key_ratio
        # if not 0.0 <= f <= 1.0:
        #     raise ValueError(f"featureless_key_ratio must be in [0.0, 1.0], got {f}")
        #
        # n_authentic = len(non_decoy_indices)
        # rng = np.random.default_rng(42)
        #
        # # n_decoy from: d = n_decoy / (n_authentic + n_decoy)
        # if d == 0.0:
        #     n_decoy = 0
        # elif d == 1.0:
        #     n_decoy = len(decoy_indices)  # use all decoys when ratio is 1.0
        # else:
        #     n_decoy = int(round(n_authentic * d / (1.0 - d)))
        #
        # # n_featureless from: f = n_featureless / (n_authentic + n_decoy + n_featureless)
        # if f == 0.0:
        #     n_featureless = 0
        # elif f == 1.0:
        #     n_featureless = len(featureless_indices)  # use all featureless when ratio is 1.0
        # else:
        #     n_featureless = int(round((n_authentic + n_decoy) * f / (1.0 - f)))
        #
        # # Sample with replacement if requested count exceeds pool size
        # sampled_decoy = (
        #     rng.choice(decoy_indices, size=n_decoy,
        #                replace=(n_decoy > len(decoy_indices))).tolist()
        #     if n_decoy > 0 and len(decoy_indices) > 0 else []
        # )
        # sampled_featureless = (
        #     rng.choice(featureless_indices, size=n_featureless,
        #                replace=(n_featureless > len(featureless_indices))).tolist()
        #     if n_featureless > 0 and len(featureless_indices) > 0 else []
        # )
        #
        # print(f"  [option2] authentic={n_authentic}, "
        #       f"decoy_pool={len(decoy_indices)} → {n_decoy} (ratio={d}), "
        #       f"featureless_pool={len(featureless_indices)} → {n_featureless} (ratio={f})")
        #
        # return list(non_decoy_indices) + sampled_decoy + sampled_featureless

        # ------------------------------------------------------------------
        # Option 3 (active):
        #   decoy_key_ratio: always use ALL non-decoy keys, then add
        #       decoy_key_ratio * n_decoy_pool randomly sampled decoy keys.
        #   featureless_key_ratio: reference size = n_non_decoy_pool + n_decoy_pool.
        #       n_featureless = reference_size * f  (duplicated/sampled with replacement)
        #       n_non_featureless = reference_size * (1 - f)  (randomly sampled from
        #           the non-decoy + sampled-decoy combined pool)
        # ------------------------------------------------------------------
        d = 1.0 if self.decoy_key_ratio == -1.0 else self.decoy_key_ratio
        if not 0.0 <= d <= 1.0:
            raise ValueError(f"decoy_key_ratio must be in [0.0, 1.0] or -1, got {self.decoy_key_ratio}")
        f = self.featureless_key_ratio
        if not 0.0 <= f <= 1.0:
            raise ValueError(f"featureless_key_ratio must be in [0.0, 1.0], got {f}")

        rng = np.random.default_rng(self.sampler_seed)

        # Step 1: Decoy sampling — all non-decoy + d * n_decoy_pool random decoys
        n_decoy_sample = int(round(d * len(decoy_indices)))
        sampled_decoy = (
            rng.choice(decoy_indices, size=n_decoy_sample, replace=False).tolist()
            if n_decoy_sample > 0 and len(decoy_indices) > 0 else []
        )
        combined_non_featureless = list(non_decoy_indices) + sampled_decoy

        # Step 2: Featureless mixing — temperature-threshold filtering
        # (preserves dataset size of combined_non_featureless)
        max_dataset_size = len(combined_non_featureless)

        if f == 0.0:
            print(f"  [option3] non_decoy={len(non_decoy_indices)}, "
                  f"decoy_pool={len(decoy_indices)} → {n_decoy_sample} (ratio={d}), "
                  f"featureless=0 (ratio={f}), total={max_dataset_size}")
            return combined_non_featureless

        valid_ratio = 1.0 - f
        filtered_non_featureless = []
        for idx in combined_non_featureless:
            data_item = self.raw_data[idx]
            begin_temp = float(data_item['begin_temp'])
            end_temp = float(data_item['end_temp'].split(' ')[0])
            substrate_temp = float(data_item['substrate_temp'])
            temp_threshold = begin_temp + valid_ratio * (end_temp - begin_temp)
            if substrate_temp <= temp_threshold:
                filtered_non_featureless.append(idx)

        # Fill the gap with featureless data (duplicated if needed)
        num_needed_from_featureless = max_dataset_size - len(filtered_non_featureless)
        if num_needed_from_featureless > 0 and len(featureless_indices) > 0:
            num_repeats = (num_needed_from_featureless // len(featureless_indices)) + 1
            sampled_featureless = (featureless_indices * num_repeats)[:num_needed_from_featureless]
        else:
            sampled_featureless = []

        print(f"  [option3] non_decoy={len(non_decoy_indices)}, "
              f"decoy_pool={len(decoy_indices)} → {n_decoy_sample} (ratio={d}), "
              f"featureless_pool={len(featureless_indices)} → {len(sampled_featureless)} (ratio={f}), "
              f"filtered_non_featureless={len(filtered_non_featureless)}, "
              f"total={len(filtered_non_featureless) + len(sampled_featureless)}")

        return filtered_non_featureless + sampled_featureless

    def __len__(self) -> int:
        """Return the number of samples in the dataset."""
        return len(self.filtered_indices)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Get a single data sample.

        Args:
            idx: Index of the sample

        Returns:
            Tuple of (inputs, output_bits)
            - inputs: Tensor of shape [5] containing temperature features
            - output_bits: Tensor of output_bit array
        """
        # Get the actual data index
        data_idx = self.filtered_indices[idx]
        data_item = self.raw_data[data_idx]

        # Extract input features as floats
        inputs = torch.tensor([
            float(data_item['begin_temp']) / 35.0,
            float(data_item['end_temp'].split(' ')[0]) / 35.0,
            float(data_item['substrate_temp']) / 35.0,
            float(data_item['win_min_temp']) / 35.0,
            float(data_item['win_max_temp']) / 35.0
        ], dtype=torch.float32)

        # if data_item['is_time_limited']:
        #     print("Warning: Accessing is_time_limited=True data in the dataset.")

        # Extract output bits
        output_bits = torch.tensor(data_item['output_bit'], dtype=torch.float32)

        return inputs, output_bits


def get_dataloader(
    data_path: str = _DEFAULT_DATA_PATH,
    split: str = "train",
    batch_size: int = 32,
    shuffle: bool = True,
    num_workers: int = 0,
    filter_inaccessible: bool = True,
    filter_duplicates: bool = False,
    featureless_key_ratio: float = 0.0,
    decoy_key_ratio: float = -1.0,
    num_training_size: int = -1,
    sampler_seed: int = 42,
    **kwargs
) -> DataLoader:
    """
    Create a PyTorch DataLoader for PUF data.

    Args:
        data_path: Path to the data_dict.npy file
        split: Data split to use ('train', 'test', or 'val')
        batch_size: Number of samples per batch
        shuffle: Whether to shuffle the data
        num_workers: Number of worker processes for data loading
        filter_inaccessible: If True, filter out instances with is_accessible=False
        filter_duplicates: If True, filter out instances with is_duplicate=True
        featureless_key_ratio: Ratio in [0.0, 1.0] of featureless (is_time_limited=True) data.
        decoy_key_ratio: If set in [0.0, 1.0], target decoy ratio within (decoy + non-decoy) total.
        num_training_size: Target dataset size. If > 0 and greater than current size, duplicates instances.
                           If -1, uses the natural dataset size.
        **kwargs: Additional arguments to pass to DataLoader

    Returns:
        DataLoader instance
    """
    dataset = PUFDataset(
        data_path=data_path,
        split=split,
        filter_inaccessible=filter_inaccessible,
        filter_duplicates=filter_duplicates,
        featureless_key_ratio=featureless_key_ratio,
        decoy_key_ratio=decoy_key_ratio,
        num_training_size=num_training_size,
        sampler_seed=sampler_seed
    )

    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        **kwargs
    )

    return dataloader


def get_train_test_loaders(
    data_path: str = _DEFAULT_DATA_PATH,
    batch_size: int = 32,
    train_shuffle: bool = True,
    test_shuffle: bool = False,
    num_workers: int = 0,
    filter_inaccessible: bool = True,
    filter_duplicates: bool = False,
    featureless_key_ratio: float = 0.0,
    decoy_key_ratio: float = -1.0,
    num_training_size: int = -1,
    sampler_seed: int = 42,
    **kwargs
) -> Tuple[DataLoader, DataLoader]:
    """
    Create train and test DataLoaders.

    Args:
        data_path: Path to the data_dict.npy file
        batch_size: Number of samples per batch
        train_shuffle: Whether to shuffle training data
        test_shuffle: Whether to shuffle test data
        num_workers: Number of worker processes for data loading
        filter_inaccessible: If True, filter out instances with is_accessible=False
        filter_duplicates: If True, filter out instances with is_duplicate=True
        featureless_key_ratio: Ratio in [0.0, 1.0] of featureless (is_time_limited=True) data.
        decoy_key_ratio: If set in [0.0, 1.0], target decoy ratio within (decoy + non-decoy) total.
        num_training_size: Target dataset size for training data. If > 0 and greater than current size,
                           duplicates instances. If -1, uses the natural dataset size.
        **kwargs: Additional arguments to pass to DataLoader

    Returns:
        Tuple of (train_loader, test_loader)
    """
    train_loader = get_dataloader(
        data_path=data_path,
        split="train",
        batch_size=batch_size,
        shuffle=train_shuffle,
        num_workers=num_workers,
        filter_inaccessible=filter_inaccessible,
        filter_duplicates=filter_duplicates,
        featureless_key_ratio=featureless_key_ratio,
        decoy_key_ratio=decoy_key_ratio,
        num_training_size=num_training_size,
        sampler_seed=sampler_seed,
        **kwargs
    )

    test_loader = get_dataloader(
        data_path=data_path,
        split="test",
        batch_size=batch_size,
        shuffle=test_shuffle,
        num_workers=num_workers,
        filter_inaccessible=False,
        filter_duplicates=False,
        featureless_key_ratio=0.0,
        decoy_key_ratio=-1.0,
        **kwargs
    )

    return train_loader, test_loader


# Example usage
if __name__ == "__main__":
    # Example 1: Create a single dataloader
    train_loader = get_dataloader(
        split="train",
        batch_size=64,
        shuffle=True,
        filter_inaccessible=True
    )

    # Iterate through a few batches
    print("\n=== Example 1: Single DataLoader ===")
    for batch_idx, (inputs, outputs) in enumerate(train_loader):
        print(f"Batch {batch_idx}:")
        print(f"  Inputs shape: {inputs.shape}")  # [batch_size, 5]
        print(f"  Outputs shape: {outputs.shape}")  # [batch_size, output_bit_length]
        print(f"  Input sample: {inputs[0]}")
        if batch_idx >= 2:
            break

    # Example 2: Create train and test loaders
    print("\n=== Example 2: Train and Test DataLoaders ===")
    train_loader, test_loader = get_train_test_loaders(
        batch_size=32,
        train_shuffle=True,
        test_shuffle=False,
        filter_inaccessible=True
    )

    print(f"Train batches: {len(train_loader)}")
    print(f"Test batches: {len(test_loader)}")

    # Example 3: Access dataset directly
    print("\n=== Example 3: Direct Dataset Access ===")
    dataset = PUFDataset(split="train", filter_inaccessible=True)
    print(f"Total samples: {len(dataset)}")
    inputs, outputs = dataset[0]
    print(f"First sample inputs: {inputs}")
    print(f"First sample output shape: {outputs.shape}")
