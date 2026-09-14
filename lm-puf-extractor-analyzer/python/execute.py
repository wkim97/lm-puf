import scipy.io as sio
import os
import re
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector, Slider
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import cv2
from scipy.fftpack import dctn
from datetime import datetime
from mpl_toolkits.axes_grid1 import make_axes_locatable
from openpyxl import Workbook

# --- 스타일 설정 ---
BG_COLOR = "#2e2e2e"       
PANEL_COLOR = "#3c3f41"    
TEXT_COLOR = "#ffffff"     
ACCENT_COLOR = "#3a96dd"   
ENTRY_BG = "#45494a"       
LIST_BG = "#2b2b2b"        

# Embedded from seed_rand.mat (seed_rand2)
SEED_RAND2 = np.array([
  [1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0],
  [1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1],
  [1, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1],
  [0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
  [1, 1, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1],
  [1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0],
  [0, 1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1],
  [1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0],
  [0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
  [1, 1, 1, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1],
  [0, 1, 0, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0],
  [1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0],
  [0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1],
  [1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0],
  [1, 0, 1, 1, 1, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1],
  [0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1],
  [1, 1, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0],
  [1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0],
  [0, 0, 1, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1],
  [1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1],
  [0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 1],
  [1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 1],
  [1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1],
  [1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0],
  [0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 1, 1, 1],
  [0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1],
  [0, 1, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 1],
  [1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0],
  [1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0],
  [0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1],
  [1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0],
  [0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0],
], dtype=int)

def imwrite_safe(filename, img):
    try:
        ext = os.path.splitext(filename)[1]
        result, n = cv2.imencode(ext, img)
        if result:
            with open(filename, mode='w+b') as f:
                n.tofile(f)
            return True
        else:
            return False
    except Exception as e:
        print(f"[Save Error] {e}")
        return False

class ModernThermalGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Thermal Analysis Pro (Perfect Arrow Navigation)")
        self.root.geometry("1400x980")
        self.root.configure(bg=BG_COLOR)
        
        self.setup_style()
        
        self.mat_path = None
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.full_data = None
        self.seed_rand2 = None
        self.points = None
        self.roi_coords = None
        self.roi_img = None
        self.trigger_idx = -1
        self.temp_history = None
        self.start_frame_idx = 0
        
        self.im_roi_obj = None 
        self.cbar = None
        self.cax = None
        self.rect_selector = None
        
        self.temp_points = []
        self.slider_obj = None
        self.batch_files = []
        self.point_setup_queue = []
        self.point_setup_index = -1
        self.point_setup_mode = False
        
        self.var_trig = tk.StringVar(value="50.0")
        self.var_start = tk.StringVar(value="40.0")
        self.var_end = tk.StringVar(value="49.0")
        self.var_step = tk.StringVar(value="3.0")
        
        self.var_vmin = tk.StringVar(value="40.0")
        self.var_vmax = tk.StringVar(value="43.0")
        self.var_cmap = tk.StringVar(value="jet")
        
        # [NEW] 노이즈 필터링 파라미터 (기본값은 원본 코드값과 동일)
        self.var_adapt_block = tk.StringVar(value="21")   # Adaptive Threshold blockSize (홀수)
        self.var_adapt_C = tk.StringVar(value="2")        # Adaptive Threshold C
        self.var_resize_size = tk.StringVar(value="64")   # Resize target size (NxN)
        self.var_dct_crop = tk.StringVar(value="2:33")    # 1-based inclusive range. Ex: 2:33 or 2:33,2:33

        # [NEW] Trigger frame averaging (1~5)
        self.var_frame_avg = tk.StringVar(value="1")      # 1 = 기존 동작, 2~5 = trigger 주변 N프레임 평균
        # [NEW] DCT sign quantize 사용 여부 (체크 시 (dct>0) 적용, 해제 시 부호 양자화 생략)
        self.chk_dct_sign = tk.BooleanVar(value=True)
        
        self.chk_binary = tk.BooleanVar(value=True) 
        self.chk_bit = tk.BooleanVar(value=True)
        self.chk_excel = tk.BooleanVar(value=True)
        self.chk_thermal = tk.BooleanVar(value=True)
        
        self.chk_reset_pts = tk.BooleanVar(value=False)
        self.chk_reset_roi = tk.BooleanVar(value=False)
        
        self.create_layout()
        self.root.mainloop()

    def setup_style(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background=PANEL_COLOR)
        style.configure("TLabel", background=PANEL_COLOR, foreground=TEXT_COLOR, font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"), foreground=ACCENT_COLOR)
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6, background=ACCENT_COLOR, foreground="white", borderwidth=0)
        style.map("TButton", background=[('active', '#2b7bbd')])
        style.configure("TCheckbutton", background=PANEL_COLOR, foreground=TEXT_COLOR, font=("Segoe UI", 10))
        style.map("TCheckbutton", background=[('active', PANEL_COLOR)])
        style.configure("TLabelframe", background=PANEL_COLOR, foreground=TEXT_COLOR)
        style.configure("TLabelframe.Label", background=PANEL_COLOR, foreground=ACCENT_COLOR, font=("Segoe UI", 10, "bold"))
        self.root.option_add('*TCombobox*Listbox.background', LIST_BG)
        self.root.option_add('*TCombobox*Listbox.foreground', 'white')

    def create_layout(self):
        self.left_panel = tk.Frame(self.root, bg=BG_COLOR)
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.fig = plt.Figure(figsize=(10, 8), dpi=100, facecolor=BG_COLOR)
        gs = self.fig.add_gridspec(2, 2, height_ratios=[1, 1])
        
        self.ax_graph = self.fig.add_subplot(gs[0, :])
        self.ax_roi = self.fig.add_subplot(gs[1, 0])
        self.ax_bin = self.fig.add_subplot(gs[1, 1])
        
        divider = make_axes_locatable(self.ax_roi)
        self.cax = divider.append_axes("right", size="5%", pad=0.05)
        
        for ax in [self.ax_graph, self.ax_roi, self.ax_bin]:
            ax.set_facecolor(BG_COLOR)
            ax.tick_params(colors='white')
            for spine in ax.spines.values(): spine.set_color('white')
            ax.xaxis.label.set_color('white')
            ax.yaxis.label.set_color('white')
            ax.title.set_color('white')
        
        self.cax.tick_params(colors='white')
        for spine in self.cax.spines.values(): spine.set_color('white')

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.left_panel)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # [MODIFIED] Scrollable right panel
        # 외부 컨테이너
        right_container = tk.Frame(self.root, bg=PANEL_COLOR, width=400)
        right_container.pack(side=tk.RIGHT, fill=tk.Y)
        right_container.pack_propagate(False)

        # Canvas + Scrollbar
        right_canvas = tk.Canvas(right_container, bg=PANEL_COLOR, highlightthickness=0, width=380)
        right_scroll = tk.Scrollbar(right_container, orient=tk.VERTICAL, command=right_canvas.yview)
        right_canvas.configure(yscrollcommand=right_scroll.set)

        right_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        right_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 실제 위젯들을 담을 내부 프레임 (기존 self.right_panel 대체)
        self.right_panel = tk.Frame(right_canvas, bg=PANEL_COLOR)
        right_window = right_canvas.create_window((0, 0), window=self.right_panel, anchor='nw')

        # 내부 프레임 크기 변화에 따라 scrollregion 자동 업데이트
        def _on_inner_configure(event):
            right_canvas.configure(scrollregion=right_canvas.bbox("all"))
        self.right_panel.bind("<Configure>", _on_inner_configure)

        # Canvas 리사이즈 시 내부 프레임 폭 맞추기
        def _on_canvas_configure(event):
            right_canvas.itemconfig(right_window, width=event.width)
        right_canvas.bind("<Configure>", _on_canvas_configure)

        # 마우스 휠 스크롤 바인딩 (Windows/Mac/Linux 대응)
        def _on_mousewheel(event):
            # Windows/Mac: event.delta 사용
            if event.delta:
                right_canvas.yview_scroll(int(-event.delta / 120), "units")
            else:
                # Linux: Button-4/5
                right_canvas.yview_scroll(-1 if event.num == 4 else 1, "units")

        def _bind_wheel(_):
            right_canvas.bind_all("<MouseWheel>", _on_mousewheel)
            right_canvas.bind_all("<Button-4>", _on_mousewheel)
            right_canvas.bind_all("<Button-5>", _on_mousewheel)

        def _unbind_wheel(_):
            right_canvas.unbind_all("<MouseWheel>")
            right_canvas.unbind_all("<Button-4>")
            right_canvas.unbind_all("<Button-5>")

        # 커서가 패널 위에 있을 때만 휠 스크롤 작동 (그래프 영역에서 방해되지 않도록)
        right_canvas.bind("<Enter>", _bind_wheel)
        right_canvas.bind("<Leave>", _unbind_wheel)
        self.right_panel.bind("<Enter>", _bind_wheel)
        self.right_panel.bind("<Leave>", _unbind_wheel)
        
        # File
        frame_file = ttk.LabelFrame(self.right_panel, text=" File Operations ", padding=10)
        frame_file.pack(fill=tk.X, padx=10, pady=5)
        self.lbl_filename = ttk.Label(frame_file, text="No file loaded", anchor="center")
        self.lbl_filename.pack(fill=tk.X, pady=(0, 5))
        
        frame_resets = ttk.Frame(frame_file)
        frame_resets.pack(fill=tk.X, pady=5)
        ttk.Checkbutton(frame_resets, text="Reset Points", variable=self.chk_reset_pts).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(frame_resets, text="Reset ROI", variable=self.chk_reset_roi).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(frame_file, text="📂 Load New File", command=self.load_new_file).pack(fill=tk.X, pady=5)

        # Params
        frame_param = ttk.LabelFrame(self.right_panel, text=" Parameters ", padding=10)
        frame_param.pack(fill=tk.X, padx=10, pady=5)
        self.create_entry(frame_param, "Trigger Temp:", self.var_trig, 0)
        self.create_entry(frame_param, "Start Temp:", self.var_start, 1)
        self.create_entry(frame_param, "End Temp:", self.var_end, 2)
        self.create_entry(frame_param, "Step Size:", self.var_step, 3)

        # [NEW] Noise Filter Parameters
        frame_filter = ttk.LabelFrame(self.right_panel, text=" Noise Filter Parameters ", padding=10)
        frame_filter.pack(fill=tk.X, padx=10, pady=5)
        self.create_entry(frame_filter, "Adapt. Block Size (odd):", self.var_adapt_block, 0)
        self.create_entry(frame_filter, "Adapt. C (bias):", self.var_adapt_C, 1)
        self.create_entry(frame_filter, "Resize Target (NxN):", self.var_resize_size, 2)
        self.create_entry(frame_filter, "DCT Crop Range:", self.var_dct_crop, 3)
        self.create_entry(frame_filter, "Frame Avg (1~5):", self.var_frame_avg, 4)
        ttk.Checkbutton(
            frame_filter,
            text="Apply DCT sign quantize (dct > 0)",
            variable=self.chk_dct_sign,
            command=self.update_plots
        ).grid(row=5, column=0, columnspan=2, sticky='w', pady=(4, 0))

        # Vis
        frame_vis = ttk.LabelFrame(self.right_panel, text=" Visualization (Preview Only) ", padding=10)
        frame_vis.pack(fill=tk.X, padx=10, pady=5)
        self.create_entry(frame_vis, "Min Temp:", self.var_vmin, 0)
        self.create_entry(frame_vis, "Max Temp:", self.var_vmax, 1)
        
        ttk.Label(frame_vis, text="Colormap:").grid(row=2, column=0, sticky='w', pady=2)
        self.cb_cmap = ttk.Combobox(frame_vis, textvariable=self.var_cmap, state="readonly", 
                                    values=["jet", "inferno", "plasma", "magma", "viridis", "gray", "hot", "cool"])
        self.cb_cmap.grid(row=2, column=1, sticky='ew', pady=2, padx=5)
        self.cb_cmap.bind("<<ComboboxSelected>>", lambda e: self.update_plots())

        # List
        frame_list = ttk.LabelFrame(self.right_panel, text=" Preview Ranges (Use Arrows) ", padding=10)
        frame_list.pack(fill=tk.X, padx=10, pady=5)
        
        list_scroll = tk.Scrollbar(frame_list, orient=tk.VERTICAL)
        self.list_ranges = tk.Listbox(frame_list, bg=LIST_BG, fg="white", 
                                      selectbackground=ACCENT_COLOR, 
                                      selectforeground="white",
                                      activestyle="none",
                                      yscrollcommand=list_scroll.set,
                                      font=("Consolas", 10), height=5, bd=0)
        list_scroll.config(command=self.list_ranges.yview)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.list_ranges.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.list_ranges.bind('<<ListboxSelect>>', self.on_range_select)
        self.list_ranges.bind('<Up>', self.move_selection_up)
        self.list_ranges.bind('<Down>', self.move_selection_down)

        # Save Options
        frame_opt = ttk.LabelFrame(self.right_panel, text=" Save Options ", padding=10)
        frame_opt.pack(fill=tk.X, padx=10, pady=5)
        ttk.Checkbutton(frame_opt, text="Save Thermal ROI (.png)", variable=self.chk_thermal).pack(anchor='w')
        ttk.Checkbutton(frame_opt, text="Save Binary Image (.png)", variable=self.chk_binary).pack(anchor='w')
        ttk.Checkbutton(frame_opt, text="Save Bit Image (XOR) (.png)", variable=self.chk_bit).pack(anchor='w')
        ttk.Checkbutton(frame_opt, text="Save Excel Data (.xlsx)", variable=self.chk_excel).pack(anchor='w')

        # Run (스크롤 영역 안에서는 side=BOTTOM 대신 자연스럽게 쌓이도록)
        frame_run = ttk.Frame(self.right_panel)
        frame_run.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(frame_run, text="🚀 Run Macro & Save", command=self.run_macro).pack(fill=tk.X, ipady=8)

        ttk.Button(frame_run, text="Batch Save Points/ROI", command=self.run_batch_point_setup).pack(fill=tk.X, pady=(8, 0), ipady=8)
        ttk.Button(frame_run, text="Batch Run All Samples", command=self.run_batch_macro).pack(fill=tk.X, pady=(8, 0), ipady=8)

        # 바닥 여유 공간 (마지막 버튼이 스크롤 끝에 딱 붙지 않게)
        tk.Frame(self.right_panel, bg=PANEL_COLOR, height=20).pack(fill=tk.X)

    def create_entry(self, parent, label_text, variable, row):
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky='w', pady=2)
        entry = tk.Entry(parent, textvariable=variable, bg=ENTRY_BG, fg="white", insertbackground="white", relief="flat")
        entry.grid(row=row, column=1, sticky='ew', pady=2, padx=5)
        parent.columnconfigure(1, weight=1)
        entry.bind('<Return>', lambda e: self.update_plots())
        entry.bind('<FocusOut>', lambda e: self.update_plots())

    def strip_generated_suffixes(self, stem):
        for suffix in ('_new', '_reduced'):
            if stem.lower().endswith(suffix):
                stem = stem[:-len(suffix)]
        return stem

    def strip_repeat_suffix(self, stem):
        return re.sub(r'(?:[ _-])\d+$', '', stem)

    def is_long_term_name(self, stem):
        return re.search(r'(^|[_ -])long[_ -]?term($|[_ -])', stem, re.IGNORECASE) is not None

    def get_point_group_name(self, file_path):
        stem = os.path.splitext(os.path.basename(file_path))[0]
        stem = self.strip_repeat_suffix(self.strip_generated_suffixes(stem))
        if self.is_long_term_name(stem):
            return "Longterm"
        return stem

    def get_point_group_key(self, file_path):
        return os.path.join(os.path.dirname(file_path).lower(), self.get_point_group_name(file_path).lower())

    def get_points_path(self, file_path):
        group_name = self.get_point_group_name(file_path)
        return os.path.join(os.path.dirname(file_path), f"{group_name}_points.mat")

    def get_group_roi_path(self, file_path):
        group_name = self.get_point_group_name(file_path)
        return os.path.join(os.path.dirname(file_path), f"{group_name}_roi.mat")

    def get_common_roi_path(self, file_path):
        return os.path.join(os.path.dirname(file_path), "common_roi.mat")

    def is_target_mat_file(self, file_path):
        return os.path.basename(file_path).lower().endswith("_new.mat")

    def filter_target_mat_files(self, file_paths):
        return [file_path for file_path in file_paths if self.is_target_mat_file(file_path)]

    def get_roi_side(self, roi_coords):
        x1, x2, y1, y2 = [int(v) for v in np.asarray(roi_coords).flatten()]
        return min(abs(x2 - x1), abs(y2 - y1))

    def prepare_file_context(self, file_path):
        self.mat_path = file_path
        self.file_dir = os.path.dirname(file_path)
        self.base_name = os.path.splitext(os.path.basename(file_path))[0].replace('_new', '').replace('_reduced', '')
        self.group_name = self.get_point_group_name(file_path)
        self.lbl_filename.config(text=os.path.basename(file_path))
        self.roi_coords = None
        self.im_roi_obj = None
        self.ax_graph.clear()
        self.ax_roi.clear()
        self.ax_bin.clear()
        self.load_data_logic()

    def get_batch_setup_label(self):
        if self.point_setup_mode and self.point_setup_queue and 0 <= self.point_setup_index < len(self.point_setup_queue):
            return f"[Setup {self.point_setup_index + 1}/{len(self.point_setup_queue)}] "
        return ""

    def start_next_point_setup_item(self):
        if not self.point_setup_queue:
            self.point_setup_mode = False
            return

        self.point_setup_index += 1
        if self.point_setup_index >= len(self.point_setup_queue):
            self.point_setup_mode = False
            self.lbl_filename.config(text="Batch point setup complete")
            messagebox.showinfo(
                "Batch Point Setup Complete",
                "All selected groups now have shared point files.\n\nUse 'Batch Run All Samples' when you want to process the full dataset."
            )
            return

        file_path = self.point_setup_queue[self.point_setup_index]
        self.prepare_file_context(file_path)
        self.lbl_filename.config(text=f"{self.get_batch_setup_label()}{os.path.basename(file_path)}")
        self.select_points_popup()

    def finish_current_point_setup_and_continue(self):
        if self.point_setup_mode:
            self.root.after(50, self.start_next_point_setup_item)

    def move_selection_up(self, event):
        selection = self.list_ranges.curselection()
        if not selection: 
            return
        current_idx = selection[0]
        if current_idx > 0:
            new_idx = current_idx - 1
            self.list_ranges.selection_clear(0, tk.END)
            self.list_ranges.selection_set(new_idx)
            self.list_ranges.activate(new_idx)
            self.list_ranges.see(new_idx)
            self.on_range_select(None)
        return "break"

    def move_selection_down(self, event):
        selection = self.list_ranges.curselection()
        if not selection: 
            if self.list_ranges.size() > 0:
                self.list_ranges.selection_set(0)
                self.on_range_select(None)
            return
        current_idx = selection[0]
        if current_idx < self.list_ranges.size() - 1:
            new_idx = current_idx + 1
            self.list_ranges.selection_clear(0, tk.END)
            self.list_ranges.selection_set(new_idx)
            self.list_ranges.activate(new_idx)
            self.list_ranges.see(new_idx)
            self.on_range_select(None)
        return "break"

    def load_new_file(self):
        file_path = filedialog.askopenfilename(
            title="Select _new.mat file",
            initialdir=self.script_dir,
            filetypes=[("New MAT files", "*_new.mat")]
        )
        if not file_path:
            return
        if not self.is_target_mat_file(file_path):
            messagebox.showwarning("Invalid File", "Only *_new.mat files can be selected.")
            return

        self.point_setup_mode = False
        self.point_setup_queue = []
        self.point_setup_index = -1
        self.prepare_file_context(file_path)
        self.select_points_popup() 

    def load_data_logic(self):
        self.seed_rand2 = SEED_RAND2
        try:
            mat = sio.loadmat(self.mat_path)
            if 'images' in mat: self.full_data = mat['images']
            elif 'temperature_frames' in mat: self.full_data = mat['temperature_frames']
            self.num_frames = self.full_data.shape[0]
            frame_means = np.mean(self.full_data, axis=(1, 2))
            self.start_frame_idx = int(np.argmin(frame_means))
        except Exception as e:
            messagebox.showerror("Error", f"Load failed: {e}")

    def select_points_popup(self):
        reset_pts = self.chk_reset_pts.get()
        pts_path = self.get_points_path(self.mat_path)

        if not reset_pts and os.path.exists(pts_path):
            try:
                self.points = sio.loadmat(pts_path)['points']
                print(f">> [Points] Loaded from {pts_path}")
                self.select_roi_popup()
                return
            except: pass

        self.temp_points = []
        initial_frame = self.start_frame_idx if self.start_frame_idx < self.num_frames else 0
        
        fig = plt.figure(figsize=(10, 8))
        plt.subplots_adjust(bottom=0.2)
        
        ax_img = fig.add_subplot(111)
        img_obj = ax_img.imshow(self.full_data[initial_frame], cmap='jet')
        ax_img.set_title(f"Select 3 Points (Frame {initial_frame})\nUse Slider to find best view -> Click 3 times", fontsize=11)
        ax_img.axis('off')

        ax_slider = plt.axes([0.2, 0.05, 0.6, 0.03])
        slider = Slider(ax_slider, 'Frame', 0, self.num_frames-1, valinit=initial_frame, valstep=1)

        def update_slider(val):
            idx = int(slider.val)
            current_frame = self.full_data[idx]
            img_obj.set_data(current_frame)
            vmin_new = np.min(current_frame)
            vmax_new = np.max(current_frame)
            img_obj.set_clim(vmin_new, vmax_new)
            ax_img.set_title(f"Select 3 Points (Frame {idx})\nRange: {vmin_new:.1f}~{vmax_new:.1f}", fontsize=11)
            fig.canvas.draw_idle()
        
        slider.on_changed(update_slider)

        def onclick(event):
            if event.inaxes != ax_img: return
            if event.button != 1: return 
            self.temp_points.append([event.xdata, event.ydata])
            ax_img.plot(event.xdata, event.ydata, 'rx', markersize=10, markeredgewidth=2)
            fig.canvas.draw_idle()
            if len(self.temp_points) >= 3:
                plt.close(fig)

        fig.canvas.mpl_connect('button_press_event', onclick)
        self.slider_obj = slider 
        plt.show() 

        if len(self.temp_points) == 3:
            self.points = np.array(self.temp_points)
            sio.savemat(pts_path, {'points': self.points})
            self.select_roi_popup()
        else:
            if self.point_setup_mode:
                self.point_setup_mode = False
                messagebox.showwarning("Batch Point Setup Stopped", "Point selection was cancelled or incomplete.")
            else:
                messagebox.showinfo("Info", "Selection cancelled or incomplete.")

    def select_roi_popup(self):
        reset_roi = self.chk_reset_roi.get()
        common_roi_path = self.get_common_roi_path(self.mat_path)
        group_roi_path = self.get_group_roi_path(self.mat_path)
        template_side = None

        if os.path.exists(common_roi_path):
            try:
                data = sio.loadmat(common_roi_path)
                template_side = self.get_roi_side(data['roi'][0])
            except:
                template_side = None

        if not reset_roi and os.path.exists(group_roi_path):
            try:
                data = sio.loadmat(group_roi_path)
                self.roi_coords = data['roi'][0]
                print(f">> [Group ROI] Loaded from {group_roi_path}")
                self.init_dashboard_data()
                self.finish_current_point_setup_and_continue()
                return
            except:
                pass

        frame_idx = self.start_frame_idx if self.start_frame_idx < self.num_frames else 0
        sample = self.full_data[frame_idx]
        h_img, w_img = sample.shape
        
        fig_roi, ax = plt.subplots(figsize=(10, 6))
        ax.imshow(sample, cmap='jet')
        ax.plot(self.points[:, 0], self.points[:, 1], 'rx')
        if template_side is not None:
            ax.set_title(
                f"Draw ROI center -> Fixed square size {template_side}px -> Close",
                fontsize=11, color='blue'
            )
        else:
            ax.set_title("Draw ROI -> Snaps to SQUARE on release -> Close", fontsize=11, color='blue')
        ax.axis('off')
        
        def on_select(eclick, erelease):
            x1, y1 = int(eclick.xdata), int(eclick.ydata)
            x2, y2 = int(erelease.xdata), int(erelease.ydata)
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            w, h = abs(x2 - x1), abs(y2 - y1)
            side = int(template_side) if template_side is not None else max(w, h)
            half = side // 2
            nx1, nx2 = cx - half, cx + half
            ny1, ny2 = cy - half, cy + half
            if nx1 < 0: 
                nx2 += abs(nx1); nx1 = 0
            if ny1 < 0: 
                ny2 += abs(ny1); ny1 = 0
            if nx2 > w_img: 
                nx1 -= (nx2 - w_img); nx2 = w_img
            if ny2 > h_img: 
                ny1 -= (ny2 - h_img); ny2 = h_img
            nx1 = max(0, nx1); ny1 = max(0, ny1)
            final_side = min(nx2 - nx1, ny2 - ny1) 
            xmin, xmax = nx1, nx1 + final_side
            ymin, ymax = ny1, ny1 + final_side
            self.roi_coords = [int(xmin), int(xmax), int(ymin), int(ymax)]
            self.rect_selector.extents = (xmin, xmax, ymin, ymax)
            fig_roi.canvas.draw_idle()
            print(f">> ROI Snapped to Square: {self.roi_coords}")

        self.rect_selector = RectangleSelector(ax, on_select, useblit=True, button=[1], interactive=True)
        plt.show()
        
        if self.roi_coords is None:
            min_side = int(template_side) if template_side is not None else min(w_img, h_img)
            self.roi_coords = [0, min_side, 0, min_side]

        sio.savemat(group_roi_path, {'roi': self.roi_coords})
        if template_side is None or reset_roi:
            sio.savemat(common_roi_path, {'roi': self.roi_coords})
        self.init_dashboard_data()
        self.finish_current_point_setup_and_continue()

    def init_dashboard_data(self):
        xs = np.clip(self.points[:, 0].astype(int), 0, self.full_data.shape[2]-1)
        ys = np.clip(self.points[:, 1].astype(int), 0, self.full_data.shape[1]-1)
        self.temp_history = np.mean(self.full_data[:, ys, xs], axis=1)
        self.start_frame_idx = int(np.argmin(self.temp_history))
        self.update_plots()

    def on_range_select(self, event):
        self.list_ranges.focus_set()
        selection = self.list_ranges.curselection()
        if not selection: return
        index = selection[0]
        try:
            start_t = float(self.var_start.get())
            step_t = float(self.var_step.get())
        except: return
        curr_min = start_t + (index * step_t)
        curr_max = curr_min + step_t
        self.var_vmin.set(f"{curr_min:.1f}")
        self.var_vmax.set(f"{curr_max:.1f}")
        self.update_plots()

    # [NEW] 필터 파라미터 안전하게 가져오기
    def get_filter_params(self):
        """Returns (block_size, C, resize_size, frame_avg) with validation."""
        try:
            block_size = int(self.var_adapt_block.get())
        except:
            block_size = 21
        # block_size는 홀수 & >= 3 이어야 함
        if block_size < 3:
            block_size = 3
        if block_size % 2 == 0:
            block_size += 1

        try:
            C_val = float(self.var_adapt_C.get())
        except:
            C_val = 2.0

        try:
            resize_size = int(self.var_resize_size.get())
        except:
            resize_size = 64
        if resize_size < 32:
            resize_size = 32  # DCT crop이 32x32이므로 최소 32 이상 필요

        # [NEW] Frame averaging count (1~5)
        try:
            frame_avg = int(self.var_frame_avg.get())
        except:
            frame_avg = 1
        if frame_avg < 1:
            frame_avg = 1
        if frame_avg > 5:
            frame_avg = 5

        return block_size, C_val, resize_size, frame_avg

    # [NEW] trigger 주변 N프레임 평균 ROI 계산
    def get_averaged_roi(self, trigger_idx, frame_avg):
        """trigger_idx 중심으로 frame_avg 장을 평균낸 ROI 이미지 반환."""
        x1, x2, y1, y2 = self.roi_coords
        if frame_avg <= 1:
            return self.full_data[trigger_idx][y1:y2, x1:x2]

        # 중심 대칭으로 범위 잡되, 경계 클램프
        half = frame_avg // 2
        s = max(0, trigger_idx - half)
        e = min(self.num_frames, s + frame_avg)
        # 끝에서 모자라면 시작을 앞당겨 정확히 frame_avg 장 확보 시도
        s = max(0, e - frame_avg)

        stack = self.full_data[s:e, y1:y2, x1:x2]
        return np.mean(stack, axis=0)

    def update_plots(self, event=None):
        if self.temp_history is None: return
        try:
            trig = float(self.var_trig.get())
            start_t = float(self.var_start.get())
            end_t = float(self.var_end.get())
            step_t = float(self.var_step.get())
            vmin = float(self.var_vmin.get())
            vmax = float(self.var_vmax.get())
            if vmin >= vmax: vmax = vmin + 1.0 
            cmap_name = self.var_cmap.get()
        except: return

        saved_sel = self.list_ranges.curselection()
        
        self.list_ranges.delete(0, tk.END)
        curr = start_t
        idx = 1
        while curr < end_t:
            c_max = round(curr + step_t, 2)
            c = round(curr, 2)
            self.list_ranges.insert(tk.END, f" {idx:02d}. {c:.1f} ~ {c_max:.1f} °C")
            curr += step_t
            idx += 1
            
        if saved_sel:
            self.list_ranges.selection_set(saved_sel)
            self.list_ranges.activate(saved_sel)
        
        # Graph
        start_frame_idx = int(np.argmin(self.temp_history))
        self.start_frame_idx = start_frame_idx
        valid_indices = np.where((self.temp_history >= trig) & (np.arange(self.num_frames) >= start_frame_idx))[0]
        
        if len(valid_indices) > 0:
            self.trigger_idx = valid_indices[0]
            status_txt = (
                f"Triggered: Frame {self.trigger_idx} "
                f"({self.temp_history[self.trigger_idx]:.1f}C), Start Frame {start_frame_idx}"
            )
        else:
            self.trigger_idx = self.num_frames - 1
            status_txt = f"Not Triggered (Start Frame {start_frame_idx})"

        self.ax_graph.clear()
        self.ax_graph.plot(self.temp_history, label='Avg Temp', color='#00ffcc')
        self.ax_graph.axhline(y=trig, color='r', linestyle='--', label='Trigger')
        self.ax_graph.axvspan(0, start_frame_idx, color='gray', alpha=0.3)
        self.ax_graph.plot(
            start_frame_idx,
            self.temp_history[start_frame_idx],
            'yo',
            markersize=6,
            label='Start (Min Temp)'
        )
        if len(valid_indices) > 0:
            self.ax_graph.plot(self.trigger_idx, self.temp_history[self.trigger_idx], 'ro')
        
        self.ax_graph.set_title(f"Temperature Profile: {status_txt}", color='white')
        self.ax_graph.legend(facecolor=PANEL_COLOR, labelcolor='white')
        self.ax_graph.grid(True, alpha=0.2, color='white')

        # Thermal ROI (with frame averaging)
        block_size, C_val, _, frame_avg = self.get_filter_params()
        x1, x2, y1, y2 = self.roi_coords
        self.roi_img = self.get_averaged_roi(self.trigger_idx, frame_avg)

        if self.im_roi_obj is None:
            self.im_roi_obj = self.ax_roi.imshow(self.roi_img, cmap=cmap_name, vmin=vmin, vmax=vmax)
            self.ax_roi.axis('off')
            self.cbar = self.fig.colorbar(self.im_roi_obj, cax=self.cax)
            self.cbar.ax.yaxis.set_tick_params(color='white')
            plt.setp(plt.getp(self.cbar.ax.axes, 'yticklabels'), color='white')
        else:
            self.im_roi_obj.set_data(self.roi_img)
            self.im_roi_obj.set_clim(vmin, vmax)
            self.im_roi_obj.set_cmap(cmap_name)
            self.cbar.update_normal(self.im_roi_obj)

        avg_tag = f" [avg={frame_avg}]" if frame_avg > 1 else ""
        self.ax_roi.set_title(f"Thermal ROI ({vmin:.1f}~{vmax:.1f}C){avg_tag}", color='white')

        # Binary with current filter params
        binary = self.get_binary(self.roi_img, vmin, vmax, block_size, C_val)
        self.ax_bin.clear()
        self.ax_bin.imshow(binary, cmap='gray')
        sign_tag = "sign" if self.chk_dct_sign.get() else "raw"
        self.ax_bin.set_title(f"Preview Binary (blk={block_size}, C={C_val}, {sign_tag})", color='white')
        self.ax_bin.axis('off')
        
        self.canvas.draw()

    # [MODIFIED] block_size, C를 파라미터로 받도록 변경
    def get_binary(self, img, min_c, max_c, block_size=21, C_val=2):
        cp = img.copy()
        cp[cp < min_c] = min_c
        cp[cp > max_c] = min_c
        
        mn, mx = np.min(cp), np.max(cp)
        if mx - mn == 0: norm = np.zeros_like(cp)
        else: norm = (cp - mn) / (mx - mn)
        
        inv = 1.0 - norm
        u8 = (inv * 255).astype(np.uint8)
        return cv2.adaptiveThreshold(u8, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, int(block_size), float(C_val))

    # [MODIFIED] resize_size, use_sign을 파라미터로 받도록 변경
    def parse_dct_crop(self, crop_spec, size):
        """
        Parse user-facing 1-based inclusive DCT crop ranges.

        Accepted:
          2:33      -> rows 2:33 and cols 2:33
          2:33,4:35 -> rows 2:33 and cols 4:35
          2-33      -> same as 2:33

        Returns Python slices as (row_start, row_stop, col_start, col_stop).
        The selected area must be exactly 32x32.
        """
        spec = str(crop_spec or "2:33").strip()
        if not spec:
            spec = "2:33"

        parts = [p.strip() for p in re.split(r"[,;]", spec) if p.strip()]
        if len(parts) == 1:
            row_part = col_part = parts[0]
        elif len(parts) == 2:
            row_part, col_part = parts
        else:
            raise ValueError("DCT Crop Range must be like 2:33 or 2:33,2:33")

        def parse_part(part):
            match = re.fullmatch(r"\s*(\d+)\s*[:-]\s*(\d+)\s*", part)
            if not match:
                raise ValueError("DCT Crop Range must be like 2:33 or 2:33,2:33")
            start_1 = int(match.group(1))
            end_1 = int(match.group(2))
            if start_1 < 1 or end_1 < start_1:
                raise ValueError("DCT Crop Range must use 1-based increasing indices")
            if (end_1 - start_1 + 1) != 32:
                raise ValueError("DCT Crop Range must select exactly 32 values, e.g. 2:33")
            if end_1 > size:
                raise ValueError(f"DCT Crop Range {start_1}:{end_1} exceeds DCT size {size}")
            return start_1 - 1, end_1

        row_start, row_stop = parse_part(row_part)
        col_start, col_stop = parse_part(col_part)
        return row_start, row_stop, col_start, col_stop

    def process_dct(self, binary, resize_size=64, use_sign=True, crop_spec="2:33"):
        """
        use_sign=True  : 기존 동작. (dct > 0).astype(int) 부호 양자화.
        use_sign=False : 부호 양자화 생략. 계수의 중앙값 기준 이진화로 대체
                        (0 근처 flip 문제를 줄이고 정보량을 유지).
        """
        img_f = binary.astype(float) / 255.0
        img_64 = cv2.resize(img_f, (int(resize_size), int(resize_size)), interpolation=cv2.INTER_AREA)
        dct_v = dctn(img_64, type=2, norm='ortho')

        if use_sign:
            quant = (dct_v > 0).astype(int)
        else:
            # DC 성분은 항상 크므로 제외하고 나머지의 절대값 중앙값 기준 이진화
            mag = np.abs(dct_v)
            mag_flat = mag.copy()
            mag_flat[0, 0] = 0  # DC 제외
            thr = np.median(mag_flat[mag_flat > 0]) if np.any(mag_flat > 0) else 0.0
            quant = (mag > thr).astype(int)

        row_start, row_stop, col_start, col_stop = self.parse_dct_crop(crop_spec, quant.shape[0])
        cropped = quant[row_start:row_stop, col_start:col_stop]
        seed = self.seed_rand2
        if seed.shape != (32, 32):
            seed = cv2.resize(seed, (32, 32), interpolation=cv2.INTER_NEAREST)

        return np.bitwise_xor(cropped.astype(int), seed.astype(int))

    def generate_outputs_for_current_file(self):
        start_v = float(self.var_start.get())
        end_v = float(self.var_end.get())
        step_v = float(self.var_step.get())
        trig_v = float(self.var_trig.get())
        cmap_name = self.var_cmap.get()

        if end_v >= trig_v:
            raise ValueError("End Temp must be lower than Trigger Temp!")
        if start_v >= end_v:
            raise ValueError("Start Temp must be lower than End Temp.")

        # 필터 파라미터
        block_size, C_val, resize_size, frame_avg = self.get_filter_params()
        use_sign = self.chk_dct_sign.get()
        crop_spec = self.var_dct_crop.get()

        self.init_dashboard_data()
        # [NEW] trigger 주변 N프레임 평균 ROI (update_plots와 일관)
        self.roi_img = self.get_averaged_roi(self.trigger_idx, frame_avg)

        folder_name = f"{self.base_name}_{trig_v}"
        save_dir = os.path.join(self.file_dir, folder_name)
        os.makedirs(save_dir, exist_ok=True)

        excel_data = {}
        curr = start_v
        idx = 1

        do_bin = self.chk_binary.get()
        do_bit = self.chk_bit.get()
        do_excel = self.chk_excel.get()
        do_thermal = self.chk_thermal.get()

        if do_thermal:
            thermal_path = os.path.join(save_dir, "Reference_Thermal.png")
            plt.imsave(thermal_path, self.roi_img, cmap=cmap_name, vmin=start_v, vmax=end_v)

        while curr < end_v:
            curr_max = round(curr + step_v, 2)
            curr = round(curr, 2)
            range_name = f"R{idx}_{curr}-{curr_max}"

            binary = self.get_binary(self.roi_img, curr, curr_max, block_size, C_val)
            bits = self.process_dct(binary, resize_size, use_sign, crop_spec)

            if do_bin:
                imwrite_safe(os.path.join(save_dir, f"{range_name}_bin.png"), binary)
            if do_bit:
                big_bits = cv2.resize((bits * 255).astype(np.uint8), None, fx=10, fy=10, interpolation=cv2.INTER_NEAREST)
                imwrite_safe(os.path.join(save_dir, f"{range_name}_bits.png"), big_bits)
            if do_thermal:
                plt.imsave(os.path.join(save_dir, f"{range_name}_thermal.png"), self.roi_img, cmap=cmap_name, vmin=curr, vmax=curr_max)
            if do_excel:
                excel_data[range_name] = bits.flatten()

            curr += step_v
            idx += 1

        if do_excel and excel_data:
            headers = list(excel_data.keys())
            workbook = Workbook()
            worksheet = workbook.active
            worksheet.title = "ThermalBits"
            worksheet.append(headers)

            column_data = [np.asarray(excel_data[header]).flatten().tolist() for header in headers]
            for row_values in zip(*column_data):
                worksheet.append(list(row_values))

            excel_name = f"{self.base_name}_{trig_v}_{start_v}_{end_v}_{step_v}.xlsx"
            workbook.save(os.path.join(save_dir, excel_name))

        return save_dir

    def run_batch_point_setup(self):
        file_paths = filedialog.askopenfilenames(
            title="Select _new.mat file(s) for point setup",
            initialdir=self.script_dir,
            filetypes=[("New MAT files", "*_new.mat")]
        )
        if not file_paths:
            return
        file_paths = self.filter_target_mat_files(file_paths)
        if not file_paths:
            messagebox.showwarning("Invalid Files", "Only *_new.mat files can be selected.")
            return

        unique_group_files = []
        seen_groups = set()
        for file_path in file_paths:
            group_key = self.get_point_group_key(file_path)
            if group_key in seen_groups:
                continue
            seen_groups.add(group_key)
            unique_group_files.append(file_path)

        self.point_setup_queue = unique_group_files
        self.point_setup_index = -1
        self.point_setup_mode = True
        self.start_next_point_setup_item()

    def run_batch_macro(self):
        file_paths = filedialog.askopenfilenames(
            title="Select _new.mat file(s) for batch run",
            initialdir=self.script_dir,
            filetypes=[("New MAT files", "*_new.mat")]
        )
        if not file_paths:
            return
        file_paths = self.filter_target_mat_files(file_paths)
        if not file_paths:
            messagebox.showwarning("Invalid Files", "Only *_new.mat files can be selected.")
            return

        common_roi_path = None
        success = []
        failed = []

        for idx, file_path in enumerate(file_paths, start=1):
            try:
                self.prepare_file_context(file_path)
                pts_path = self.get_points_path(file_path)
                group_roi_path = self.get_group_roi_path(file_path)
                common_roi_path = self.get_common_roi_path(file_path)

                if not os.path.exists(pts_path):
                    raise ValueError(f"Missing shared points file: {os.path.basename(pts_path)}")

                self.points = sio.loadmat(pts_path)['points']
                if os.path.exists(group_roi_path):
                    self.roi_coords = sio.loadmat(group_roi_path)['roi'][0]
                elif os.path.exists(common_roi_path):
                    self.roi_coords = sio.loadmat(common_roi_path)['roi'][0]
                else:
                    raise ValueError(
                        f"Missing ROI file: {os.path.basename(group_roi_path)} "
                        f"(or fallback {os.path.basename(common_roi_path)})"
                    )
                self.root.update_idletasks()

                save_dir = self.generate_outputs_for_current_file()
                success.append(os.path.basename(file_path))
                self.lbl_filename.config(text=f"[Batch {idx}/{len(file_paths)}] {os.path.basename(file_path)}")
                print(f">> Batch processed: {file_path} -> {save_dir}")
            except Exception as e:
                failed.append(f"{os.path.basename(file_path)}: {e}")

        if success:
            self.lbl_filename.config(text=f"Batch complete: {len(success)}/{len(file_paths)}")
        if failed:
            messagebox.showwarning(
                "Batch Complete",
                f"Processed {len(success)}/{len(file_paths)} files.\n\n" + "\n".join(failed[:10])
            )
        else:
            messagebox.showinfo("Batch Complete", f"Processed all {len(success)} files successfully.")

    def run_macro(self):
        try:
            save_dir = self.generate_outputs_for_current_file()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        messagebox.showinfo("Success", f"All done!\nSaved in:\n{os.path.basename(save_dir)}")

if __name__ == "__main__":
    ModernThermalGUI()
