import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from itertools import combinations
from scipy.stats import norm
from scipy.special import comb
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import re

# ── color theme ───────────────────────────────────────────────────────────────
BG_COLOR     = "#2e2e2e"
PANEL_COLOR  = "#3c3f41"
TEXT_COLOR   = "#ffffff"
ACCENT_COLOR = "#3a96dd"
ACTION_COLOR = "#e67e22"
SUCCESS_COLOR= "#27ae60"
ENTRY_BG     = "#45494a"
LIST_BG      = "#2b2b2b"


# ═════════════════════════════════════════════════════════════════════════════
#  PUF METRIC COMPUTATIONS
#  References:
#    Maiti et al. (2013) Springer — Uniformity, Uniqueness, Reliability
#    Pal   et al. (2022) Sci.Rep. — P_clone via Gaussian CDF
#    Shannon    (1948)             — Per-bit Shannon entropy (uniformity, UPPER bound)
#    NIST SP 800-90B (2018)        — Min-entropy (per-bit + IID MCV), crypto LOWER bound
#
#  NOTE on entropy reporting:
#    * Shannon per-bit entropy (H_avg) measures only per-bit BALANCE; summing it
#      (H_total = Sum H_i) is an UPPER bound on the joint entropy (subadditivity),
#      attained only if all bits are mutually independent. It is NOT a keyspace.
#    * For cryptographic claims, report MIN-ENTROPY (lower bound on unpredictability).
#      Min-entropy <= Shannon entropy always.
# ═════════════════════════════════════════════════════════════════════════════

def compute_uniformity(bits_matrix):
    """
    Uniformity (Maiti 2013):
      U = (1/s) * sum(K_l)   averaged over all samples
      Ideal = 0.5  (50%)
    bits_matrix : (N_samples, N_bits)
    """
    return float(np.mean(bits_matrix))   # = mean(all bits)


def compute_uniqueness(inter_hds):
    """
    Uniqueness (Maiti 2013):
      Uniqueness = 2/(q*(q-1)) * sum(HD_ij/s) * 100%
                 = 2 * mean(inter_hds) * 100%
      Ideal = 100%
    """
    if len(inter_hds) == 0:
        return float('nan')
    return float(2.0 * np.mean(inter_hds) * 100.0)


def compute_reliability(intra_hds):
    """
    Reliability (Maiti 2013):
      Reliability = 1 - intra_HD  (mean)
      Ideal = 100%
    """
    if len(intra_hds) == 0:
        return float('nan')
    return float((1.0 - np.mean(intra_hds)) * 100.0)


def safe_mean(values):
    if len(values) == 0:
        return float('nan')
    return float(np.mean(values))


def safe_std(values):
    if len(values) == 0:
        return float('nan')
    return float(np.std(values))


def compute_gaussian_stats(hds):
    if len(hds) < 2:
        return float('nan'), float('nan')
    return float(np.mean(hds)), float(np.std(hds))


def compute_p_clone(inter_hds, threshold=None):
    """
    P_clone (Pal et al. 2022, Sci. Rep.):
      Fit Gaussian to inter-HD distribution.
      threshold (if None) = mu_inter - 3*sigma_inter  (FAR = 0.13%)
      P_clone = Phi( (threshold - mu) / sigma )
               = probability that an adversarial clone falls below threshold

    Returns: p_clone (float), threshold (float), mu, sigma
    """
    if len(inter_hds) < 2:
        return float('nan'), float('nan'), float('nan'), float('nan')

    mu    = float(np.mean(inter_hds))
    sigma = float(np.std(inter_hds))

    if threshold is None:
        threshold = mu - 3.0 * sigma      # default: 3-sigma below mean

    # P_clone = CDF of Normal at threshold
    p_clone = float(norm.cdf(threshold, loc=mu, scale=sigma))
    return p_clone, threshold, mu, sigma


def compute_false_rates(mu_intra, sigma_intra, mu_inter, sigma_inter, threshold):
    """
    Threshold-based Gaussian error rates using normalized PDFs/CDFs (area = 1).
      FPR = P(inter <= threshold)
      FNR = P(intra > threshold)
    """
    values = (mu_intra, sigma_intra, mu_inter, sigma_inter, threshold)
    if not all(np.isfinite(v) for v in values):
        return float('nan'), float('nan')
    if sigma_intra <= 0 or sigma_inter <= 0:
        return float('nan'), float('nan')

    false_positive = float(norm.cdf(threshold, loc=mu_inter, scale=sigma_inter))
    false_negative = float(norm.sf(threshold, loc=mu_intra, scale=sigma_intra))
    return false_positive, false_negative


def compute_collision_prob(p_clone, n_devices):
    """
    Expected number of collisions among n_devices:
      E[collision] = C(n,2) * p_clone
    """
    if n_devices < 2 or not np.isfinite(p_clone):
        return float('nan')
    n_pairs = comb(n_devices, 2, exact=True)
    return float(n_pairs) * p_clone


def compute_gaussian_intersection(mu1, sigma1, mu2, sigma2):
    """
    Return the physically relevant intersection of two normalized Gaussian PDFs.
    The chosen root is the one that lies between the two means if possible.

    Returns: x_intersection, y_pdf
    """
    if not all(np.isfinite(v) for v in (mu1, sigma1, mu2, sigma2)):
        return float('nan'), float('nan')
    if sigma1 <= 0 or sigma2 <= 0:
        return float('nan'), float('nan')

    if np.isclose(sigma1, sigma2):
        x = 0.5 * (mu1 + mu2)
        y = float(norm.pdf(x, mu1, sigma1))
        return float(x), y

    a = (1.0 / sigma1**2) - (1.0 / sigma2**2)
    b = (-2.0 * mu1 / sigma1**2) + (2.0 * mu2 / sigma2**2)
    c = (
        (mu1**2 / sigma1**2)
        - (mu2**2 / sigma2**2)
        - 2.0 * np.log(sigma2 / sigma1)
    )

    roots = np.roots([a, b, c])
    real_roots = sorted(float(np.real(r)) for r in roots if np.isreal(r))
    if not real_roots:
        return float('nan'), float('nan')

    lo, hi = sorted((mu1, mu2))
    between = [r for r in real_roots if lo <= r <= hi]
    x = between[0] if between else min(real_roots, key=lambda r: abs(r - 0.5 * (mu1 + mu2)))
    y = float(norm.pdf(x, mu1, sigma1))
    return float(x), y


def compute_shannon_entropy(bits_matrix):
    """
    Per-bit Shannon entropy (Shannon 1948).
    bits_matrix : (N_samples, N_bits)
    Returns:
      H_total : sum of per-bit entropy  (ideal = N_bits)
      H_avg   : mean per-bit entropy    (ideal = 1.0)
      IBR     : H_total / N_bits * 100% (ideal = 100%)
      p       : per-bit probabilities
    """
    eps = 1e-12
    p   = np.mean(bits_matrix, axis=0)
    p_s = np.clip(p, eps, 1.0 - eps)
    H   = -p_s * np.log2(p_s) - (1.0 - p_s) * np.log2(1.0 - p_s)

    H_total = float(np.sum(H))
    H_avg   = float(np.mean(H))
    N_bits  = bits_matrix.shape[1]
    IBR     = H_total / N_bits * 100.0
    return H_total, H_avg, IBR, p, H


def compute_min_entropy_perbit(bits_matrix, alpha=0.005):
    """
    Per-bit-position MIN-entropy across devices (cryptographic lower bound).
    bits_matrix : (N_devices, N_bits)

    For each bit position i:
        p_i    = P(bit_i = 1) over the N device responses
        p_max  = max(p_i, 1 - p_i)                       # most-likely-symbol prob
        H_inf_i (plug-in)  = -log2(p_max)                # ideal = 1.0 (p = 0.5)

    NIST SP 800-90B-style 99% upper-confidence bound on p_max (n = N devices):
        z      = Phi^-1(1 - alpha)            (alpha = 0.005  ->  z ≈ 2.576)
        p_u    = min(1, p_max + z*sqrt(p_max(1-p_max)/(N-1)))
        H_inf_i (99% LCB)  = -log2(p_u)                  # conservative

    Returns:
      Hmin_total_pi, Hmin_avg_pi,            # plug-in     (sum / mean over bits)
      Hmin_total_cb, Hmin_avg_cb,            # 99% lower-confidence-bounded
      Hmin_bits_pi, Hmin_bits_cb, p          # per-bit arrays + per-bit p

    CAUTION: min-entropy <= Shannon entropy. The TOTAL (sum over bits) assumes bit
    independence and is therefore an UPPER bound on the JOINT min-entropy
    (subadditivity); it is a ceiling, NOT a guaranteed keyspace.
    With only N devices per bit, the 99% LCB is the honest conservative figure.
    """
    eps = 1e-12
    N   = int(bits_matrix.shape[0])
    p     = np.mean(bits_matrix, axis=0)
    pmax  = np.clip(np.maximum(p, 1.0 - p), 0.5, 1.0 - eps)
    Hmin_bits_pi = -np.log2(pmax)

    if N > 1:
        z      = float(norm.ppf(1.0 - alpha))
        pmax_u = np.minimum(1.0 - eps, pmax + z * np.sqrt(pmax * (1.0 - pmax) / (N - 1)))
    else:
        pmax_u = pmax
    Hmin_bits_cb = -np.log2(pmax_u)

    return (float(np.sum(Hmin_bits_pi)), float(np.mean(Hmin_bits_pi)),
            float(np.sum(Hmin_bits_cb)), float(np.mean(Hmin_bits_cb)),
            Hmin_bits_pi, Hmin_bits_cb, p)


def compute_nist_mcv_min_entropy(bits_matrix, alpha=0.005):
    """
    NIST SP 800-90B IID 'Most Common Value' (MCV) min-entropy over the pooled
    bitstream (all devices x all bit positions treated as one i.i.d. symbol source).
        n     = total number of bits
        p_hat = max(count0, count1) / n
        p_u   = min(1, p_hat + z*sqrt(p_hat(1-p_hat)/(n-1))),  z = Phi^-1(1 - alpha)
        H_min = -log2(p_u)        (bits of min-entropy per output bit)

    CAUTION: the IID-track MCV assumes i.i.d. symbols and is therefore BLIND to
    per-position / spatial structure; it tends to OVER-estimate for 2-D PUF arrays.
    For publication, run the full 800-90B non-IID suite (10 estimators; final
    estimate = min over estimators) with the official NIST tool.
    Returns: H_min, p_hat, p_u, n
    """
    eps  = 1e-12
    flat = np.asarray(bits_matrix).reshape(-1)
    n    = int(flat.size)
    if n < 2:
        return float('nan'), float('nan'), float('nan'), n
    c1    = int(np.sum(flat != 0))
    p_hat = max(n - c1, c1) / n
    z     = float(norm.ppf(1.0 - alpha))
    p_u   = min(1.0 - eps, p_hat + z * np.sqrt(p_hat * (1.0 - p_hat) / (n - 1)))
    H_min = float(-np.log2(p_u))
    return H_min, float(p_hat), float(p_u), n


def compute_bootstrap(samples_dict, n_rep):
    """
    Bootstrap convergence (Maiti 2013 style):
      For N = 2, 3, ..., N_total:
        Randomly sample N devices (rep=0 of each) and compute
        mean Inter-HD and mean Intra-HD.
      Repeat B times, take mean ± std.

    Returns: ns, inter_means, inter_stds, intra_means, intra_stds
    """
    names = list(samples_dict.keys())
    N_total = len(names)
    B = 200   # bootstrap iterations

    if N_total < 2:
        empty = np.array([])
        return empty, empty, empty, empty, empty

    ns          = list(range(2, N_total + 1))
    inter_means = []
    inter_stds  = []
    intra_means = []
    intra_stds  = []

    for n in ns:
        inter_b = []
        intra_b = []
        for _ in range(B):
            chosen = np.random.choice(names, size=n, replace=False)
            # inter
            hds_inter = []
            for a, b in combinations(chosen, 2):
                r1 = samples_dict[a][0]
                r2 = samples_dict[b][0]
                mn = min(len(r1), len(r2))
                hds_inter.append(np.sum(r1[:mn] != r2[:mn]) / mn)
            # intra (all reps of chosen devices)
            hds_intra = []
            for dev in chosen:
                reps = samples_dict[dev]
                for r1, r2 in combinations(reps, 2):
                    mn = min(len(r1), len(r2))
                    hds_intra.append(np.sum(r1[:mn] != r2[:mn]) / mn)
            if hds_inter:
                inter_b.append(np.mean(hds_inter))
            if hds_intra:
                intra_b.append(np.mean(hds_intra))

        inter_means.append(np.mean(inter_b) if inter_b else np.nan)
        inter_stds.append(np.std(inter_b)   if inter_b else np.nan)
        intra_means.append(np.mean(intra_b) if intra_b else np.nan)
        intra_stds.append(np.std(intra_b)   if intra_b else np.nan)

    return (np.array(ns),
            np.array(inter_means), np.array(inter_stds),
            np.array(intra_means), np.array(intra_stds))


def estimate_bootstrap_convergence_n(ns, means, stds, mean_tol=0.005, std_tol=0.005):
    """
    Heuristic convergence point:
      smallest N after which the bootstrap mean stays within mean_tol of
      the final mean and the bootstrap std stays below std_tol.
    """
    if len(ns) == 0 or len(means) == 0 or len(stds) == 0:
        return float('nan')

    finite_mask = np.isfinite(means) & np.isfinite(stds)
    if not np.any(finite_mask):
        return float('nan')

    final_mean = float(means[finite_mask][-1])
    for i in range(len(ns)):
        tail_means = means[i:]
        tail_stds = stds[i:]
        tail_mask = np.isfinite(tail_means) & np.isfinite(tail_stds)
        if not np.any(tail_mask):
            continue
        if (np.all(np.abs(tail_means[tail_mask] - final_mean) <= mean_tol)
                and np.all(tail_stds[tail_mask] <= std_tol)):
            return int(ns[i])
    return float('nan')


# ═════════════════════════════════════════════════════════════════════════════
#  GUI
# ═════════════════════════════════════════════════════════════════════════════

class HDAnalyzerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("LM-PUF  HD & PUF Parameter Analyzer  (Min-entropy / NIST SP 800-90B)")
        self.root.geometry("980x760")
        self.root.configure(bg=BG_COLOR)

        self.all_files    = []
        self.n_per_sample = tk.IntVar(value=5)

        self._setup_style()
        self._create_layout()
        self.root.mainloop()

    # ── style ─────────────────────────────────────────────────────────────────
    def _setup_style(self):
        s = ttk.Style()
        s.theme_use('clam')
        s.configure("TFrame",      background=PANEL_COLOR)
        s.configure("TLabel",      background=PANEL_COLOR, foreground=TEXT_COLOR,
                    font=("Segoe UI", 10))
        s.configure("Bold.TLabel", background=PANEL_COLOR, foreground=ACCENT_COLOR,
                    font=("Segoe UI", 10, "bold"))
        s.configure("TButton",     font=("Segoe UI", 10, "bold"), padding=6,
                    background=ACCENT_COLOR, foreground="white", borderwidth=0)
        s.map("TButton", background=[('active', '#2b7bbd')])
        s.configure("TLabelframe",       background=PANEL_COLOR, foreground=TEXT_COLOR)
        s.configure("TLabelframe.Label", background=PANEL_COLOR,
                    foreground=ACCENT_COLOR, font=("Segoe UI", 10, "bold"))
        s.configure("TSpinbox", fieldbackground=ENTRY_BG,
                    foreground=TEXT_COLOR, background=PANEL_COLOR)

    # ── layout ────────────────────────────────────────────────────────────────
    def _create_layout(self):
        # 파일 선택
        frame_file = ttk.LabelFrame(self.root,
                                    text=" 1. Select Excel files (all samples x all reps) ",
                                    padding=10)
        frame_file.pack(fill=tk.BOTH, expand=True, padx=15, pady=(15, 5))

        btn_row = tk.Frame(frame_file, bg=PANEL_COLOR)
        btn_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(btn_row, text="Add files",
                   command=self._add_files).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_row, text="Add folder",
                   command=self._add_folder).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_row, text="Load test_data",
                   command=self._load_test_data).pack(side=tk.LEFT, padx=(0, 6))
        self.btn_remove = ttk.Button(btn_row, text="Remove selected",
                                     command=self._remove_selected,
                                     state="disabled")
        self.btn_remove.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_row, text="Clear all",
                   command=self._clear_files).pack(side=tk.LEFT)
        self.lbl_count = ttk.Label(btn_row, text="0 files selected",
                                   style="Bold.TLabel")
        self.lbl_count.pack(side=tk.RIGHT, padx=6)

        list_frame = tk.Frame(frame_file, bg=PANEL_COLOR)
        list_frame.pack(fill=tk.BOTH, expand=True)
        scroll_y = tk.Scrollbar(list_frame, orient=tk.VERTICAL)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox = tk.Listbox(list_frame, bg=LIST_BG, fg="white",
                                  selectbackground=ACCENT_COLOR,
                                  selectmode=tk.EXTENDED,
                                  font=("Consolas", 9), height=9,
                                  bd=0, yscrollcommand=scroll_y.set)
        self.listbox.pack(fill=tk.BOTH, expand=True)
        scroll_y.config(command=self.listbox.yview)
        self.listbox.bind('<<ListboxSelect>>', self._update_remove_button)
        self.listbox.bind('<Delete>', self._remove_selected)
        self.listbox.bind('<BackSpace>', self._remove_selected)

        # 설정
        frame_cfg = ttk.LabelFrame(self.root, text=" 2. Settings ", padding=12)
        frame_cfg.pack(fill=tk.X, padx=15, pady=5)

        ttk.Label(frame_cfg, text="Reps per sample:").grid(
            row=0, column=0, sticky='w', padx=6)
        self.spin_rep = ttk.Spinbox(
            frame_cfg, from_=1, to=100,
            textvariable=self.n_per_sample,
            width=8, command=self._refresh_info)
        self.spin_rep.grid(row=0, column=1, sticky='w', padx=6)
        self.spin_rep.bind('<Return>',   lambda e: self._refresh_info())
        self.spin_rep.bind('<FocusOut>', lambda e: self._refresh_info())

        ttk.Label(frame_cfg, text="Detected samples:").grid(
            row=0, column=2, sticky='w', padx=(30, 6))
        self.lbl_samples = ttk.Label(frame_cfg, text="0",
                                     foreground="#00ff88",
                                     background=PANEL_COLOR,
                                     font=("Segoe UI", 11, "bold"))
        self.lbl_samples.grid(row=0, column=3, sticky='w')

        ttk.Label(frame_cfg,
                  text="Files are grouped in order: files 1~N = sample1, N+1~2N = sample2 ...",
                  foreground="#aaaaaa").grid(
            row=1, column=0, columnspan=5, sticky='w', padx=6, pady=(6, 0))

        # 실행 버튼
        frame_run = tk.Frame(self.root, bg=BG_COLOR)
        frame_run.pack(fill=tk.X, padx=15, pady=10)
        self.btn_run = tk.Button(
            frame_run,
            text="Run Full PUF Analysis  (HD + Uniformity + Uniqueness + Reliability + P_clone + Entropy + Bootstrap)",
            font=("Segoe UI", 11, "bold"),
            bg=SUCCESS_COLOR, fg="white",
            activebackground="#2ecc71",
            relief="flat", state="disabled",
            command=self._run_analysis
        )
        self.btn_run.pack(fill=tk.X, ipady=10)

    # ── file management ───────────────────────────────────────────────────────
    def _natural_key(self, path_str):
        parts = re.split(r'(\d+)', path_str.lower())
        return [int(p) if p.isdigit() else p for p in parts]

    def _refresh_file_listbox(self):
        self.listbox.delete(0, tk.END)
        root_dir = Path.cwd()
        for file_path in self.all_files:
            path_obj = Path(file_path)
            try:
                display = str(path_obj.relative_to(root_dir))
            except ValueError:
                display = path_obj.name
            self.listbox.insert(tk.END, "  " + display)

    def _update_remove_button(self, event=None):
        state = "normal" if self.listbox.curselection() else "disabled"
        self.btn_remove.config(state=state)

    def _add_paths(self, paths):
        added = 0
        existing = set(self.all_files)
        for path in sorted((str(Path(p).resolve()) for p in paths), key=self._natural_key):
            if path not in existing:
                self.all_files.append(path)
                existing.add(path)
                added += 1

        self.all_files.sort(key=self._natural_key)
        self._refresh_file_listbox()
        self._refresh_info()
        self.btn_run.config(state="normal" if self.all_files else "disabled")
        self._update_remove_button()
        return added

    def _add_files(self):
        files = filedialog.askopenfilenames(
            title="Select xlsx files (all samples, all reps)",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if not files:
            return
        added = self._add_paths(files)
        if added == 0:
            messagebox.showinfo("Info", "No new Excel files were added.")

    def _add_folder(self):
        folder = filedialog.askdirectory(
            title="Select folder containing xlsx files",
            initialdir=str(Path.cwd())
        )
        if not folder:
            return

        files = [str(p) for p in Path(folder).rglob("*.xlsx")]
        if not files:
            messagebox.showwarning("No Files", "No .xlsx files were found in the selected folder.")
            return

        added = self._add_paths(files)
        self.lbl_count.config(text=f"{len(self.all_files)} files selected ({added} added)")

    def _load_test_data(self):
        test_data_dir = Path(__file__).resolve().parent / "test_data"
        if not test_data_dir.exists():
            messagebox.showerror("Missing Folder", f"Folder not found:\n{test_data_dir}")
            return

        files = [str(p) for p in test_data_dir.rglob("*.xlsx")]
        if not files:
            messagebox.showwarning("No Files", f"No .xlsx files were found under:\n{test_data_dir}")
            return

        added = self._add_paths(files)
        self.lbl_count.config(text=f"{len(self.all_files)} files selected ({added} added)")

    def _clear_files(self):
        self.all_files.clear()
        self.listbox.delete(0, tk.END)
        self.lbl_count.config(text="0 files selected")
        self.lbl_samples.config(text="0")
        self.btn_run.config(state="disabled")
        self._update_remove_button()

    def _remove_selected(self, event=None):
        selected = [
            int(i) for i in self.listbox.curselection()
            if 0 <= int(i) < len(self.all_files)
        ]
        if not selected:
            return "break" if event is not None else None

        first_index = min(selected)
        for index in sorted(selected, reverse=True):
            del self.all_files[index]

        removed_count = len(selected)
        self._refresh_file_listbox()
        self._refresh_info()
        self.lbl_count.config(
            text=f"{len(self.all_files)} files selected ({removed_count} removed)")
        self.btn_run.config(state="normal" if self.all_files else "disabled")

        if self.all_files:
            next_index = min(first_index, len(self.all_files) - 1)
            self.listbox.selection_set(next_index)
            self.listbox.activate(next_index)
            self.listbox.see(next_index)

        self._update_remove_button()
        return "break" if event is not None else None

    def _refresh_info(self):
        n_rep   = max(1, self.n_per_sample.get())
        n_files = len(self.all_files)
        n_s     = n_files // n_rep
        self.lbl_count.config(text=f"{n_files} files selected")
        self.lbl_samples.config(text=str(n_s))

    # ── data loading ──────────────────────────────────────────────────────────
    def _load_bits(self, filepath):
        df = pd.read_excel(filepath, header=0)
        return df.values.flatten().astype(int)

    def _hamming(self, a, b):
        n = min(len(a), len(b))
        return float(np.sum(a[:n] != b[:n]) / n)

    # ── analysis ──────────────────────────────────────────────────────────────
    def _run_analysis(self):
        n_rep     = max(1, self.n_per_sample.get())
        n_files   = len(self.all_files)
        n_samples = n_files // n_rep
        n_leftover = n_files % n_rep

        if n_samples < 1:
            messagebox.showerror("Error",
                f"File count ({n_files}) < reps per sample ({n_rep}).")
            return
        if n_leftover:
            messagebox.showwarning(
                "Warning",
                f"File count ({n_files}) is not divisible by reps per sample ({n_rep}).\n"
                f"{n_leftover} file(s) at the end will be ignored."
            )
        if n_samples == 1 and n_rep < 2:
            messagebox.showerror(
                "Error",
                "Single-sample intra-HD analysis requires at least 2 repetitions."
            )
            return
        if n_samples < 2:
            messagebox.showwarning("Warning",
                "Only 1 sample selected. Inter-HD based metrics will be skipped.")

        self.btn_run.config(state="disabled", text="Computing...")
        self.root.update()

        try:
            # ── load ──────────────────────────────────────────────────────────
            print("\n>> Loading files...")
            samples = {}
            for i in range(n_samples):
                name = f"S{i+1:02d}"
                samples[name] = []
                for j in range(n_rep):
                    idx  = i * n_rep + j
                    bits = self._load_bits(self.all_files[idx])
                    samples[name].append(bits)
                    print(f"   [{name} rep{j+1}] {os.path.basename(self.all_files[idx])}")

            # ── Intra-HD ──────────────────────────────────────────────────────
            intra_hds, intra_labels = [], []
            intra_pair_rows = []
            intra_sample_stats = []
            for name, meas in samples.items():
                pairwise_hds = []
                pairwise_labels = []
                for (idx1, m1), (idx2, m2) in combinations(enumerate(meas, start=1), 2):
                    hd = self._hamming(m1, m2)
                    pairwise_hds.append(hd)
                    pairwise_labels.append(f"{name}_rep{idx1}_vs_rep{idx2}")
                    intra_pair_rows.append((name, f"rep{idx1}_vs_rep{idx2}", float(hd)))
                if not pairwise_hds:
                    continue
                pairwise_arr = np.array(pairwise_hds, dtype=float)
                sample_stat = {
                    'sample': name,
                    'n_pairs': int(len(pairwise_arr)),
                    'mean': safe_mean(pairwise_arr),
                    'std': safe_std(pairwise_arr),
                    'min': float(np.min(pairwise_arr)),
                    'max': float(np.max(pairwise_arr)),
                }
                intra_sample_stats.append(sample_stat)
                if n_samples == 1:
                    intra_hds.extend(float(hd) for hd in pairwise_arr)
                    intra_labels.extend(pairwise_labels)
                else:
                    intra_hds.append(sample_stat['mean'])
                    intra_labels.append(name)

            # ── Inter-HD ──────────────────────────────────────────────────────
            inter_hds, inter_labels = [], []
            names = list(samples.keys())
            for n1, n2 in combinations(names, 2):
                inter_hds.append(self._hamming(samples[n1][0], samples[n2][0]))
                inter_labels.append(f"{n1}_vs_{n2}")

            intra_hds = np.array(intra_hds)
            inter_hds = np.array(inter_hds) if inter_hds else np.array([])
            intra_mean_global = safe_mean(intra_hds)
            intra_std_global  = safe_std(intra_hds)
            intra_high_threshold = float('nan')
            if len(intra_hds) > 1 and np.isfinite(intra_std_global) and intra_std_global > 0:
                intra_high_threshold = intra_mean_global + 2.0 * intra_std_global
            intra_sample_stats = sorted(
                intra_sample_stats,
                key=lambda row: row['mean'] if np.isfinite(row['mean']) else -np.inf,
                reverse=True
            )
            for rank, row in enumerate(intra_sample_stats, start=1):
                if np.isfinite(intra_std_global) and intra_std_global > 0 and np.isfinite(row['mean']):
                    zscore = (row['mean'] - intra_mean_global) / intra_std_global
                else:
                    zscore = float('nan')
                row['rank'] = rank
                row['zscore'] = float(zscore) if np.isfinite(zscore) else float('nan')
                row['is_high_outlier'] = bool(
                    np.isfinite(intra_high_threshold) and row['mean'] > intra_high_threshold
                )

            # ── bits matrix (N_samples x N_bits) ─────────────────────────────
            # Use rep0 of each sample for bit-level analyses
            bit_rows = [samples[nm][0] for nm in names]
            min_len  = min(len(r) for r in bit_rows)
            bits_mat = np.array([r[:min_len] for r in bit_rows])

            # ── PUF metrics ───────────────────────────────────────────────────
            print(">> Computing PUF metrics...")
            uniformity  = compute_uniformity(bits_mat)
            uniqueness  = compute_uniqueness(inter_hds)
            reliability = compute_reliability(intra_hds)
            H_total, H_avg, IBR, p_bits, H_bits = compute_shannon_entropy(bits_mat)
            (hmin_total_pi, hmin_avg_pi,
             hmin_total_cb, hmin_avg_cb,
             hmin_bits_pi, hmin_bits_cb, _pmin) = compute_min_entropy_perbit(bits_mat)
            nist_hmin, nist_phat, nist_pu, nist_n = compute_nist_mcv_min_entropy(bits_mat)
            mu_inter, sigma_inter = compute_gaussian_stats(inter_hds)
            intra_mu    = safe_mean(intra_hds)
            intra_sigma = safe_std(intra_hds)
            fit_cross_x, fit_cross_y = compute_gaussian_intersection(
                intra_mu, intra_sigma, mu_inter, sigma_inter
            )
            legacy_threshold = float('nan')
            if np.isfinite(mu_inter) and np.isfinite(sigma_inter):
                legacy_threshold = mu_inter - 3.0 * sigma_inter
            threshold = fit_cross_x if np.isfinite(fit_cross_x) else legacy_threshold
            false_positive, false_negative = compute_false_rates(
                intra_mu, intra_sigma, mu_inter, sigma_inter, threshold
            )
            p_clone = false_positive
            collision = compute_collision_prob(p_clone, n_samples)

            # ── Bootstrap ─────────────────────────────────────────────────────
            print(">> Bootstrap convergence (B=200, please wait)...")
            bs = compute_bootstrap(samples, n_rep)
            bs_ns, bs_im, bs_is, bs_am, bs_as = bs
            bootstrap_conv_inter = estimate_bootstrap_convergence_n(bs_ns, bs_im, bs_is)
            bootstrap_conv_intra = estimate_bootstrap_convergence_n(bs_ns, bs_am, bs_as)
            if np.isfinite(bootstrap_conv_inter) and np.isfinite(bootstrap_conv_intra):
                bootstrap_conv_recommended = int(max(bootstrap_conv_inter, bootstrap_conv_intra))
            elif np.isfinite(bootstrap_conv_inter):
                bootstrap_conv_recommended = int(bootstrap_conv_inter)
            elif np.isfinite(bootstrap_conv_intra):
                bootstrap_conv_recommended = int(bootstrap_conv_intra)
            else:
                bootstrap_conv_recommended = float('nan')

            metrics = {
                'n_samples'  : n_samples,
                'n_rep'      : n_rep,
                'analysis_mode': 'intra_only' if n_samples == 1 else 'full',
                'n_bits'     : min_len,
                'uniformity' : uniformity,
                'uniqueness' : uniqueness,
                'reliability': reliability,
                'p_clone'    : p_clone,
                'threshold'  : threshold,
                'threshold_legacy': legacy_threshold,
                'mu_inter'   : mu_inter,
                'sigma_inter': sigma_inter,
                'mu_intra'   : intra_mu,
                'sigma_intra': intra_sigma,
                'false_positive': false_positive,
                'false_negative': false_negative,
                'intra_high_threshold': intra_high_threshold,
                'intra_pair_rows': intra_pair_rows,
                'intra_sample_stats': intra_sample_stats,
                'fit_cross_x': fit_cross_x,
                'fit_cross_y': fit_cross_y,
                'collision'  : collision,
                'H_total'    : H_total,
                'H_avg'      : H_avg,
                'IBR'        : IBR,
                'p_bits'     : p_bits,
                'H_bits'     : H_bits,
                'hmin_avg_pi'  : hmin_avg_pi,
                'hmin_total_pi': hmin_total_pi,
                'hmin_avg_cb'  : hmin_avg_cb,
                'hmin_total_cb': hmin_total_cb,
                'hmin_bits_pi' : hmin_bits_pi,
                'hmin_bits_cb' : hmin_bits_cb,
                'nist_hmin'    : nist_hmin,
                'nist_phat'    : nist_phat,
                'nist_pu'      : nist_pu,
                'nist_n'       : nist_n,
                'bootstrap'  : bs,
                'bootstrap_conv_inter': bootstrap_conv_inter,
                'bootstrap_conv_intra': bootstrap_conv_intra,
                'bootstrap_conv_recommended': bootstrap_conv_recommended,
            }

            self._show_results(
                intra_hds, intra_labels,
                inter_hds, inter_labels,
                metrics, samples
            )

        except Exception as e:
            import traceback; traceback.print_exc()
            messagebox.showerror("Error", str(e))
        finally:
            self.btn_run.config(
                state="normal",
                text="Run Full PUF Analysis  (HD + Uniformity + Uniqueness + Reliability + P_clone + Entropy + Bootstrap)"
            )

    # ── results window ────────────────────────────────────────────────────────
    def _show_results(self, intra_hds, intra_labels,
                      inter_hds, inter_labels,
                      m, samples):

        save_dir = os.path.dirname(self.all_files[0])
        analysis_mode = m.get('analysis_mode', 'full')

        win = tk.Toplevel(self.root)
        win.title("PUF Analysis Results")
        win.geometry("1560x880")
        win.configure(bg=BG_COLOR)

        fig = plt.Figure(figsize=(15.6, 8.4), facecolor=BG_COLOR)
        gs  = gridspec.GridSpec(2, 3, figure=fig,
                                left=0.06, right=0.97,
                                top=0.93,  bottom=0.08,
                                hspace=0.44, wspace=0.34)

        def style_ax(ax):
            ax.set_facecolor(BG_COLOR)
            ax.tick_params(colors='white', labelsize=8)
            for sp in ax.spines.values(): sp.set_color('#555555')
            ax.xaxis.label.set_color('white')
            ax.yaxis.label.set_color('white')
            ax.title.set_color('white')

        def fmt_sci(x):
            if not np.isfinite(x):
                return 'N/A'
            return f'{x:.4e}'

        bins   = np.linspace(0, 1, 50)
        x_fit  = np.linspace(0, 1, 300)
        bin_w  = bins[1] - bins[0]

        # ── [A] HD distribution ───────────────────────────────────────────────
        ax_hd = fig.add_subplot(gs[0, 0])
        style_ax(ax_hd)

        if len(intra_hds) > 0:
            ax_hd.hist(intra_hds, bins=bins, density=False,
                       alpha=0.75, color='#3a96dd',
                       label=f'Intra-HD  n={len(intra_hds)}')
        else:
            ax_hd.text(0.5, 0.5, 'No intra-HD pairs available',
                       ha='center', va='center', color='white',
                       transform=ax_hd.transAxes)
        if len(inter_hds) > 0:
            ax_hd.hist(inter_hds, bins=bins, density=False,
                       alpha=0.75, color='#e74c3c',
                       label=f'Inter-HD  n={len(inter_hds)}')

        if len(intra_hds) > 1 and np.isfinite(m['sigma_intra']) and m['sigma_intra'] > 0:
            mu_i, sd_i = m['mu_intra'], m['sigma_intra']
            ax_hd.plot(x_fit, norm.pdf(x_fit, mu_i, sd_i) * len(intra_hds) * bin_w,
                       color='#7ec8f7', lw=2,
                       label=f'Intra fit μ={mu_i:.3f}')
        if len(inter_hds) > 1 and np.isfinite(m['sigma_inter']) and m['sigma_inter'] > 0:
            ax_hd.plot(x_fit, norm.pdf(x_fit, m['mu_inter'], m['sigma_inter']) * len(inter_hds) * bin_w,
                       color='#f1948a', lw=2,
                       label=f'Inter fit μ={m["mu_inter"]:.3f}')
            ax_hd.axvline(m['threshold'], color='yellow', lw=1.2, ls='--',
                          label=f'Norm. threshold={m["threshold"]:.3f}')
        if np.isfinite(m['fit_cross_x']) and not np.isclose(m['fit_cross_x'], m['threshold'], equal_nan=False):
            ax_hd.axvline(m['fit_cross_x'], color='#ff66cc', lw=1.2, ls='--',
                          label=f'Fit intersection={m["fit_cross_x"]:.3f}')

        ideal_hd = 0.0 if analysis_mode == 'intra_only' else 0.5
        ideal_label = 'Ideal 0.0' if analysis_mode == 'intra_only' else 'Ideal 0.5'
        ax_hd.axvline(ideal_hd, color='white', ls=':', alpha=0.4, label=ideal_label)
        ax_hd.set_xlabel('Hamming Distance')
        ax_hd.set_ylabel('Count')
        ax_hd.set_title('[A]  Intra-HD Distribution' if analysis_mode == 'intra_only'
                        else '[A]  HD Distribution', fontweight='bold')
        handles, labels = ax_hd.get_legend_handles_labels()
        if handles:
            ax_hd.legend(facecolor=PANEL_COLOR, labelcolor='white', fontsize=7)
        ax_hd.grid(True, alpha=0.12, color='white')

        # ── [B] Intra-HD detail by sample/pair ───────────────────────────────
        ax_detail = fig.add_subplot(gs[0, 1])
        style_ax(ax_detail)
        if len(intra_hds) > 0:
            if analysis_mode == 'full':
                detail_vals = intra_hds
                detail_labels = []
                for label in intra_labels:
                    match = re.fullmatch(r'S0*(\d+)', label)
                    detail_labels.append(f"S{match.group(1)}" if match else label)
            else:
                order = np.argsort(intra_hds)[::-1]
                detail_vals = intra_hds[order]
                detail_labels = [intra_labels[idx] for idx in order]
            high_th = m.get('intra_high_threshold', float('nan'))
            colors = [
                '#ff8c69' if np.isfinite(high_th) and val > high_th else '#7ec8f7'
                for val in detail_vals
            ]
            x_pos = np.arange(len(detail_vals))
            ax_detail.bar(x_pos, detail_vals, color=colors, edgecolor='white',
                          linewidth=0.3, alpha=0.88)
            if np.isfinite(m['mu_intra']):
                ax_detail.axhline(m['mu_intra'], color='white', lw=1.2, ls='--',
                                  label=f'Mean={m["mu_intra"]:.4f}')
            if np.isfinite(high_th):
                ax_detail.axhline(high_th, color='#ffb347', lw=1.2, ls='--',
                                  label=f'High guide={high_th:.4f}')
            ax_detail.set_xticks(x_pos)
            ax_detail.set_xticklabels(detail_labels, rotation=70, ha='right', fontsize=7)
            ax_detail.set_xlabel('Sample' if analysis_mode == 'full' else 'Pair')
            ax_detail.set_ylabel('Mean Intra-HD' if analysis_mode == 'full' else 'Intra-HD')
            if len(detail_vals) > 0:
                ax_detail.set_ylim(0, max(float(np.max(detail_vals)) * 1.18, 0.02))
            handles, labels = ax_detail.get_legend_handles_labels()
            if handles:
                ax_detail.legend(facecolor=PANEL_COLOR, labelcolor='white', fontsize=7)
        else:
            ax_detail.text(0.5, 0.5, 'No intra-HD detail available',
                           ha='center', va='center', color='white',
                           transform=ax_detail.transAxes)
        ax_detail.set_title('[B]  Sample-wise Intra-HD' if analysis_mode == 'full'
                            else '[B]  Pair-wise Intra-HD',
                            fontweight='bold', fontsize=9)
        ax_detail.grid(True, alpha=0.12, color='white')

        # ── [C] Normalized Gaussian threshold (full + zoom) ──────────────────
        gs_thr = gs[0, 2].subgridspec(2, 1, hspace=0.20, height_ratios=[1.0, 1.0])
        ax_thr_full = fig.add_subplot(gs_thr[0, 0])
        ax_thr_zoom = fig.add_subplot(gs_thr[1, 0])
        style_ax(ax_thr_full)
        style_ax(ax_thr_zoom)
        if np.isfinite(m['fit_cross_x']):
            x_full = np.linspace(0.0, 1.0, 1200)
            y_intra_full = norm.pdf(x_full, m['mu_intra'], m['sigma_intra'])
            y_inter_full = norm.pdf(x_full, m['mu_inter'], m['sigma_inter'])
            y_full_max = max(float(np.max(y_intra_full)), float(np.max(y_inter_full))) * 1.10
            cross_x = float(m['fit_cross_x'])
            has_cross_y = np.isfinite(m['fit_cross_y'])
            cross_y = float(m['fit_cross_y']) if has_cross_y else 0.0

            ax_thr_full.plot(x_full, y_intra_full, color='#7ec8f7', lw=2, label='Intra fit')
            ax_thr_full.plot(x_full, y_inter_full, color='#f1948a', lw=2, label='Inter fit')
            if np.isfinite(m['threshold']):
                ax_thr_full.axvline(m['threshold'], color='yellow', lw=1.2, ls='--',
                                    label=f'Norm. threshold={m["threshold"]:.4f}')
            if has_cross_y:
                ax_thr_full.scatter([cross_x], [cross_y],
                                    color='#ff66cc', edgecolors='white', linewidths=0.5,
                                    s=40, zorder=6, label='Intersection')
            ax_thr_full.set_xlim(0.0, 1.0)
            ax_thr_full.set_ylim(0.0, y_full_max)
            ax_thr_full.set_ylabel('Normalized PDF')
            ax_thr_full.set_title('[C]  Normalized Gaussian Threshold',
                                  fontweight='bold', fontsize=9)
            ax_thr_full.text(0.50, 0.92, f"Threshold = {m['threshold']:.4f}",
                             transform=ax_thr_full.transAxes,
                             ha='center', va='top', fontsize=9, color='white')
            ax_thr_full.legend(facecolor=PANEL_COLOR, labelcolor='white', fontsize=7,
                               loc='upper left')

            ax_thr_zoom.plot(x_full, y_intra_full, color='#7ec8f7', lw=2, label='Intra fit')
            ax_thr_zoom.plot(x_full, y_inter_full, color='#f1948a', lw=2, label='Inter fit')
            if np.isfinite(m['threshold']):
                ax_thr_zoom.axvline(m['threshold'], color='yellow', lw=1.2, ls='--',
                                    label=f'Norm. threshold={m["threshold"]:.4f}')
            if has_cross_y:
                if not np.isclose(cross_x, m['threshold'], equal_nan=False):
                    ax_thr_zoom.axvline(cross_x, color='#ff66cc', lw=1.4, ls='--',
                                        label=f'Intersection={cross_x:.4f}')
                ax_thr_zoom.axhline(cross_y, color='#ff66cc', lw=1.0, ls=':',
                                    alpha=0.7)
                ax_thr_zoom.scatter([cross_x], [cross_y],
                                    color='#ff66cc', edgecolors='white', linewidths=0.5,
                                    s=52, zorder=6)
            ax_thr_zoom.set_xlim(0.3, 0.5)
            if has_cross_y and cross_y > 0:
                y_zoom_max = cross_y * 3.0
            else:
                x_zoom = np.linspace(0.3, 0.5, 600)
                y_zoom_intra = norm.pdf(x_zoom, m['mu_intra'], m['sigma_intra'])
                y_zoom_inter = norm.pdf(x_zoom, m['mu_inter'], m['sigma_inter'])
                y_zoom_max = max(
                    float(np.max(y_zoom_intra)),
                    float(np.max(y_zoom_inter)),
                    np.finfo(float).tiny
                )
            ax_thr_zoom.set_ylim(0.0, y_zoom_max)
            ax_thr_zoom.set_xlabel('Hamming Distance')
            ax_thr_zoom.set_ylabel('Normalized PDF')
            ax_thr_zoom.ticklabel_format(axis='y', style='sci', scilimits=(0, 0), useMathText=True)
            rate_text = (
                f"Normalized threshold = {m['threshold']:.4f}\n"
                f"Intersection PDF = {fmt_sci(cross_y)}\n"
                f"False positive rate = {fmt_sci(m['false_positive'])}\n"
                f"False negative rate = {fmt_sci(m['false_negative'])}"
            )
            ax_thr_zoom.text(0.03, 0.95, rate_text,
                             transform=ax_thr_zoom.transAxes,
                             ha='left', va='top', fontsize=8.3, color='white',
                             bbox=dict(boxstyle='round,pad=0.35',
                                       facecolor=PANEL_COLOR, alpha=0.78))
        else:
            thr_msg = ('Inter-HD fit unavailable in single-sample mode'
                       if analysis_mode == 'intra_only'
                       else 'Threshold / fit view unavailable')
            for ax_thr in (ax_thr_full, ax_thr_zoom):
                ax_thr.text(0.5, 0.5, thr_msg,
                            ha='center', va='center', color='white',
                            transform=ax_thr.transAxes)
        ax_thr_full.grid(True, alpha=0.12, color='white')
        ax_thr_zoom.grid(True, alpha=0.12, color='white')

        # ── [D] Per-bit Shannon vs Min-entropy histogram ──────────────────────
        ax_ent = fig.add_subplot(gs[1, 0])
        style_ax(ax_ent)
        ax_ent.hist(m['H_bits'], bins=40, color='#f39c12',
                    edgecolor='white', lw=0.3, alpha=0.55, label='Shannon H_i')
        ax_ent.hist(m['hmin_bits_pi'], bins=40, color='#9b59b6',
                    edgecolor='white', lw=0.3, alpha=0.55, label='Min-ent H∞_i')
        ax_ent.axvline(np.mean(m['H_bits']), color='#f39c12', lw=1.8, ls='--',
                       label=f'Shannon avg={np.mean(m["H_bits"]):.3f}')
        ax_ent.axvline(m['hmin_avg_pi'], color='#9b59b6', lw=1.8, ls='--',
                       label=f'Min-ent avg={m["hmin_avg_pi"]:.3f}')
        ax_ent.axvline(m['hmin_avg_cb'], color='#c39bd3', lw=1.4, ls='-.',
                       label=f'Min-ent 99%LCB={m["hmin_avg_cb"]:.3f}')
        ax_ent.axvline(1.0, color='lime', lw=1.0, ls=':',
                       label='Ideal=1.0')
        ax_ent.set_xlabel('Per-bit entropy  (bits)')
        ax_ent.set_ylabel('Count')
        ax_ent.set_title('[D]  Per-bit Shannon vs Min-entropy',
                         fontweight='bold', fontsize=9)
        ax_ent.legend(facecolor=PANEL_COLOR, labelcolor='white', fontsize=6.2)
        ax_ent.grid(True, alpha=0.12, color='white')

        # ── [E]/[F] Bootstrap + bit-wise uniformity ──────────────────────────
        gs_bottom_left = gs[1, 1].subgridspec(2, 1, hspace=0.32, height_ratios=[1.0, 1.0])

        ax_bs = fig.add_subplot(gs_bottom_left[0, 0])
        style_ax(ax_bs)
        ns, im_arr, is_arr, am_arr, as_arr = m['bootstrap']
        has_bootstrap_plot = False
        if len(ns) > 0:
            if np.any(np.isfinite(im_arr)):
                ax_bs.fill_between(ns, im_arr - is_arr, im_arr + is_arr,
                                   alpha=0.22, color='#e74c3c')
                ax_bs.plot(ns, im_arr, color='#e74c3c', lw=1.8, label='Inter-HD')
                has_bootstrap_plot = True
            if np.any(np.isfinite(am_arr)):
                ax_bs.fill_between(ns, am_arr - as_arr, am_arr + as_arr,
                                   alpha=0.22, color='#3a96dd')
                ax_bs.plot(ns, am_arr, color='#3a96dd', lw=1.8, label='Intra-HD')
                has_bootstrap_plot = True
            if np.any(np.isfinite(im_arr)):
                ax_bs.axhline(0.5, color='white', ls=':', alpha=0.35, label='Ideal 0.5')
            if np.isfinite(m.get('bootstrap_conv_recommended', float('nan'))):
                ax_bs.axvline(m['bootstrap_conv_recommended'], color='#f1c40f', lw=1.2, ls='--',
                              label=f'Conv. N={int(m["bootstrap_conv_recommended"])}')
            ax_bs.set_xlabel('N samples')
            ax_bs.set_ylabel('Mean HD')
            if has_bootstrap_plot:
                ax_bs.set_xlim(ns[0], ns[-1])
                handles, labels = ax_bs.get_legend_handles_labels()
                if handles:
                    ax_bs.legend(facecolor=PANEL_COLOR, labelcolor='white', fontsize=6.8,
                                 loc='best')
            else:
                ax_bs.text(0.5, 0.5, 'Bootstrap data unavailable',
                           ha='center', va='center', color='white',
                           transform=ax_bs.transAxes)
        else:
            ax_bs.text(0.5, 0.5, 'Bootstrap requires at least 2 samples',
                       ha='center', va='center', color='white',
                       transform=ax_bs.transAxes)
        ax_bs.set_title('[E]  Bootstrap Convergence', fontweight='bold', fontsize=8.8)
        ax_bs.grid(True, alpha=0.12, color='white')

        ax_uni = fig.add_subplot(gs_bottom_left[1, 0])
        style_ax(ax_uni)
        bit_idx = np.arange(len(m['p_bits']))
        if len(bit_idx) > 0:
            ax_uni.plot(bit_idx, m['p_bits'], color='#2ecc71', lw=1.1, alpha=0.95,
                        label='p(bit=1)')
            ax_uni.axhline(0.5, color='white', ls=':', alpha=0.5, label='Ideal 0.5')
            ax_uni.axhline(np.mean(m['p_bits']), color='#f1c40f', lw=1.2, ls='--',
                           label=f'Mean={np.mean(m["p_bits"]):.3f}')
            ax_uni.fill_between(bit_idx, m['p_bits'], 0.5, color='#2ecc71', alpha=0.10)
            ax_uni.set_xlim(0, len(bit_idx) - 1 if len(bit_idx) > 1 else 1)
            ax_uni.set_ylim(0.0, 1.0)
            handles, labels = ax_uni.get_legend_handles_labels()
            if handles:
                ax_uni.legend(facecolor=PANEL_COLOR, labelcolor='white', fontsize=6.8,
                              loc='upper right')
        else:
            ax_uni.text(0.5, 0.5, 'Bit-wise uniformity unavailable',
                        ha='center', va='center', color='white',
                        transform=ax_uni.transAxes)
        ax_uni.set_xlabel('Bit index')
        ax_uni.set_ylabel('Probability of 1')
        ax_uni.set_title('[F]  Bit-wise Uniformity', fontweight='bold', fontsize=8.8)
        ax_uni.grid(True, alpha=0.12, color='white')

        # ── [E] PUF metrics summary ───────────────────────────────────────────
        ax_sum = fig.add_subplot(gs[1, 2])
        ax_sum.axis('off')
        style_ax(ax_sum)

        def log10_safe(x):
            if np.isnan(x):
                return 'N/A'
            if x <= 0:
                return '-inf'
            return f'{np.log10(x):.1f}'

        def fmt_value(x, digits=4, suffix=''):
            if not np.isfinite(x):
                return 'N/A'
            return f'{x:.{digits}f}{suffix}'

        intra_mean = safe_mean(intra_hds)
        intra_std  = safe_std(intra_hds)
        inter_mean = safe_mean(inter_hds)
        inter_std  = safe_std(inter_hds)
        intra_entry_ideal = str(m['n_samples']) if analysis_mode == 'full' else '-'
        worst_intra_label = 'N/A'
        worst_intra_value = float('nan')
        if len(intra_hds) > 0:
            worst_idx = int(np.argmax(intra_hds))
            worst_intra_label = intra_labels[worst_idx]
            worst_intra_value = float(intra_hds[worst_idx])
        p_clone_str = log10_safe(m['p_clone'])
        col_str     = log10_safe(m['collision'])

        sep = "-" * 46
        summary_lines = [
            sep,
            f"  LM-PUF Standard Metrics (N={m['n_samples']} devices, {m['n_bits']} bits)",
            sep,
            f"  {'Metric':<28}  {'Value':>10}  {'Ideal':>10}",
            sep,
            f"  {'Analysis mode':<28}  {('Intra-only' if analysis_mode == 'intra_only' else 'Full'):>10}  {'-':>10}",
            f"  {'Intra-HD entries':<28}  {len(intra_hds):>10}  {intra_entry_ideal:>10}",
            f"  {'Uniformity':<28}  {fmt_value(m['uniformity'] * 100.0, 3, '%'):>10}  {'50.000%':>10}",
            f"  {'Uniqueness':<28}  {fmt_value(m['uniqueness'], 3, '%'):>10}  {'100.000%':>10}",
            f"  {'Reliability':<28}  {fmt_value(m['reliability'], 3, '%'):>10}  {'100.000%':>10}",
            sep,
            f"  {'Intra-HD  mean':<28}  {fmt_value(intra_mean, 4):>10}  {'0.0000':>10}",
            f"  {'Intra-HD  std':<28}  {fmt_value(intra_std, 4):>10}",
            f"  {'Inter-HD  mean':<28}  {fmt_value(inter_mean, 4):>10}  {'0.5000':>10}",
            f"  {'Inter-HD  std':<28}  {fmt_value(inter_std, 4):>10}",
            sep,
            f"  {'Fit intersection':<28}  {fmt_value(m['fit_cross_x'], 4):>10}",
            f"  {'Auth threshold (norm. PDF)':<28}  {fmt_value(m['threshold'], 4):>10}",
            f"  {'Legacy threshold (3-sigma)':<28}  {fmt_value(m['threshold_legacy'], 4):>10}",
            f"  {'False positive rate':<28}  {fmt_sci(m['false_positive']):>10}",
            f"  {'False negative rate':<28}  {fmt_sci(m['false_negative']):>10}",
            f"  {'P_clone  log10':<28}  {p_clone_str:>10}  {'<< -30':>10}",
            f"  {'Collision (N=' + str(m['n_samples']) + ')  log10':<28}  {col_str:>10}  {'<<  0':>10}",
            sep,
            f"  {'Bootstrap conv. N inter':<28}  {fmt_value(m['bootstrap_conv_inter'], 0):>10}",
            f"  {'Bootstrap conv. N intra':<28}  {fmt_value(m['bootstrap_conv_intra'], 0):>10}",
            f"  {'Bootstrap conv. N rec.':<28}  {fmt_value(m['bootstrap_conv_recommended'], 0):>10}",
            sep,
            f"  {'Shannon H_avg (bits/bit, UB)':<28}  {fmt_value(m['H_avg'], 4):>10}  {'1.0000':>10}",
            f"  {'Shannon H_total (=H_avg*Nb)':<28}  {fmt_value(m['H_total'], 1):>10}  {float(m['n_bits']):>10.0f}",
            f"  {'IBR  (%)':<28}  {fmt_value(m['IBR'], 3, '%'):>10}  {'100.000%':>10}",
            sep,
            f"  {'MIN-ENTROPY (NIST 800-90B)':<28}  {'':>10}  {'ideal/bit':>10}",
            f"  {'  Min-ent/bit (plug-in)':<28}  {fmt_value(m['hmin_avg_pi'], 4):>10}  {'1.0000':>10}",
            f"  {'  Min-ent/bit (99% LCB, n=dev)':<28}  {fmt_value(m['hmin_avg_cb'], 4):>10}  {'1.0000':>10}",
            f"  {'  Min-ent total (sum = UB)':<28}  {fmt_value(m['hmin_total_pi'], 1):>10}  {float(m['n_bits']):>10.0f}",
            f"  {'  NIST MCV/bit (IID, pooled)':<28}  {fmt_value(m['nist_hmin'], 4):>10}  {'1.0000':>10}",
            f"  {'  NIST MCV p_max (upper)':<28}  {fmt_value(m['nist_pu'], 4):>10}  {'0.5000':>10}",
        ]
        if analysis_mode == 'intra_only':
            summary_lines.extend([
                sep,
                "  Note: inter-HD based metrics are unavailable in single-sample mode.",
            ])
        if len(intra_hds) > 0:
            summary_lines.extend([
                sep,
                f"  Worst intra target: {worst_intra_label} = {fmt_value(worst_intra_value, 4)}",
            ])
            if np.isfinite(m.get('intra_high_threshold', float('nan'))):
                summary_lines.append(
                    f"  High intra guide: mean + 2σ = {fmt_value(m['intra_high_threshold'], 4)}"
                )
        summary_lines.extend([
            sep,
            "  Caveat: 'total' entropy = sum of per-bit values, which is an",
            "  UPPER bound on joint entropy (equality iff bits independent).",
            "  Use min-entropy (lower bound) for cryptographic keyspace claims;",
            "  for keyspace, derive effective DoF from the inter-HD distribution.",
        ])
        summary_lines.append(sep)
        summary_text = "\n".join(summary_lines)

        ax_sum.text(0.02, 0.97, summary_text,
                    transform=ax_sum.transAxes,
                    fontsize=6.5, verticalalignment='top',
                    fontfamily='Consolas', color='white',
                    bbox=dict(boxstyle='round,pad=0.45',
                              facecolor=PANEL_COLOR, alpha=0.9))

        fig.suptitle('LM-PUF  Intra-HD Analysis' if analysis_mode == 'intra_only'
                     else 'LM-PUF  Full PUF Parameter Analysis',
                     color='white', fontsize=13, fontweight='bold')

        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        canvas.draw()

        # 저장 버튼
        btn_save = tk.Button(
            win,
            text="Save Results  (PNG + Excel)",
            font=("Segoe UI", 11, "bold"),
            bg=ACTION_COLOR, fg="white",
            activebackground="#d35400",
            relief="flat",
            command=lambda: self._save_results(
                fig, intra_hds, intra_labels,
                inter_hds, inter_labels, m, save_dir)
        )
        btn_save.pack(fill=tk.X, padx=20, pady=10, ipady=8)

    # ── save ──────────────────────────────────────────────────────────────────
    def _save_results(self, fig, intra_hds, intra_labels,
                      inter_hds, inter_labels, m, save_dir):

        # PNG
        png_path = os.path.join(save_dir, "PUF_Analysis.png")
        fig.savefig(png_path, dpi=150, bbox_inches='tight', facecolor=BG_COLOR)

        # Excel
        wb  = Workbook()
        hdr = Font(bold=True, color="FFFFFF")
        bg1 = PatternFill("solid", fgColor="1F497D")
        bg2 = PatternFill("solid", fgColor="2E4057")

        # ── Sheet 1: PUF Metrics Summary ──────────────────────────────────────
        ws = wb.active
        ws.title = "PUF_Metrics"

        def add_header(ws, row, cols):
            for c, val in enumerate(cols, 1):
                cell = ws.cell(row=row, column=c, value=val)
                cell.font = hdr
                cell.fill = bg1
                cell.alignment = Alignment(horizontal='center')

        def add_row(ws, row, vals, bold=False, fill=None):
            for c, val in enumerate(vals, 1):
                cell = ws.cell(row=row, column=c, value=val)
                if bold: cell.font = Font(bold=True)
                if fill: cell.fill = fill

        def excel_scalar(value, digits=None):
            if isinstance(value, str):
                return value
            if isinstance(value, (int, np.integer)):
                return int(value)
            if isinstance(value, (float, np.floating)):
                if not np.isfinite(value):
                    return 'N/A'
                value = float(value)
                return round(value, digits) if digits is not None else value
            return value

        intra_mean = safe_mean(intra_hds)
        intra_std  = safe_std(intra_hds)
        inter_mean = safe_mean(inter_hds)
        inter_std  = safe_std(inter_hds)
        if np.isfinite(m['p_clone']) and m['p_clone'] > 0:
            p_clone_log10 = round(np.log10(m['p_clone']), 2)
        else:
            p_clone_log10 = 'N/A'

        add_header(ws, 1, ['Metric', 'Value', 'Ideal', 'Reference'])
        rows_data = [
            ('N_samples',               m['n_samples'],       '-',      '-'),
            ('N_bits per response',      m['n_bits'],         '-',      '-'),
            ('N_reps per sample',        m['n_rep'],          '-',      '-'),
            ('Intra-HD entries',        len(intra_hds),
             m['n_samples'] if m.get('analysis_mode') == 'full' else '-', '-'),
            ('Analysis mode',           'Intra-only' if m.get('analysis_mode') == 'intra_only' else 'Full',
             '-', '-'),
            ('─'*20,                    '─'*10,              '─'*10,   '─'*20),
            ('Uniformity (%)',           excel_scalar(m['uniformity']*100, 4),  50.0,
             'Maiti et al. 2013'),
            ('Uniqueness (%)',           excel_scalar(m['uniqueness'], 4),      100.0,
             'Maiti et al. 2013'),
            ('Reliability (%)',          excel_scalar(m['reliability'], 4),     100.0,
             'Maiti et al. 2013'),
            ('─'*20,                    '─'*10,              '─'*10,   '─'*20),
            ('Intra-HD mean',           excel_scalar(intra_mean, 6), 0.0, '-'),
            ('Intra-HD std',            excel_scalar(intra_std, 6), '-', '-'),
            ('Inter-HD mean',           excel_scalar(inter_mean, 6), 0.5, '-'),
            ('Inter-HD std',            excel_scalar(inter_std, 6), '-', '-'),
            ('─'*20,                    '─'*10,              '─'*10,   '─'*20),
            ('Fit intersection',        excel_scalar(m['fit_cross_x'], 4), '-', '-'),
            ('Auth threshold (norm. PDF)',excel_scalar(m['threshold'], 4),       '-',
             '-'),
            ('Legacy threshold (3-sigma)',excel_scalar(m['threshold_legacy'], 4), '-', 'Pal et al. 2022'),
            ('False positive rate',     excel_scalar(m['false_positive']), '-', '-'),
            ('False negative rate',     excel_scalar(m['false_negative']), '-', '-'),
            ('P_clone',                 excel_scalar(m['p_clone']),
             '<< 1', 'Pal et al. 2022'),
            ('P_clone log10',           p_clone_log10,
             '<<-30', 'Pal et al. 2022'),
            (f'Collision E[N={m["n_samples"]}]',
             excel_scalar(m['collision']),
             '<< 1', '-'),
            ('─'*20,                    '─'*10,              '─'*10,   '─'*20),
            ('Bootstrap conv. N inter', excel_scalar(m.get('bootstrap_conv_inter')), '-', '-'),
            ('Bootstrap conv. N intra', excel_scalar(m.get('bootstrap_conv_intra')), '-', '-'),
            ('Bootstrap conv. N rec.',  excel_scalar(m.get('bootstrap_conv_recommended')), '-', '-'),
            ('─'*20,                    '─'*10,              '─'*10,   '─'*20),
            ('Shannon H_avg (bits/bit, UB)', excel_scalar(m['H_avg'], 6),        1.0,
             'Shannon 1948 (uniformity / upper bound)'),
            ('Shannon H_total (=H_avg*Nbits)', excel_scalar(m['H_total'], 4),    m['n_bits'],
             'subadditive UPPER bound, not keyspace'),
            ('IBR (%)',                 excel_scalar(m['IBR'], 4),             100.0,
             'Kim et al. 2025'),
            ('─'*20,                    '─'*10,              '─'*10,   '─'*20),
            ('Min-entropy/bit (plug-in)', excel_scalar(m['hmin_avg_pi'], 6),    1.0,
             'NIST SP 800-90B (2018)'),
            ('Min-entropy/bit (99% LCB)', excel_scalar(m['hmin_avg_cb'], 6),    1.0,
             'NIST SP 800-90B (n = N_devices)'),
            ('Min-entropy total (sum, UB)', excel_scalar(m['hmin_total_pi'], 4), m['n_bits'],
             'subadditive UPPER bound, not keyspace'),
            ('NIST MCV min-ent/bit (IID)', excel_scalar(m['nist_hmin'], 6),     1.0,
             'NIST SP 800-90B IID-MCV (pooled)'),
            ('NIST MCV p_max (upper)',  excel_scalar(m['nist_pu'], 6),          0.5,
             'NIST SP 800-90B'),
            ('NIST MCV pooled n (bits)', excel_scalar(m['nist_n']),            '-',
             'NIST SP 800-90B'),
        ]
        for r_i, rd in enumerate(rows_data, 2):
            add_row(ws, r_i, rd)
        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 18
        ws.column_dimensions['C'].width = 12
        ws.column_dimensions['D'].width = 22

        # ── Sheet 2: Intra-HD raw ──────────────────────────────────────────────
        ws2 = wb.create_sheet("Intra_HD_values")
        add_header(ws2, 1, ['Sample_or_pair', 'HD'])
        for r_i, (lbl, hd) in enumerate(zip(intra_labels, intra_hds), 2):
            ws2.cell(r_i, 1, lbl)
            ws2.cell(r_i, 2, round(float(hd), 6))

        ws3 = wb.create_sheet("Intra_HD_by_sample")
        add_header(ws3, 1, ['Sample', 'Mean_HD', 'Std_HD', 'Min_HD', 'Max_HD',
                            'N_pairs', 'Rank', 'Zscore', 'High_outlier'])
        for r_i, row in enumerate(m.get('intra_sample_stats', []), 2):
            ws3.cell(r_i, 1, row['sample'])
            ws3.cell(r_i, 2, excel_scalar(row['mean'], 6))
            ws3.cell(r_i, 3, excel_scalar(row['std'], 6))
            ws3.cell(r_i, 4, excel_scalar(row['min'], 6))
            ws3.cell(r_i, 5, excel_scalar(row['max'], 6))
            ws3.cell(r_i, 6, row['n_pairs'])
            ws3.cell(r_i, 7, row.get('rank', ''))
            ws3.cell(r_i, 8, excel_scalar(row.get('zscore', float('nan')), 4))
            ws3.cell(r_i, 9, 'Y' if row.get('is_high_outlier') else '')

        ws4 = wb.create_sheet("Intra_HD_pairs")
        add_header(ws4, 1, ['Sample', 'Pair', 'HD'])
        for r_i, (sample_name, pair_name, hd) in enumerate(m.get('intra_pair_rows', []), 2):
            ws4.cell(r_i, 1, sample_name)
            ws4.cell(r_i, 2, pair_name)
            ws4.cell(r_i, 3, round(float(hd), 6))

        # ── Sheet 3: Inter-HD raw ──────────────────────────────────────────────
        if len(inter_hds) > 0:
            ws5 = wb.create_sheet("Inter_HD_raw")
            add_header(ws5, 1, ['Pair', 'HD'])
            for r_i, (lbl, hd) in enumerate(zip(inter_labels, inter_hds), 2):
                ws5.cell(r_i, 1, lbl)
                ws5.cell(r_i, 2, round(float(hd), 6))

        # ── Sheet 4: Bootstrap ────────────────────────────────────────────────
        ws6 = wb.create_sheet("Bootstrap")
        add_header(ws6, 1, ['N_samples',
                             'Inter_HD_mean', 'Inter_HD_std',
                             'Intra_HD_mean', 'Intra_HD_std'])
        ns, im, is_, am, as_ = m['bootstrap']
        for r_i, (n, i_m, i_s, a_m, a_s) in enumerate(zip(ns,im,is_,am,as_), 2):
            ws6.cell(r_i, 1, int(n))
            ws6.cell(r_i, 2, round(float(i_m), 6) if not np.isnan(i_m) else '')
            ws6.cell(r_i, 3, round(float(i_s), 6) if not np.isnan(i_s) else '')
            ws6.cell(r_i, 4, round(float(a_m), 6) if not np.isnan(a_m) else '')
            ws6.cell(r_i, 5, round(float(a_s), 6) if not np.isnan(a_s) else '')

        # ── Sheet 5: Per-bit entropy (Shannon + Min-entropy) ──────────────────
        ws7 = wb.create_sheet("Per_bit_entropy")
        add_header(ws7, 1, ['Bit_index', 'p_i', 'H_shannon_i', 'Hmin_i', 'Hmin_i_99LCB'])
        for r_i, (p, H, Hm, Hmc) in enumerate(
                zip(m['p_bits'], m['H_bits'], m['hmin_bits_pi'], m['hmin_bits_cb']), 2):
            ws7.cell(r_i, 1, r_i - 2)
            ws7.cell(r_i, 2, round(float(p), 6))
            ws7.cell(r_i, 3, round(float(H), 6))
            ws7.cell(r_i, 4, round(float(Hm), 6))
            ws7.cell(r_i, 5, round(float(Hmc), 6))

        xlsx_path = os.path.join(save_dir, "PUF_Analysis.xlsx")
        wb.save(xlsx_path)

        messagebox.showinfo("Saved",
            f"PNG : {os.path.basename(png_path)}\n"
            f"Excel: {os.path.basename(xlsx_path)}\n\n"
            f"Location: {save_dir}")
        print(f">> Saved: {png_path}")
        print(f">> Saved: {xlsx_path}")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    HDAnalyzerGUI()
