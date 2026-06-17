"""
Build featureless substrate folders for each '{begin} to {end}' directory.

Rule (per-begin_end):
  - Within a single begin_end dir, scan all (substrate, window, R-column) combos.
    Any column whose '{col}_bin.png' is entirely white (all pixels == 255) is a
    featureless reading FOR THAT begin_end.
  - All such readings inside the same begin_end must be identical -> that
    begin_end's 1024-bit featureless pattern.
  - Create target substrate folder `{prefix}_{begin}.0/` and write 3 xlsx files
    (w in {0.1, 0.2, 0.3}). Each xlsx has one column
    `R1_{begin}-{begin+w}` containing that begin_end's pattern.

To keep runtime bounded, at most PER_BE_LIMIT bin.png files are inspected per
begin_end (not per substrate).
"""

import os
import re
import sys
from typing import List, Tuple

import numpy as np
import pandas as pd
from PIL import Image


WINDOWS = [0.1, 0.2, 0.3]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_ROOTS = [
    os.path.join(SCRIPT_DIR, "251212ML_IR"),
    os.path.join(SCRIPT_DIR, "260408ML_IR"),
]


def fmt(x: float) -> str:
    return f"{x:.1f}"


def format_range(lo: float, hi: float) -> str:
    return f"{fmt(lo)}-{fmt(hi)}"


def range_from_col(col: str) -> str:
    return col.split("_", 1)[1]


def _split_range(rng: str) -> Tuple[str, str]:
    if "--" in rng:
        lo, hi = rng.split("--", 1)
        return lo, "-" + hi
    idx = rng.index("-", 1) if rng.startswith("-") else rng.index("-")
    return rng[:idx], rng[idx + 1:]


def is_all_white(path: str) -> bool:
    img = np.array(Image.open(path).convert("L"))
    return bool((img == 255).all())


def parse_substrate_folder(name: str) -> Tuple[str, float]:
    m = re.match(r"^(.+)_(-?\d+(?:\.\d+)?)$", name)
    if not m:
        return None, None
    return m.group(1), float(m.group(2))


def parse_begin_temp(begin_end_dir_name: str) -> float:
    return float(begin_end_dir_name.split(" to ")[0])


def find_xlsx_for_window(folder: str, w: float) -> str:
    suffix = f"_{w}.xlsx"
    for name in os.listdir(folder):
        if name.endswith(suffix):
            return os.path.join(folder, name)
    return None


def iter_begin_end_dirs():
    for root in DATA_ROOTS:
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            full = os.path.join(root, name)
            if os.path.isdir(full):
                yield root, name, full


def iter_substrate_entries(begin_end_dir: str):
    for name in sorted(os.listdir(begin_end_dir)):
        full = os.path.join(begin_end_dir, name)
        if not os.path.isdir(full):
            continue
        prefix, sub_t = parse_substrate_folder(name)
        if prefix is None:
            continue
        yield full, name, prefix, sub_t


PER_BE_LIMIT = 10


def collect_featureless_pattern_for_be(root: str, dir_name: str, be_full: str):
    """Return 1024-bit pattern for one begin_end dir, or None if no all-white found."""
    begin_temp = parse_begin_temp(dir_name)
    matches: List[Tuple[str, np.ndarray]] = []
    white_found = 0

    for sub_full, sub_name, _, sub_t in iter_substrate_entries(be_full):
        if sub_t == begin_temp:
            continue
        if white_found >= PER_BE_LIMIT:
            break
        print(f"[scan] {os.path.basename(root)}/{dir_name}/{sub_name}", flush=True)
        white_cols = []
        for fn in sorted(os.listdir(sub_full)):
            if not fn.endswith("_bin.png"):
                continue
            if white_found >= PER_BE_LIMIT:
                break
            bin_path = os.path.join(sub_full, fn)
            if not is_all_white(bin_path):
                continue
            print(f"  [img] {fn}", flush=True)
            white_cols.append(fn[:-len("_bin.png")])
            white_found += 1
            print(f"    -> all-white ({white_found}/{PER_BE_LIMIT})", flush=True)
        if not white_cols:
            continue

        cols_by_w = {w: [] for w in WINDOWS}
        for col in white_cols:
            rng = range_from_col(col)
            lo_s, hi_s = _split_range(rng)
            w = round(float(hi_s) - float(lo_s), 1)
            if w in cols_by_w:
                cols_by_w[w].append(col)

        for w, cols in cols_by_w.items():
            if not cols:
                continue
            xlsx_path = find_xlsx_for_window(sub_full, w)
            if xlsx_path is None:
                continue
            print(f"  [xlsx] {os.path.basename(xlsx_path)} cols={cols}", flush=True)
            df = pd.read_excel(xlsx_path)
            for col in cols:
                if col not in df.columns:
                    continue
                bits = df[col].to_numpy(dtype=np.int64)
                tag = f"{sub_name}/w{w}/{col}"
                matches.append((tag, bits))

    if not matches:
        return None

    ref_tag, ref_bits = matches[0]
    mismatches = [(tag, int((b != ref_bits).sum())) for tag, b in matches[1:]
                  if not np.array_equal(b, ref_bits)]
    print(f"  {dir_name}: {len(matches)} featureless readings, ref={ref_tag}")
    if mismatches:
        print(f"  [error] {len(mismatches)} readings differ. Examples:")
        for tag, d in mismatches[:10]:
            print(f"    diff {d}/{len(ref_bits)} bits: {tag}")
        raise ValueError(f"Featureless bits differ within {dir_name}")
    return ref_bits


def write_featureless_for_begin_end(be_full: str, pattern: np.ndarray) -> None:
    dir_name = os.path.basename(be_full.rstrip("/"))
    begin_temp = parse_begin_temp(dir_name)

    subs = list(iter_substrate_entries(be_full))
    if not subs:
        return
    sources = [s for s in subs if s[3] != begin_temp]
    existing_target = [s for s in subs if s[3] == begin_temp]

    if existing_target:
        target_full, _, target_prefix, _ = existing_target[0]
    else:
        target_prefix = sources[0][2]
        target_name = f"{target_prefix}_{fmt(begin_temp)}"
        target_full = os.path.join(be_full, target_name)
        os.makedirs(target_full, exist_ok=True)

    last_end = round(begin_temp + 0.9, 1)
    for w in WINDOWS:
        target_hi = round(begin_temp + w, 1)
        target_col = f"R1_{format_range(begin_temp, target_hi)}"
        fname = f"{target_prefix}_{fmt(begin_temp)}_{fmt(begin_temp)}_{fmt(last_end)}_{w}.xlsx"
        out_path = os.path.join(target_full, fname)
        pd.DataFrame({target_col: pattern}).to_excel(out_path, index=False)
        print(f"[ok] {out_path}")


def main():
    for root, dir_name, be_full in iter_begin_end_dirs():
        try:
            pattern = collect_featureless_pattern_for_be(root, dir_name, be_full)
            if pattern is None:
                print(f"[skip] {dir_name}: no all-white bin.png found")
                continue
            write_featureless_for_begin_end(be_full, pattern)
        except Exception as e:
            print(f"[error] {be_full}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
