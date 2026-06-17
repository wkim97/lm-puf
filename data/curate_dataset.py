import os
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd
from PIL import Image

# Raw IR folders and the curated output live in this data/ directory.
_DATA_DIR = os.path.dirname(os.path.abspath(__file__))


def read_excel_file(file_path):
    """
    Read an Excel file with temperature window data.

    Args:
        file_path: Path to the Excel file

    Returns:
        win_min_temps: List of minimum temperatures for each window
        win_max_temps: List of maximum temperatures for each window
        is_accessibles: List of booleans indicating if the window is accessible
        output_bits: List of numpy arrays, each containing the bits for one window
    """
    # Read the Excel file
    df = pd.read_excel(file_path)

    # Get the directory containing the Excel file
    file_dir = os.path.dirname(file_path)

    win_min_temps = []
    win_max_temps = []
    is_accessibles = []
    output_bits = []

    # Process each column
    for col_name in df.columns:
        # Parse the column name: e.g., "R1_-1.0--0.8" or "R5_-0.2-0.0"
        # Format: Rn_win_min_temp-win_max_temp
        parts = col_name.split('_', 1)  # Split only on first underscore
        if len(parts) == 2:
            temp_range = parts[1]  # e.g., "-1.0--0.8" or "-0.2-0.0"

            # Case 1: If there is '--' in range, the second (max) number is negative
            if '--' in temp_range:
                temps = temp_range.split('--')
                win_min_temp = float(temps[0])
                win_max_temp = float('-' + temps[1])
            # Case 2: No '--' means both numbers are positive (or min is negative, max is positive)
            else:
                # Find the separator dash (not the leading dash for negative number)
                if temp_range[0] == '-':
                    # First number is negative, find the next dash
                    idx = temp_range.index('-', 1)
                else:
                    # First number is positive
                    idx = temp_range.index('-')

                win_min_temp = float(temp_range[:idx])
                win_max_temp = float(temp_range[idx+1:])

            win_min_temps.append(win_min_temp)
            win_max_temps.append(win_max_temp)

            # Check if {col_name}_bin.png exists and if all pixels are white
            png_path = os.path.join(file_dir, f"{col_name}_bin.png")
            is_accessible = True  # Default to True

            if os.path.exists(png_path):
                try:
                    img = Image.open(png_path)
                    img_array = np.array(img)

                    # Fast check using min/max instead of checking all pixels
                    if len(img_array.shape) == 2:  # Grayscale
                        min_val, max_val = img_array.min(), img_array.max()
                        all_white = (min_val == 255 and max_val == 255)
                        all_black = (min_val == 0 and max_val == 0)
                    else:  # RGB or RGBA
                        rgb_array = img_array[:, :, :3]
                        min_val, max_val = rgb_array.min(), rgb_array.max()
                        all_white = (min_val == 255 and max_val == 255)
                        all_black = (min_val == 0 and max_val == 0)

                    # If all pixels are white or black, set is_accessible to False
                    if all_white or all_black:
                        is_accessible = False
                except Exception as e:
                    print(f"Warning: Could not read {png_path}: {e}")

            is_accessibles.append(is_accessible)

            # Get the bits as a numpy array
            bits = df[col_name].to_numpy(dtype=int)
            output_bits.append(bits)

    return win_min_temps, win_max_temps, is_accessibles, output_bits


def check_is_time_limited(begin_temp, substrate_temp):
    """
    Check if begin_temp equals substrate_temp.

    Args:
        begin_temp: Beginning temperature
        substrate_temp: Substrate temperature

    Returns:
        True if begin_temp equals substrate_temp, False otherwise
    """
    return float(begin_temp) == float(substrate_temp)


def check_is_duplicate(end_temp):
    """
    Check if end_temp contains (1) or (2), indicating a duplicate.

    Args:
        end_temp: End temperature string

    Returns:
        True if end_temp contains (1) or (2), False otherwise
    """
    return '(1)' in end_temp or '(2)' in end_temp or '\(1\)' in end_temp or '\(2\)' in end_temp


def process_excel_file(file_path, begin_temp, end_temp, substrate_temp, test_begin_temp=None):
    """
    Process a single Excel file and return data entries.

    Args:
        file_path: Path to the Excel file
        begin_temp: Beginning temperature
        end_temp: End temperature
        substrate_temp: Substrate temperature
        test_begin_temp: Not used anymore (kept for compatibility)

    Returns:
        List of data dictionary entries for this file
    """
    # print(f"Processing Excel file: {file_path}")
    win_min_temps, win_max_temps, is_accessibles, output_bits = read_excel_file(file_path)

    entries = []
    eligible_for_split_indices = []

    for idx, (win_min_temp, win_max_temp, is_accessible, output_bit) in enumerate(zip(
        win_min_temps, win_max_temps, is_accessibles, output_bits
    )):
        is_duplicate = check_is_duplicate(end_temp)
        is_time_limited = check_is_time_limited(begin_temp, substrate_temp)

        if '\(1\)' in end_temp:
            end_temp = end_temp.replace('\(1\)', '')
        if '\(2\)' in end_temp:
            end_temp = end_temp.replace('\(2\)', '')

        is_decoy = float(begin_temp) < 16.5

        entry = {
            'begin_temp': begin_temp,
            'end_temp': end_temp,
            'substrate_temp': substrate_temp,
            'win_min_temp': win_min_temp,
            'win_max_temp': win_max_temp,
            'is_time_limited': is_time_limited,
            'is_accessible': is_accessible,
            'is_duplicate': is_duplicate,
            'is_decoy': is_decoy,
            'output_bit': output_bit,
            'split': 'train'  # Will be assigned for eligible entries
        }
        entries.append(entry)

        # Track indices eligible for train/test split
        if not is_decoy and is_accessible:
            eligible_for_split_indices.append(idx)

    return entries, eligible_for_split_indices


def read_and_store_data(data_dirs, output_dir, max_workers=None, test_begin_temp=None, random_seed=42, test_ratio=0.1):
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Accept either a single path or a list of paths
    if isinstance(data_dirs, str):
        data_dirs = [data_dirs]

    # Collect all Excel files to process
    file_tasks = []

    for data_dir in data_dirs:
        begin_end_temp = os.listdir(data_dir)

        # Iterate through each temperature range directory
        for cur_begin_end_temp in begin_end_temp:
            cur_path = os.path.join(data_dir, cur_begin_end_temp)
            if not os.path.isdir(cur_path) or " to " not in cur_begin_end_temp:
                continue
            begin_temp, end_temp = cur_begin_end_temp.split(" to ")
            substrates = os.listdir(cur_path)

            # Iterate through each substrate directory
            for substrate in substrates:
                substrate_dir = os.path.join(cur_path, substrate)
                if not os.path.isdir(substrate_dir):
                    continue
                substrate_temp = substrate.split("_")[-1]

                # Collect Excel files in the substrate directory
                for file_name in os.listdir(substrate_dir):
                    if file_name.endswith(".xlsx") or file_name.endswith(".xls"):
                        file_path = os.path.join(substrate_dir, file_name)
                        file_tasks.append((file_path, begin_temp, end_temp, substrate_temp))

    print(f"Found {len(file_tasks)} Excel files to process")

    # Process files in parallel
    data_dict = []
    all_eligible_indices = []  # List of (data_dict_idx,) tuples for eligible entries

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_file = {
            executor.submit(process_excel_file, file_path, begin_temp, end_temp, substrate_temp, test_begin_temp): file_path
            for file_path, begin_temp, end_temp, substrate_temp in file_tasks
        }

        # Collect results as they complete
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                entries, eligible_indices = future.result()
                base_idx = len(data_dict)
                data_dict.extend(entries)
                # Convert local indices to global indices
                for local_idx in eligible_indices:
                    all_eligible_indices.append(base_idx + local_idx)
            except Exception as e:
                print(f"Error processing {file_path}: {e}")

    # Add data_index to each entry
    for idx, entry in enumerate(data_dict):
        entry['data_index'] = idx

    # Randomly split eligible entries into train/test (90/10)
    if all_eligible_indices:
        print(f"Found {len(all_eligible_indices)} eligible entries (is_decoy=False, is_accessible=True)")

        # Set random seed for reproducibility
        np.random.seed(random_seed)

        # Shuffle indices
        shuffled_indices = np.array(all_eligible_indices)
        np.random.shuffle(shuffled_indices)

        # Split into test and train (10% test, 90% train)
        num_test = int(len(shuffled_indices) * test_ratio)
        test_indices = shuffled_indices[:num_test]

        # Assign splits
        for idx in test_indices:
            data_dict[idx]['split'] = 'test'

        print(f"Assigned {num_test} entries to test set ({test_ratio*100:.1f}%) and {len(shuffled_indices) - num_test} to train set ({(1-test_ratio)*100:.1f}%)")

    # Save the data dictionary as a numpy file
    output_path = os.path.join(output_dir, "data_dict.npy")
    np.save(output_path, data_dict)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Data Handler Configuration")
    parser.add_argument(
        "--data_dir",
        type=str,
        nargs="+",
        default=[
            os.path.join(_DATA_DIR, "251212ML_IR"),
            os.path.join(_DATA_DIR, "260408ML_IR"),
        ],
        help="Path(s) to the data directory (one or more)",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=_DATA_DIR,
        help="Path to the output directory",
    )
    parser.add_argument(
        "--max_workers",
        type=int,
        default=None,
        help="Maximum number of parallel workers (default: number of CPUs)",
    )
    parser.add_argument(
        "--random_seed",
        type=int,
        default=42,
        help="Random seed for train/test split (default: 42)",
    )
    parser.add_argument(
        "--test_ratio",
        type=float,
        default=0.1,
        help="Ratio of test data (default: 0.1 for 10%% test, 90%% train)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    print(f"Data directory: {args.data_dir}")
    print(f"Output directory: {args.output_dir}")
    print(f"Max workers: {args.max_workers if args.max_workers else 'auto'}")
    print(f"Random seed: {args.random_seed}")
    print(f"Test ratio: {args.test_ratio} ({args.test_ratio*100:.1f}% test, {(1-args.test_ratio)*100:.1f}% train)")
    read_and_store_data(args.data_dir, args.output_dir, args.max_workers, None, args.random_seed, args.test_ratio)