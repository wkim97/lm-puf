# lm-puf-extractor-analyzer

LM-PUF response **extractor** (Steps 1–3) and **analyzer** (Step 4). This repository turns raw **FLIR
radiometric IR videos (`.seq`)** of a liquid-metal PUF sample into **1024-bit responses**, one per
temperature window, and evaluates them with the standard PUF figures of merit.

Each sample video is processed in three GUI steps, and a fourth tool evaluates the resulting
responses with the standard PUF figures of merit. Steps 2–4 are provided both as **Python** and as
**MATLAB** programs (same windows, file formats and outputs — see *MATLAB version* below); Step 1
is Python only because it depends on the FLIR SDK.

| Step | Python | MATLAB | Input → Output | What it does |
|------|--------|--------|----------------|--------------|
| 1 | `python/Count2Temp.py` | — | `*.seq` → `*.mat` | Decodes every frame of a FLIR `.seq` file into a Celsius temperature stack (`temperature_frames`, `N×H×W`, float32) |
| 2 | `python/samplematcher.py` | `matlab/samplematcher.m` | `*.mat` → `*_new.mat` | Perspective-corrects the whole stack onto a fixed rectangular grid using 4 sample corners (manual or auto-snapped) |
| 3 | `python/execute.py` | `matlab/execute.m` | `*_new.mat` → `*.xlsx`, `*.png` | Finds the trigger frame, sweeps temperature windows over the ROI, and converts each window into a 32 × 32 (1024-bit) response via adaptive threshold → 2-D DCT → sign quantization → XOR with a fixed seed |
| 4 | `python/hd_analyzer_min.py` | `matlab/hd_analyzer_min.m` | `*.xlsx` (N samples × R reps) → `PUF_Analysis.{png,xlsx}` | Intra/inter Hamming distance, uniformity, uniqueness, reliability, P_clone / FAR / FRR, Shannon **and min-entropy** (NIST SP 800-90B), bootstrap convergence |

## Layout

```
lm-puf-extractor-analyzer/
├── python/
│   ├── Count2Temp.py        # Step 1: FLIR .seq  → .mat     (temperature_frames)
│   ├── samplematcher.py     # Step 2: .mat       → _new.mat (perspective-corrected 'images')
│   ├── execute.py           # Step 3: _new.mat   → R*_bin.png / R*_bits.png / *.xlsx (1024-bit responses)
│   └── hd_analyzer_min.py   # Step 4: *.xlsx     → PUF_Analysis.png / PUF_Analysis.xlsx (HD & entropy metrics)
├── matlab/
│   ├── samplematcher.m      # Step 2 (MATLAB R2016a+)
│   ├── execute.m            # Step 3 (MATLAB R2016a+)
│   ├── hd_analyzer_min.m    # Step 4 (MATLAB R2016a+)
│   └── lib/                 # shared functions (puf_*.m): binarisation, DCT response, warping,
│                            #   corner refinement, metrics, dashboard, .xlsx / .mat I/O
├── environment.yml          # conda environment (name: puf-data)
├── requirements.txt         # same pins for plain pip
└── README.md
```

---

## 1. System requirements

**Operating system**
- Windows 10/11 (developed and tested on Windows 11). Steps 2–4 are pure Python
  (NumPy / SciPy / pandas / OpenCV / Tkinter) and run anywhere those are available; **Step 1
  requires the FLIR Science File SDK, which is distributed for Windows and Linux only.**

**Software dependencies** (pinned in `environment.yml` / `requirements.txt`; key versions)
- Python 3.13.12
- NumPy 2.3.0, SciPy 1.15.3, pandas 3.0.2, matplotlib 3.10.8
- opencv-python 4.11.0.86 (Steps 2–3)
- openpyxl 3.1.5 (`.xlsx` I/O in Steps 3–4)
- Tk 8.6 (bundled with the python.org / conda Python builds)
- **FLIR Science File SDK (`FileSDK` 2024.7.1, imported as `fnv`)** — only needed by
  `Count2Temp.py`. It is **not on PyPI**; see the installation guide below.

**MATLAB version** (`matlab/`)
- MATLAB **R2016a** or newer (written against R2016a: no implicit expansion, no `string` type,
  classic `figure` / `uicontrol` GUIs).
- **Image Processing Toolbox** (`fitgeotrans`, `imwarp`, `dct2`, `fspecial`, `imfilter`,
  `graythresh`, `bwconncomp`, `bwboundaries`).
- **Statistics and Machine Learning Toolbox** (`normpdf`, `normcdf`, `norminv`).
- Microsoft Excel is *optional*: `.xlsx` files are written with `writetable`. When Excel is
  installed, `writetable` goes through Excel and the tools remove Excel's default empty sheets
  afterwards, so the first sheet is always the data sheet.

**Tested on**
- Windows 11 Pro, Python 3.13.12, FLIR Science File SDK 2024.7.1.
- Windows 11 Pro, MATLAB R2016a (9.0), Image Processing Toolbox 9.4, Statistics and Machine
  Learning Toolbox 10.2.

**Hardware**
- No GPU is used. Any desktop/laptop is sufficient; RAM is the only constraint, since a whole
  `.seq` recording is held in memory as float32 (`frames × height × width × 4 bytes`).
- Raw data were recorded with a FLIR radiometric camera saved in the `.seq` container.

---

## 2. Installation guide

```bash
# 1. Enter the repository folder
cd lm-puf-extractor-analyzer

# 2. Create the conda environment (Python, NumPy, SciPy, pandas, matplotlib, OpenCV, openpyxl, Tk)
conda env create -f environment.yml

# 3. Activate it
conda activate puf-data
```

Or with plain pip on an existing Python 3.13 install:

```bash
pip install -r requirements.txt
```

**FLIR Science File SDK (Step 1 only).** Download the *Science File SDK* from the FLIR/Teledyne
support site (free account required), run the installer, then install the bundled Python wheel
into the same environment, e.g.

```bash
# Windows default install location; adjust the path/version to your installer
pip install "C:/Program Files/FLIR Systems/sdks/file/python/FileSDK-2024.7.1-cp313-cp313-win_amd64.whl"
python -c "import fnv.file; print('FLIR FileSDK OK')"
```

If you already have `.mat` temperature stacks (e.g. exported elsewhere), Step 1 and the SDK can
be skipped entirely.

**MATLAB version.** Nothing to install beyond MATLAB and the two toolboxes; add the folder to the
path once per session (each tool adds its own `lib/` folder automatically):

```matlab
addpath('path/to/lm-puf-extractor-analyzer/matlab')
samplematcher      % Step 2
execute            % Step 3
hd_analyzer_min    % Step 4
```

**Typical install time:** 1–3 minutes for the conda/pip environment; the FLIR SDK installer adds
a few more minutes. The MATLAB version needs no installation.

---

## 3. Instructions for use

All four tools are GUI applications; launch them with `python python/<name>.py` (or, for
Steps 2–4, type the tool name at the MATLAB prompt — windows, buttons and parameters are the
same). Outputs of Steps 1–3 are always written **next to the input file**, so keep one sample per
folder.

### Step 1 — `Count2Temp.py`: FLIR `.seq` → `.mat`

```bash
python python/Count2Temp.py
```

1. **Add SEQ Files** — select one or more `.seq` recordings.
2. **Start Conversion** — every frame is read through the SDK with the unit forced to
   temperature (°C) and stacked into a `(num_frames, height, width)` float32 array.
3. Output: `<name>.mat` with key `temperature_frames`, saved beside each `.seq`.

Runs in a background thread with a progress bar; files are processed sequentially and memory is
released between files.

### Step 2 — `samplematcher.py`: perspective correction → `_new.mat`

```bash
python python/samplematcher.py
```

1. **Load MAT File** — select the `<name>.mat` from Step 1 (or several files; they form a queue).
2. **Select Frame (← / →)** — scrub to a frame where the sample outline is clearly visible.
3. **Corner Detection** — click **Set Points (Manual)** and click the 4 sample corners, or
   **Calculate Position (Auto)** to snap the points to the sample edge (Otsu threshold →
   largest contour → `cornerSubPix` refinement). Points can be dragged for fine adjustment.
4. **Target Scale** — output grid size (default `760 × 390`).
5. **Run and Save** — a homography is fitted to the 4 points and applied to *every* frame
   (`cv2.warpPerspective`, bilinear).
   Outputs beside the input:
   - `<name>_xy.mat` — the 4 corner points and target size (reusable),
   - `<name>_new.mat` — the corrected stack under key `images`.

   For many files: save points per file with **Save Points Only**, then **Batch Process Saved
   Points** to warp all of them at once. Files that share a stem (e.g. `A_1.mat`, `A_2.mat`)
   are grouped and reuse the same points.

### Step 3 — `execute.py`: temperature windows → 1024-bit responses

```bash
python python/execute.py
```

1. **Load New File** — select a `*_new.mat` (only `_new.mat` files are accepted).
2. **Select 3 points** (popup) — click three probe pixels on the sample; their mean temperature
   over time is the *temperature history* used for triggering. Saved as `<group>_points.mat`.
3. **Select ROI** (popup) — drag the rectangle that contains the liquid-metal pattern. Saved as
   `<group>_roi.mat` (or reused from `common_roi.mat` if one exists in the folder).
4. **Parameters**

   | Parameter | Default | Meaning |
   |-----------|:-------:|---------|
   | Trigger Temp | 50.0 | The *trigger frame* is the first frame after the coldest frame whose probe temperature ≥ this value. The ROI is taken from that frame (optionally averaged over 1–5 neighbouring frames). |
   | Start / End / Step | 40.0 / 49.0 / 3.0 | Temperature windows `[Start, Start+Step)`, `[Start+Step, Start+2·Step)`, … up to `End`. Each window yields one response. |
   | Adaptive block / C | 21 / 2 | `cv2.adaptiveThreshold` (Gaussian) parameters for binarisation. |
   | Resize | 64 | Binary image is resized to `Resize × Resize` before the DCT (must be ≥ 32). |
   | DCT crop | `2:33` | 1-based inclusive row/column range of DCT coefficients kept (must be exactly 32 × 32). |
   | DCT sign quantize | on | `bit = (coef > 0)`; off = median-magnitude threshold instead. |

5. **Run Macro & Save** (single file) or **Batch Run All Samples** (all `_new.mat` files with
   saved points/ROI). **Batch Save Points/ROI** lets you set points/ROI for many files up front.

For every window the pipeline is:

```
ROI (°C) ─ clip to [min, max) ─ normalise ─ invert ─ adaptiveThreshold ─▶ binary      (R*_bin.png)
         ─ resize 64×64 ─ dctn(type-II, ortho) ─ sign quantise ─ crop 32×32 ─ XOR seed ─▶ 1024 bits  (R*_bits.png / .xlsx)
```

The XOR seed (`SEED_RAND2`, a fixed 32 × 32 binary matrix) is embedded at the top of
`execute.py`, so responses are reproducible without any external file.

### Output format

For an input `<base>_new.mat` and trigger `T`, a folder `<base>_T/` is created next to it:

| File | Content |
|------|---------|
| `Reference_Thermal.png` | ROI at the trigger frame, colour-scaled to `[Start, End]` |
| `R<n>_<min>-<max>_thermal.png` | ROI colour-scaled to the window |
| `R<n>_<min>-<max>_bin.png` | Binarised ROI (`0`/`255`) |
| `R<n>_<min>-<max>_bits.png` | The 32 × 32 response, upscaled 10× for viewing |
| `<base>_<T>_<Start>_<End>_<Step>.xlsx` | Sheet `ThermalBits`: one column per window, header `R<n>_<min>-<max>`, **1024 rows** (row-major flatten of the 32 × 32 response) |

Which of the PNG/XLSX outputs are written is selectable under **Save Options**.

### Step 4 — `hd_analyzer_min.py`: PUF metrics (HD, uniqueness, reliability, entropy)

```bash
python python/hd_analyzer_min.py
```

Takes the Step-3 `.xlsx` responses of **N samples × R repeated measurements** and computes the
standard PUF figures of merit. (`_min` = *min-entropy*: this version adds the NIST SP 800-90B
min-entropy estimators on top of the Shannon-only analyzer.)

1. **Add files** / **Add folder** — select every `.xlsx` (all samples × all reps). Files are
   natural-sorted by name and grouped **in order**: files 1…R → sample 1, R+1…2R → sample 2, …
   Name them so that they sort correctly, e.g. `S01_rep1`, `S01_rep2`, …, `S30_rep5`.
2. **Reps per sample** — R (default 5). The number of detected samples (`⌊files / R⌋`) is shown.
3. **Run Full PUF Analysis** — each `.xlsx` is flattened into one bit vector (all window columns
   concatenated, row-major), then:

   | Metric | Definition | Ideal |
   |--------|------------|:-----:|
   | Intra-HD (reliability) | Pairwise fractional HD between the R repetitions of the same sample; per-sample mean, rank, z-score, high-outlier flag (> mean + 2σ) | 0 |
   | Inter-HD (uniqueness) | Fractional HD between rep 1 of every pair of samples | 0.5 |
   | Uniformity | Mean fraction of 1s per response (Maiti et al. 2013) | 0.5 |
   | P_clone, FAR / FRR | Gaussian fits to the intra/inter distributions; decision threshold at their intersection (fallback `μ_inter − 3σ`), P_clone = Φ((thr − μ_inter)/σ_inter) (Pal et al. 2022), collision probability over N devices | → 0 |
   | Shannon entropy per bit | `H_i` from `p(bit_i = 1)` across samples — an **upper bound** (bit balance only) | 1 |
   | **Min-entropy per bit** | `H∞_i = −log₂ max(p_i, 1−p_i)`, plug-in **and** 99 % lower-confidence bound with n = N samples (NIST SP 800-90B); plus the IID *most-common-value* estimator on the pooled bitstream | 1 |
   | Convergence vs. sample size ("Bootstrap") | For each n = 2…N, the mean inter-/intra-HD is computed over 200 random subsets of n devices drawn **without replacement**; mean ± 1 s.d. across the 200 subsets is reported (the s.d. is 0 at n = N by construction), plus the n at which the curves converge | — |

4. **Save Results (PNG + Excel)** — writes into a chosen folder:
   - `PUF_Analysis.png` — dashboard (HD histograms + Gaussian fits, per-sample intra-HD,
     Shannon vs. min-entropy histogram, bootstrap curves, summary text),
   - `PUF_Analysis.xlsx` — sheets `PUF_Metrics`, `Intra_HD_values`, `Intra_HD_by_sample`,
     `Intra_HD_pairs`, `Inter_HD_raw`, `Bootstrap` (`N_samples`, `Inter_HD_mean`, `Inter_HD_std`,
     `Intra_HD_mean`, `Intra_HD_std` — the std columns are ±1 s.d. across the 200 subsets, not
     confidence intervals), `Per_bit_entropy` (`p_i`, `H_shannon_i`, `Hmin_i`, `Hmin_i_99LCB` per bit).

**Load test_data** looks for `.xlsx` files under `python/test_data/` (not shipped); drop any
Step-3 output folders there to try the tool. The summed "total" entropies are reported as
subadditive upper bounds, not as a key space — for cryptographic claims use the min-entropy rows.

### MATLAB version — what is identical and what is not

The MATLAB programs are ports of the Python GUIs with the same windows, buttons, parameters,
file names and file formats, so the two can be mixed freely (e.g. Python `_new.mat` → MATLAB
`execute`, or MATLAB `.xlsx` → Python `hd_analyzer_min.py`). All `.mat` files are written in the
v7 format that `scipy.io.loadmat` reads, and the coordinates stored in `_points.mat`, `_roi.mat`
and `_xy.mat` are 0-based pixel indices in both implementations. Points to be aware of:

| | Python | MATLAB | Effect |
|---|---|---|---|
| Binarisation (`execute`) | `cv2.adaptiveThreshold` (Gaussian, 8-bit) | `fspecial` + `imfilter`, rounded to 8 bit, integer bias | Identical binaries on our test ROI (0 of 104 976 pixels differ, 18 windows) |
| Area resize + DCT + XOR | `cv2.resize(INTER_AREA)`, `scipy.fftpack.dctn` | exact area average (`puf_resize_area`) + `dct2` | **Identical responses**: 0 of 18 432 bits differ over 18 windows × 4 parameter sets |
| Perspective warp (`samplematcher`) | `cv2.warpPerspective`, bilinear | `fitgeotrans` + `imwarp`, bilinear | Same mapping; interpolation rounding differs slightly (max 0.07 °C, mean 0.001 °C on a 390 × 760 test frame) |
| Auto corner snap | nearest *vertex* of the simplified contour (`CHAIN_APPROX_SIMPLE`) | nearest *pixel* of the blob boundary (`bwboundaries`) | Snap positions can differ before the identical sub-pixel refinement; the points are always reviewed on screen |
| Metrics (`hd_analyzer_min`) | NumPy / SciPy | MATLAB + Statistics Toolbox | Identical to the printed precision (verified on the 30 × 5 dataset: all `PUF_Metrics`, per-bit and raw-HD values match; the random-subsample convergence curves differ only by their random draws) |
| `.xlsx` styling | bold, coloured header row | plain header row | Same sheets, columns and values |
| Colormaps (preview, `*_thermal.png`) | matplotlib `jet`, `inferno`, `plasma`, `magma`, `viridis`, `gray`, `hot`, `cool` | built-in MATLAB `jet`, `parula`, `hot`, `cool`, `gray`, `bone`, `copper`, `hsv` | Visualisation only; the response bits do not depend on the colormap |

Because the Python tools read `.mat` files with `scipy.io.loadmat` (MAT v5/v7 only), a MATLAB
`_new.mat` larger than 2 GB — which MATLAB can only store as v7.3 — cannot be opened by
`execute.py`; use the MATLAB `execute` for such files.

### Expected run time

Interactive; each step completes within seconds per sample on an ordinary laptop, except
`Count2Temp.py`, whose cost scales with the number of frames in the `.seq` file (reading through
the SDK dominates). `hd_analyzer_min.py` on 30 samples × 5 reps (150 files, 3072 bits each) takes ≈ 20 s on a
desktop CPU — ≈ 3 s to read the `.xlsx` files and ≈ 16 s for the 200-subset convergence analysis
(the MATLAB version takes ≈ 30 s on the same data). No GPU is involved.
