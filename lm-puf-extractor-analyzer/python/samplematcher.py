import scipy.io as sio
import os
import re
import numpy as np
import cv2
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# --- 스타일 설정 ---
BG_COLOR = "#2e2e2e"       
PANEL_COLOR = "#3c3f41"    
TEXT_COLOR = "#ffffff"     
ACCENT_COLOR = "#3a96dd"   # 파란색 (일반 버튼)
ACTION_COLOR = "#e67e22"   # 주황색 (계산 버튼)
SUCCESS_COLOR = "#27ae60"  # 녹색 (완료/저장)
STOP_COLOR = "#c0392b"     # 빨간색 (중지)
ENTRY_BG = "#45494a"       

class ModernPerspectiveGUI:
    def __init__(self):
        # 1. 메인 윈도우 설정
        self.root = tk.Tk()
        self.root.title("Perspective Correction Pro (Auto-Snap Points)")
        self.root.geometry("1400x950")
        self.root.configure(bg=BG_COLOR)
        
        self.setup_style()
        
        # 데이터 변수
        self.mat_path = None
        self.full_images = None
        self.current_frame = None
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.file_dir = self.script_dir
        self.file_name = None
        self.file_queue = []
        self.current_file_index = -1
        
        self.manual_points = [] 
        self.is_positioning_mode = False 
        self.selected_point_idx = None
        
        # 시각화 객체
        self.fig = None
        self.ax = None
        self.canvas = None
        self.img_obj = None
        self.scatter_manual = None
        self.scatter_selected = None
        self.line_manual = None
        self.zoom_ax = None
        self.zoom_img_obj = None
        self.zoom_marker = None
        self.zoom_hline = None
        self.zoom_vline = None
        self.zoom_radius = 20
        
        # Tkinter 변수
        self.var_width = tk.StringVar(value="760")
        self.var_height = tk.StringVar(value="390")
        self.var_frame_idx = tk.IntVar(value=0)
        self.status_msg = tk.StringVar(value="Ready. Load a file.")
        
        # 2. 레이아웃 생성
        self.create_layout()
        
        # 3. 키보드 이벤트 바인딩
        self.root.bind_all('<Left>', lambda event: self.handle_horizontal_key(event, -1))
        self.root.bind_all('<Right>', lambda event: self.handle_horizontal_key(event, 1))
        self.root.bind_all('<Up>', lambda event: self.handle_vertical_key(event, -1))
        self.root.bind_all('<Down>', lambda event: self.handle_vertical_key(event, 1))
        self.root.bind_all('<Shift-Left>', lambda event: self.handle_horizontal_key(event, -5))
        self.root.bind_all('<Shift-Right>', lambda event: self.handle_horizontal_key(event, 5))
        self.root.bind_all('<Shift-Up>', lambda event: self.handle_vertical_key(event, -5))
        self.root.bind_all('<Shift-Down>', lambda event: self.handle_vertical_key(event, 5))
        
        # 4. 메인 루프
        self.root.mainloop()

    def setup_style(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("TFrame", background=PANEL_COLOR)
        style.configure("TLabel", background=PANEL_COLOR, foreground=TEXT_COLOR, font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"), foreground=ACCENT_COLOR)
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6, background=ACCENT_COLOR, foreground="white", borderwidth=0)
        style.map("TButton", background=[('active', '#2b7bbd')])
        style.configure("TLabelframe", background=PANEL_COLOR, foreground=TEXT_COLOR)
        style.configure("TLabelframe.Label", background=PANEL_COLOR, foreground=ACCENT_COLOR, font=("Segoe UI", 10, "bold"))

    def create_layout(self):
        # [LEFT] Canvas
        self.left_panel = tk.Frame(self.root, bg=BG_COLOR)
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.fig, self.ax = plt.subplots(figsize=(10, 8), dpi=100, facecolor=BG_COLOR)
        self.ax.set_facecolor(BG_COLOR)
        self.ax.axis('off')
        self.zoom_ax = self.fig.add_axes([0.68, 0.70, 0.22, 0.22], facecolor="#111111")
        self.zoom_ax.set_xticks([])
        self.zoom_ax.set_yticks([])
        self.zoom_ax.set_title("Zoom", color="white", fontsize=9, pad=4)
        for spine in self.zoom_ax.spines.values():
            spine.set_edgecolor("white")
            spine.set_linewidth(1.0)
        self.zoom_ax.set_visible(False)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.left_panel)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.canvas.mpl_connect('button_press_event', self.on_canvas_click)

        # [RIGHT] Control Panel
        self.right_panel = tk.Frame(self.root, bg=PANEL_COLOR, width=350)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.Y)
        self.right_panel.pack_propagate(False)

        # --- 1. File Load ---
        frame_file = ttk.LabelFrame(self.right_panel, text=" 1. File Operations ", padding=15)
        frame_file.pack(fill=tk.X, padx=15, pady=10)
        self.lbl_file = ttk.Label(frame_file, text="No file loaded", anchor="center")
        self.lbl_file.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(frame_file, text="📂 Load MAT File", command=self.load_file).pack(fill=tk.X)

        # --- 2. Frame Selection ---
        frame_slide = ttk.LabelFrame(self.right_panel, text=" 2. Select Frame (Use ← / →) ", padding=15)
        frame_slide.pack(fill=tk.X, padx=15, pady=10)
        self.lbl_frame = ttk.Label(frame_slide, text="Frame: 0")
        self.lbl_frame.pack(anchor='w')
        self.slider = ttk.Scale(frame_slide, from_=0, to=100, variable=self.var_frame_idx, command=self.on_slider_change)
        self.slider.pack(fill=tk.X, pady=5)

        # --- 3. Points & Calculation ---
        frame_pts = ttk.LabelFrame(self.right_panel, text=" 3. Corner Detection ", padding=15)
        frame_pts.pack(fill=tk.X, padx=15, pady=10)
        
        self.btn_pos = tk.Button(frame_pts, text="🎯 Set Points (Manual)", 
                                 font=("Segoe UI", 11, "bold"), 
                                 bg=ACCENT_COLOR, fg="white", 
                                 activebackground="#2b7bbd", activeforeground="white",
                                 relief="flat", cursor="hand2",
                                 command=self.toggle_positioning_mode)
        self.btn_pos.pack(fill=tk.X, pady=5, ipady=5)

        self.lbl_pts_status = ttk.Label(frame_pts, text="Points: 0 / 4", font=("Segoe UI", 11), anchor="center")
        self.lbl_pts_status.pack(pady=5)

        self.btn_calc = tk.Button(frame_pts, text="⚙️ Calculate Position (Auto)", 
                                  font=("Segoe UI", 11, "bold"), 
                                  bg=ACTION_COLOR, fg="white", 
                                  activebackground="#d35400", activeforeground="white",
                                  relief="flat", cursor="hand2",
                                  state="disabled", 
                                  command=self.run_calculation)
        self.btn_calc.pack(fill=tk.X, pady=5, ipady=5)

        ttk.Button(frame_pts, text="↺ Reset Points", command=self.reset_points).pack(fill=tk.X, pady=5)

        # --- 4. Target Scale ---
        frame_target = ttk.LabelFrame(self.right_panel, text=" 4. Target Scale ", padding=15)
        frame_target.pack(fill=tk.X, padx=15, pady=10)
        
        self.create_entry(frame_target, "Target Width (mm):", self.var_width, 0)
        self.create_entry(frame_target, "Target Height (mm):", self.var_height, 1)

        # --- 5. Execute ---
        frame_exec = ttk.LabelFrame(self.right_panel, text=" 5. Execute ", padding=15)
        frame_exec.pack(fill=tk.X, padx=15, pady=10, side=tk.BOTTOM)
        
        self.btn_save = tk.Button(frame_exec, text="💾 Run and Save", 
                                  font=("Segoe UI", 12, "bold"), 
                                  bg=SUCCESS_COLOR, fg="white", 
                                  activebackground="#2ecc71", activeforeground="white",
                                  relief="flat", cursor="hand2",
                                  state="disabled", 
                                  command=self.run_warp_process)
        self.btn_save.pack(fill=tk.X, pady=(0, 10), ipady=10)
        
        ttk.Button(frame_exec, text="📂 Open Current Folder", command=self.open_current_folder).pack(fill=tk.X)
        
        self.btn_save.config(text="Run Current Sample")

        self.btn_save_points = tk.Button(frame_exec, text="Save Points Only",
                                         font=("Segoe UI", 11, "bold"),
                                         bg=ACCENT_COLOR, fg="white",
                                         activebackground="#2b7bbd", activeforeground="white",
                                         relief="flat", cursor="hand2",
                                         state="disabled",
                                         command=self.save_points_only)
        self.btn_save_points.pack(fill=tk.X, pady=(8, 8), ipady=7)

        self.btn_batch = tk.Button(frame_exec, text="Batch Process Saved Points",
                                   font=("Segoe UI", 11, "bold"),
                                   bg=ACTION_COLOR, fg="white",
                                   activebackground="#d35400", activeforeground="white",
                                   relief="flat", cursor="hand2",
                                   command=self.batch_process_saved_points)
        self.btn_batch.pack(fill=tk.X, pady=(0, 10), ipady=7)

        ttk.Label(self.right_panel, textvariable=self.status_msg, foreground="#aaaaaa").pack(side=tk.BOTTOM, pady=5)

    def create_entry(self, parent, label, variable, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky='w', pady=2)
        e = tk.Entry(parent, textvariable=variable, bg=ENTRY_BG, fg="white", insertbackground="white", relief="flat", width=10)
        e.grid(row=row, column=1, sticky='e', pady=2, padx=5)

    def open_current_folder(self):
        target_dir = getattr(self, 'file_dir', None) or self.script_dir
        if os.path.exists(target_dir):
            try:
                os.startfile(target_dir) 
            except AttributeError:
                import subprocess
                try:
                    subprocess.call(['open', target_dir]) 
                except:
                    subprocess.call(['xdg-open', target_dir]) 
        else:
            messagebox.showwarning("Warning", "No active folder found.")

    def move_frame(self, event, delta):
        if isinstance(event.widget, tk.Entry): return
        if self.full_images is None: return
        
        current_idx = self.var_frame_idx.get()
        new_idx = current_idx + delta
        if 0 <= new_idx < self.full_images.shape[0]:
            self.var_frame_idx.set(new_idx)
            self.on_slider_change(new_idx)

    def handle_horizontal_key(self, event, delta):
        if self.selected_point_idx is not None:
            self.nudge_selected_point(delta, 0)
            return "break"
        if delta in (-1, 1):
            self.move_frame(event, delta)
            return "break"

    def handle_vertical_key(self, event, delta):
        if self.selected_point_idx is None:
            return
        self.nudge_selected_point(0, delta)
        return "break"

    def nudge_selected_point(self, dx, dy):
        if isinstance(self.root.focus_get(), tk.Entry):
            return
        if self.selected_point_idx is None or self.current_frame is None:
            return
        if not (0 <= self.selected_point_idx < len(self.manual_points)):
            self.selected_point_idx = None
            return

        height, width = self.current_frame.shape[:2]
        x, y = self.manual_points[self.selected_point_idx]
        x = float(np.clip(x + dx, 0, width - 1))
        y = float(np.clip(y + dy, 0, height - 1))
        self.manual_points[self.selected_point_idx] = [x, y]
        self.draw_points()
        self.status_msg.set(f"Point {self.selected_point_idx + 1} adjusted to ({x:.1f}, {y:.1f}).")

    def find_nearby_point(self, x, y):
        if not self.manual_points or self.current_frame is None:
            return None

        pts = np.array(self.manual_points, dtype=np.float32)
        click_pt = np.array([x, y], dtype=np.float32)
        distances = np.linalg.norm(pts - click_pt, axis=1)
        pick_radius = max(8.0, min(self.current_frame.shape[:2]) * 0.03)
        nearest_idx = int(np.argmin(distances))
        if distances[nearest_idx] <= pick_radius:
            return nearest_idx
        return None

    # =========================================================
    # 1. 파일 로드
    # =========================================================
    def load_file(self):
        file_path = filedialog.askopenfilename(title="Select MAT file", filetypes=[("MAT files", "*.mat")])
        if not file_path: return

        try:
            data = sio.loadmat(file_path)
            if 'temperature_frames' in data:
                self.full_images = data['temperature_frames']
            elif 'images' in data:
                self.full_images = data['images']
            else:
                messagebox.showerror("Error", "No valid image data found.")
                return

            self.mat_path = file_path
            self.file_name = os.path.splitext(os.path.basename(file_path))[0]
            self.file_dir = os.path.dirname(file_path)
            
            num_frames = self.full_images.shape[0]
            init_idx = int(num_frames * 0.1)
            
            self.slider.configure(to=num_frames-1)
            self.var_frame_idx.set(init_idx)
            
            self.lbl_file.config(text=self.file_name)
            self.reset_points(silent=True)
            
            self.update_image(init_idx)
            self.status_msg.set(f"Loaded. Total frames: {num_frames}")
            self.root.focus_set()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load: {e}")

    def on_slider_change(self, val):
        if self.full_images is None: return
        idx = int(float(val))
        self.lbl_frame.config(text=f"Frame: {idx}")
        self.update_image(idx)

    def update_image(self, idx):
        self.current_frame = self.full_images[idx]
        if self.img_obj is None:
            self.img_obj = self.ax.imshow(self.current_frame, cmap='jet')
        else:
            self.img_obj.set_data(self.current_frame)
            vmin, vmax = np.min(self.current_frame), np.max(self.current_frame)
            self.img_obj.set_clim(vmin, vmax)
        self.update_zoom_view()
        self.canvas.draw()

    # =========================================================
    # 2. 포인트 설정
    # =========================================================
    def toggle_positioning_mode(self):
        if self.full_images is None:
            messagebox.showwarning("Warning", "Load a file first.")
            return

        self.is_positioning_mode = not self.is_positioning_mode
        
        if self.is_positioning_mode:
            self.btn_pos.config(text="🛑 Stop Setting", bg=STOP_COLOR)
            self.status_msg.set("Click 4 corners on the image.")
            # 이미 4개가 있다면 리셋
            if len(self.manual_points) == 4:
                self.reset_points(silent=True)
        else:
            self.btn_pos.config(text="🎯 Set Points (Manual)", bg=ACCENT_COLOR)
            self.status_msg.set("Positioning mode stopped.")

    def on_canvas_click(self, event):
        if not self.is_positioning_mode: return
        if event.inaxes != self.ax: return
        if len(self.manual_points) >= 4: return 

        self.manual_points.append([event.xdata, event.ydata])
        self.draw_points()
        
        count = len(self.manual_points)
        self.lbl_pts_status.config(text=f"Points: {count} / 4")
        
        if count == 4:
            self.status_msg.set("4 points set. Click 'Calculate Position'.")
            self.toggle_positioning_mode() 
            self.btn_calc.config(state="normal", bg=ACTION_COLOR) 

    def draw_points(self):
        if self.scatter_manual: self.scatter_manual.remove()
        if self.line_manual: 
            for line in self.line_manual: line.remove()
            
        # Draw Points (Using manual_points list)
        pts = np.array(self.manual_points)
        if len(pts) > 0:
            self.scatter_manual = self.ax.scatter(pts[:, 0], pts[:, 1], c='red', s=60, edgecolors='white', zorder=5, label='Points')
            
            if len(pts) > 1:
                # 점들을 잇는 선
                lines = self.ax.plot(pts[:, 0], pts[:, 1], 'r--', linewidth=1, alpha=0.7)
                self.line_manual = lines
                
                # 4개면 닫힌 사각형으로 표시
                if len(pts) == 4:
                    closed = np.vstack([pts, pts[0]])
                    lines[0].set_data(closed[:, 0], closed[:, 1])

        self.canvas.draw()

    def reset_points(self, silent=False):
        self.manual_points = []
        
        self.draw_points()
        self.lbl_pts_status.config(text="Points: 0 / 4")
        
        self.btn_calc.config(state="disabled", bg="#7f8c8d") 
        self.btn_save.config(state="disabled", bg="#7f8c8d") 
        self.is_positioning_mode = False
        self.btn_pos.config(text="🎯 Set Points (Manual)", bg=ACCENT_COLOR)
        
        if not silent:
            self.status_msg.set("Points reset.")

    # =========================================================
    # 3. 계산 (Red Points Move)
    # =========================================================
    def run_calculation(self):
        if len(self.manual_points) != 4:
            messagebox.showwarning("Warning", "Please set 4 points first.")
            return

        self.status_msg.set("Calculating...")
        self.root.update()

        try:
            initial_arr = np.array(self.manual_points, dtype=np.float32)
            # 알고리즘 실행
            refined = self.iterative_refinement(initial_arr, self.current_frame)
            
            # [수정됨] 계산 결과를 manual_points에 덮어씌움 -> 점이 이동함
            self.manual_points = refined.tolist()
            self.draw_points()
            
            self.status_msg.set("Points Snapped to Edges. Ready to Save.")
            self.btn_save.config(state="normal", bg=SUCCESS_COLOR) 
            
        except Exception as e:
            messagebox.showerror("Error", f"Calculation failed: {e}")
            self.status_msg.set("Calculation failed.")

    def toggle_positioning_mode(self):
        if self.full_images is None:
            messagebox.showwarning("Warning", "Load a file first.")
            return

        self.is_positioning_mode = not self.is_positioning_mode

        if self.is_positioning_mode:
            self.btn_pos.config(text="🛑 Stop Setting", bg=STOP_COLOR)
            self.status_msg.set("Click points to add or reselect them. Use arrow keys for fine adjustment.")
        else:
            self.btn_pos.config(text="🎯 Set Points (Manual)", bg=ACCENT_COLOR)
            self.status_msg.set("Positioning mode stopped.")

    def on_canvas_click(self, event):
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            return

        self.root.focus_set()

        selected_idx = self.find_nearby_point(event.xdata, event.ydata)
        if selected_idx is not None:
            self.selected_point_idx = selected_idx
            self.draw_points()
            self.status_msg.set(f"Point {selected_idx + 1} selected. Use arrow keys to fine-tune it.")
            return

        if not self.is_positioning_mode:
            return
        if len(self.manual_points) >= 4:
            self.status_msg.set("Select an existing point to fine-tune it.")
            return

        self.manual_points.append([event.xdata, event.ydata])
        self.selected_point_idx = len(self.manual_points) - 1
        self.draw_points()

        count = len(self.manual_points)
        self.lbl_pts_status.config(text=f"Points: {count} / 4")

        if count == 4:
            self.is_positioning_mode = False
            self.btn_calc.config(state="normal", bg=ACTION_COLOR)
            self.status_msg.set("4 points set. Select a point to fine-tune it or click 'Calculate Position'.")
        else:
            self.status_msg.set(f"Point {count} added. Click it again, then use arrow keys to fine-tune.")

    def draw_points(self):
        if self.scatter_manual:
            self.scatter_manual.remove()
        if self.scatter_selected:
            self.scatter_selected.remove()
        if self.line_manual:
            for line in self.line_manual:
                line.remove()

        self.scatter_manual = None
        self.scatter_selected = None
        self.line_manual = None

        pts = np.array(self.manual_points)
        if len(pts) > 0:
            self.scatter_manual = self.ax.scatter(
                pts[:, 0], pts[:, 1], c='red', s=60, edgecolors='white', zorder=5, label='Points'
            )

            if self.selected_point_idx is not None and 0 <= self.selected_point_idx < len(pts):
                selected_pt = pts[self.selected_point_idx]
                self.scatter_selected = self.ax.scatter(
                    [selected_pt[0]], [selected_pt[1]],
                    s=180, facecolors='none', edgecolors='yellow', linewidths=2.0, zorder=6
                )

            if len(pts) > 1:
                lines = self.ax.plot(pts[:, 0], pts[:, 1], 'r--', linewidth=1, alpha=0.7)
                self.line_manual = lines

                if len(pts) == 4:
                    closed = np.vstack([pts, pts[0]])
                    lines[0].set_data(closed[:, 0], closed[:, 1])

        self.update_zoom_view()
        self.canvas.draw()

    def reset_points(self, silent=False):
        self.manual_points = []
        self.selected_point_idx = None

        self.draw_points()
        self.lbl_pts_status.config(text="Points: 0 / 4")

        self.btn_calc.config(state="disabled", bg="#7f8c8d")
        self.btn_save.config(state="disabled", bg="#7f8c8d")
        self.is_positioning_mode = False
        self.btn_pos.config(text="🎯 Set Points (Manual)", bg=ACCENT_COLOR)

        if not silent:
            self.status_msg.set("Points reset.")

    def get_target_dimensions(self):
        try:
            target_w = int(self.var_width.get())
            target_h = int(self.var_height.get())
        except Exception:
            raise ValueError("Invalid target dimensions.")

        if target_w <= 0 or target_h <= 0:
            raise ValueError("Target dimensions must be positive.")
        return target_w, target_h

    def get_xy_save_path(self, mat_path=None):
        source_path = mat_path or self.mat_path
        if not source_path:
            raise ValueError("No MAT file selected.")
        source_dir = os.path.dirname(source_path)
        source_name = os.path.splitext(os.path.basename(source_path))[0]
        return os.path.join(source_dir, f"{source_name}_xy.mat")

    def save_points_metadata(self, mat_path, points, target_w, target_h):
        xy_save_path = self.get_xy_save_path(mat_path)
        points_arr = np.array(points, dtype=np.float32)
        sio.savemat(
            xy_save_path,
            {
                'x': points_arr[:, 0].reshape(-1, 1),
                'y': points_arr[:, 1].reshape(-1, 1),
                'target_width': np.array([[target_w]], dtype=np.int32),
                'target_height': np.array([[target_h]], dtype=np.int32),
            }
        )
        return xy_save_path

    def load_points_metadata(self, xy_path):
        data = sio.loadmat(xy_path)
        if 'x' not in data or 'y' not in data:
            raise ValueError(f"Invalid point file: {os.path.basename(xy_path)}")

        x = np.array(data['x'], dtype=np.float32).reshape(-1)
        y = np.array(data['y'], dtype=np.float32).reshape(-1)
        if x.size != 4 or y.size != 4:
            raise ValueError(f"Point file must contain exactly 4 points: {os.path.basename(xy_path)}")

        points = np.column_stack((x, y)).astype(np.float32)
        target_w = int(np.array(data.get('target_width', [[int(self.var_width.get() or 0)]]), dtype=np.int32).reshape(-1)[0])
        target_h = int(np.array(data.get('target_height', [[int(self.var_height.get() or 0)]]), dtype=np.int32).reshape(-1)[0])
        if target_w <= 0 or target_h <= 0:
            raise ValueError(f"Invalid target size in point file: {os.path.basename(xy_path)}")

        return points, target_w, target_h

    def load_images_from_mat(self, mat_path):
        data = sio.loadmat(mat_path)
        if 'temperature_frames' in data:
            return data['temperature_frames']
        if 'images' in data:
            return data['images']
        raise ValueError(f"No valid image data found in {os.path.basename(mat_path)}.")

    def warp_images_with_points(self, images, final_pts, target_w, target_h, progress_prefix=None):
        dst_pts = np.array([
            [0, 0],
            [target_w, 0],
            [target_w, target_h],
            [0, target_h]
        ], dtype=np.float32)
        M = cv2.getPerspectiveTransform(np.array(final_pts, dtype=np.float32), dst_pts)

        num_frames = images.shape[0]
        output_images = np.zeros((num_frames, target_h, target_w), dtype=np.float32)

        for i in range(num_frames):
            output_images[i, :, :] = cv2.warpPerspective(
                images[i, :, :], M, (target_w, target_h), flags=cv2.INTER_LINEAR
            )
            if i % 100 == 0 or i == num_frames - 1:
                if progress_prefix:
                    self.status_msg.set(f"{progress_prefix}: {i + 1}/{num_frames} frames")
                self.root.update()
        return output_images

    def process_single_sample(self, mat_path, points, target_w, target_h, progress_prefix=None):
        images = self.load_images_from_mat(mat_path)
        output_images = self.warp_images_with_points(images, points, target_w, target_h, progress_prefix)
        new_save_path = os.path.join(
            os.path.dirname(mat_path),
            f"{os.path.splitext(os.path.basename(mat_path))[0]}_new.mat"
        )
        sio.savemat(new_save_path, {'images': output_images})
        return new_save_path

    def save_points_only(self):
        if len(self.manual_points) != 4:
            messagebox.showwarning("Warning", "Please set 4 points first.")
            return
        if not self.mat_path:
            messagebox.showwarning("Warning", "Load a file first.")
            return

        try:
            target_w, target_h = self.get_target_dimensions()
            group_paths = self.get_current_group_paths()
            saved_count = 0
            last_xy_save_path = None
            for mat_path in group_paths:
                last_xy_save_path = self.save_points_metadata(mat_path, self.manual_points, target_w, target_h)
                saved_count += 1

            group_label = self.get_group_display_name(self.mat_path)
            self.status_msg.set(f"Saved shared point file for {group_label} ({saved_count} file(s)).")
            has_next = self.file_queue and (self.current_file_index + 1) < len(self.file_queue)
            if has_next:
                self.move_to_next_file_in_queue()
            else:
                self.status_msg.set("All selected MAT files have saved points.")
                messagebox.showinfo(
                    "Saved",
                    f"Shared point file saved for group {group_label}.\nApplied to {saved_count} file(s).\n\nLast saved file:\n{os.path.basename(last_xy_save_path)}\n\nAll selected MAT files are done.\nUse 'Batch Process Saved Points' to process them all at once."
                )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save points: {e}")

    def batch_process_saved_points(self):
        loaded_files = []
        for mat_path in self.file_queue or ([self.mat_path] if self.mat_path else []):
            if mat_path and mat_path not in loaded_files:
                loaded_files.append(mat_path)

        if not loaded_files:
            messagebox.showwarning("Warning", "Load MAT file(s) first.")
            return

        success_files = []
        failed_files = []
        total_files = len(loaded_files)

        for idx, source_path in enumerate(loaded_files, start=1):
            source_name = os.path.basename(source_path)
            if not os.path.exists(source_path):
                failed_files.append(f"{source_name}: MAT file not found")
                continue

            xy_path = self.get_xy_save_path(source_path)
            if not os.path.exists(xy_path):
                failed_files.append(f"{source_name}: saved point file not found ({os.path.basename(xy_path)})")
                continue

            try:
                points, target_w, target_h = self.load_points_metadata(xy_path)
                self.status_msg.set(f"Batch {idx}/{total_files}: {source_name}")
                self.root.update()
                new_save_path = self.process_single_sample(
                    source_path,
                    points,
                    target_w,
                    target_h,
                    progress_prefix=f"Batch {idx}/{total_files}"
                )
                success_files.append(os.path.basename(new_save_path))
            except Exception as e:
                failed_files.append(f"{source_name}: {e}")

        summary = [f"Processed {len(success_files)} / {total_files} samples."]
        if failed_files:
            summary.append("")
            summary.extend(failed_files[:10])
            if len(failed_files) > 10:
                summary.append(f"... and {len(failed_files) - 10} more failures")

        self.status_msg.set(f"Batch complete: {len(success_files)} / {total_files} samples processed.")
        messagebox.showinfo("Batch Complete", "\n".join(summary))

    def run_calculation(self):
        if len(self.manual_points) != 4:
            messagebox.showwarning("Warning", "Please set 4 points first.")
            return

        self.status_msg.set("Calculating...")
        self.root.update()

        try:
            initial_arr = np.array(self.manual_points, dtype=np.float32)
            refined = self.iterative_refinement(initial_arr, self.current_frame)

            self.manual_points = refined.tolist()
            self.selected_point_idx = None
            self.draw_points()

            self.status_msg.set("Points snapped to edges. Click a point if you want more fine adjustment.")
            self.btn_save.config(state="normal", bg=SUCCESS_COLOR)
            self.btn_save_points.config(state="normal", bg=ACCENT_COLOR)

        except Exception as e:
            messagebox.showerror("Error", f"Calculation failed: {e}")
            self.status_msg.set("Calculation failed.")

    def set_position_button_state(self, active):
        if active:
            self.btn_pos.config(text="Stop Setting", bg=STOP_COLOR)
        else:
            self.btn_pos.config(text="Set Points (Manual)", bg=ACCENT_COLOR)

    def get_zoom_target_point(self):
        if not self.manual_points:
            return None
        if self.selected_point_idx is not None and 0 <= self.selected_point_idx < len(self.manual_points):
            return self.manual_points[self.selected_point_idx]
        return self.manual_points[-1]

    def update_zoom_view(self):
        if self.zoom_ax is None or self.current_frame is None:
            return

        target = self.get_zoom_target_point()
        if target is None:
            self.zoom_ax.set_visible(False)
            return

        height, width = self.current_frame.shape[:2]
        x, y = target
        x = float(np.clip(x, 0, width - 1))
        y = float(np.clip(y, 0, height - 1))

        half = self.zoom_radius
        x0 = max(0, int(np.floor(x - half)))
        x1 = min(width, int(np.ceil(x + half + 1)))
        y0 = max(0, int(np.floor(y - half)))
        y1 = min(height, int(np.ceil(y + half + 1)))
        zoom_region = self.current_frame[y0:y1, x0:x1]

        if zoom_region.size == 0:
            self.zoom_ax.set_visible(False)
            return

        vmin = float(np.min(self.current_frame))
        vmax = float(np.max(self.current_frame))
        extent = [x0, x1, y1, y0]

        if self.zoom_img_obj is None:
            self.zoom_img_obj = self.zoom_ax.imshow(
                zoom_region, cmap='jet', interpolation='nearest', extent=extent
            )
        else:
            self.zoom_img_obj.set_data(zoom_region)
            self.zoom_img_obj.set_extent(extent)
        self.zoom_img_obj.set_clim(vmin, vmax)

        if self.zoom_hline is None:
            self.zoom_hline = self.zoom_ax.axhline(y, color='white', linewidth=0.8, alpha=0.9)
            self.zoom_vline = self.zoom_ax.axvline(x, color='white', linewidth=0.8, alpha=0.9)
            self.zoom_marker = self.zoom_ax.scatter(
                [x], [y], s=70, facecolors='none', edgecolors='yellow', linewidths=1.4, zorder=5
            )
        else:
            self.zoom_hline.set_ydata([y, y])
            self.zoom_vline.set_xdata([x, x])
            self.zoom_marker.set_offsets(np.array([[x, y]]))

        self.zoom_ax.set_xlim(x0, x1)
        self.zoom_ax.set_ylim(y1, y0)
        self.zoom_ax.set_visible(True)

    def toggle_positioning_mode(self):
        if self.full_images is None:
            messagebox.showwarning("Warning", "Load a file first.")
            return

        self.is_positioning_mode = not self.is_positioning_mode
        self.set_position_button_state(self.is_positioning_mode)

        if self.is_positioning_mode:
            self.status_msg.set("Click points to add or reselect them. Use arrow keys for fine adjustment.")
        else:
            self.status_msg.set("Positioning mode stopped.")

    def on_canvas_click(self, event):
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            return

        self.root.focus_set()

        selected_idx = self.find_nearby_point(event.xdata, event.ydata)
        if selected_idx is not None:
            self.selected_point_idx = selected_idx
            self.draw_points()
            self.status_msg.set(f"Point {selected_idx + 1} selected. Use arrow keys to fine-tune it.")
            return

        if not self.is_positioning_mode:
            return
        if len(self.manual_points) >= 4:
            self.status_msg.set("Select an existing point to fine-tune it.")
            return

        self.manual_points.append([event.xdata, event.ydata])
        self.selected_point_idx = len(self.manual_points) - 1
        self.draw_points()

        count = len(self.manual_points)
        self.lbl_pts_status.config(text=f"Points: {count} / 4")

        if count == 4:
            self.is_positioning_mode = False
            self.set_position_button_state(False)
            self.btn_calc.config(state="normal", bg=ACTION_COLOR)
            self.btn_save.config(state="normal", bg=SUCCESS_COLOR)
            self.btn_save_points.config(state="normal", bg=ACCENT_COLOR)
            self.status_msg.set("4 points set. Save points only, run this sample now, or calculate first.")
        else:
            self.status_msg.set(f"Point {count} added. Click it again, then use arrow keys to fine-tune.")

    def reset_points(self, silent=False):
        self.manual_points = []
        self.selected_point_idx = None

        self.draw_points()
        self.lbl_pts_status.config(text="Points: 0 / 4")

        self.btn_calc.config(state="disabled", bg="#7f8c8d")
        self.btn_save.config(state="disabled", bg="#7f8c8d")
        self.btn_save_points.config(state="disabled", bg="#7f8c8d")
        self.is_positioning_mode = False
        self.set_position_button_state(False)

        if not silent:
            self.status_msg.set("Points reset.")

    def iterative_refinement(self, initial_pts, img):
        norm = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        blur = cv2.GaussianBlur(norm, (9, 9), 0)
        _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        refined_pts = []
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            contour_pts = largest_contour.squeeze()
            if contour_pts.ndim == 1: contour_pts = contour_pts.reshape(-1, 2)

            for pt in initial_pts:
                distances = np.linalg.norm(contour_pts - pt, axis=1)
                nearest_idx = np.argmin(distances)
                refined_pts.append(contour_pts[nearest_idx])
            refined_pts = np.array(refined_pts, dtype=np.float32)
        else:
            refined_pts = initial_pts 

        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.001)
        gray_float = np.float32(norm)
        try:
            final_refined = cv2.cornerSubPix(gray_float, refined_pts, (11, 11), (-1, -1), criteria)
        except:
            final_refined = refined_pts
            
        return self.order_points(final_refined)

    def order_points(self, pts):
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)] 
        rect[2] = pts[np.argmax(s)] 
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)] 
        rect[3] = pts[np.argmax(diff)] 
        return rect

    # =========================================================
    # 4. 워핑 및 저장
    # =========================================================
    def run_warp_process(self):
        # manual_points가 이미 보정된(계산된) 상태임
        if len(self.manual_points) != 4:
            messagebox.showwarning("Warning", "Points not set.")
            return
        
        try:
            target_w = int(self.var_width.get())
            target_h = int(self.var_height.get())
        except:
            messagebox.showerror("Error", "Invalid Dimensions.")
            return

        self.status_msg.set("Processing Warping... This may take a while.")
        self.root.update()

        final_pts = np.array(self.manual_points, dtype=np.float32)
        dst_pts = np.array([
            [0, 0],
            [target_w, 0],
            [target_w, target_h],
            [0, target_h]
        ], dtype=np.float32)

        M = cv2.getPerspectiveTransform(final_pts, dst_pts)
        
        num_frames = self.full_images.shape[0]
        output_images = np.zeros((num_frames, target_h, target_w), dtype=np.float32)
        
        print(f">> Warping {num_frames} frames...")
        for i in range(num_frames):
            output_images[i, :, :] = cv2.warpPerspective(
                self.full_images[i, :, :], M, (target_w, target_h), flags=cv2.INTER_LINEAR
            )
            if i % 100 == 0:
                self.status_msg.set(f"Warping: {i}/{num_frames} frames")
                self.root.update()

        xy_save_path = os.path.join(self.file_dir, f"{self.file_name}_xy.mat")
        sio.savemat(xy_save_path, {'x': final_pts[:, 0].reshape(-1, 1), 'y': final_pts[:, 1].reshape(-1, 1)})
        
        new_save_path = os.path.join(self.file_dir, f"{self.file_name}_new.mat")
        sio.savemat(new_save_path, {'images': output_images})
        
        print(f"Saved: {new_save_path}")
        self.status_msg.set("Processing Complete!")
        messagebox.showinfo("Success", f"Files saved:\n{os.path.basename(new_save_path)}")

    def restore_saved_points_for_current_file(self):
        xy_path = self.get_xy_save_path(self.mat_path)
        if not os.path.exists(xy_path):
            return False

        points, target_w, target_h = self.load_points_metadata(xy_path)
        self.manual_points = points.tolist()
        self.selected_point_idx = None
        self.var_width.set(str(target_w))
        self.var_height.set(str(target_h))
        self.lbl_pts_status.config(text="Points: 4 / 4")
        self.btn_calc.config(state="normal", bg=ACTION_COLOR)
        self.btn_save.config(state="normal", bg=SUCCESS_COLOR)
        self.btn_save_points.config(state="normal", bg=ACCENT_COLOR)
        self.draw_points()
        return True

    def get_queue_label(self):
        if self.file_queue and 0 <= self.current_file_index < len(self.file_queue):
            return f"[{self.current_file_index + 1}/{len(self.file_queue)}] "
        return ""

    def strip_repeat_suffix(self, stem):
        return re.sub(r'(?:[ _-])\d+$', '', stem)

    def is_generated_mat_file(self, file_path):
        stem = os.path.splitext(os.path.basename(file_path))[0].lower()
        return stem.endswith('_xy') or stem.endswith('_new')

    def get_file_sort_key(self, file_path):
        stem = os.path.splitext(os.path.basename(file_path))[0]
        repeat_match = re.search(r'(?:[ _-])(\d+)$', stem)
        repeat_idx = int(repeat_match.group(1)) if repeat_match else 0
        return (self.get_point_group_key(file_path), repeat_idx, stem.lower())

    def get_point_group_key(self, file_path):
        stem = os.path.splitext(os.path.basename(file_path))[0]
        shared_stem = self.strip_repeat_suffix(stem)
        return os.path.join(os.path.dirname(file_path).lower(), shared_stem.lower())

    def get_group_display_name(self, file_path):
        stem = os.path.splitext(os.path.basename(file_path))[0]
        return self.strip_repeat_suffix(stem)

    def get_current_group_paths(self):
        if not self.mat_path:
            return []
        if not self.file_queue:
            return [self.mat_path]

        current_key = self.get_point_group_key(self.mat_path)
        return [path for path in self.file_queue if self.get_point_group_key(path) == current_key]

    def load_selected_mat_file(self, file_path):
        self.full_images = self.load_images_from_mat(file_path)
        self.mat_path = file_path
        self.file_name = os.path.splitext(os.path.basename(file_path))[0]
        self.file_dir = os.path.dirname(file_path)

        num_frames = self.full_images.shape[0]
        init_idx = int(num_frames * 0.1)

        self.slider.configure(to=num_frames - 1)
        self.var_frame_idx.set(init_idx)

        self.reset_points(silent=True)
        self.update_image(init_idx)

        queue_label = self.get_queue_label()
        self.lbl_file.config(text=f"{queue_label}{self.file_name}")

        if self.restore_saved_points_for_current_file():
            self.status_msg.set(f"{queue_label}Loaded saved points for {self.file_name}.")
        else:
            self.status_msg.set(f"{queue_label}Loaded. Total frames: {num_frames}")
        self.root.focus_set()

    def move_to_next_file_in_queue(self):
        if not self.file_queue:
            return False

        current_group_key = None
        if 0 <= self.current_file_index < len(self.file_queue):
            current_group_key = self.get_point_group_key(self.file_queue[self.current_file_index])

        next_index = self.current_file_index + 1
        while next_index < len(self.file_queue):
            if self.get_point_group_key(self.file_queue[next_index]) != current_group_key:
                break
            next_index += 1

        if next_index >= len(self.file_queue):
            self.status_msg.set("All selected MAT files have saved points.")
            messagebox.showinfo(
                "Queue Complete",
                "All selected MAT files have saved points.\n\nUse 'Batch Process Saved Points' to process them all at once."
            )
            return False

        self.current_file_index = next_index
        self.load_selected_mat_file(self.file_queue[self.current_file_index])
        return True

    def load_file(self):
        file_paths = filedialog.askopenfilenames(
            title="Select MAT file(s)",
            initialdir=self.script_dir,
            filetypes=[("MAT files", "*.mat")]
        )
        if not file_paths:
            return

        try:
            self.file_queue = sorted(
                [path for path in file_paths if not self.is_generated_mat_file(path)],
                key=self.get_file_sort_key
            )
            if not self.file_queue:
                messagebox.showwarning("Warning", "Select source MAT files, not *_xy.mat or *_new.mat files.")
                return
            self.current_file_index = 0
            self.load_selected_mat_file(self.file_queue[self.current_file_index])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load: {e}")

    def run_warp_process(self):
        if len(self.manual_points) != 4:
            messagebox.showwarning("Warning", "Points not set.")
            return
        if not self.mat_path:
            messagebox.showwarning("Warning", "Load a file first.")
            return

        try:
            target_w, target_h = self.get_target_dimensions()
            final_pts = np.array(self.manual_points, dtype=np.float32)
            xy_save_path = self.save_points_metadata(self.mat_path, final_pts, target_w, target_h)

            self.status_msg.set("Processing current sample...")
            self.root.update()
            new_save_path = self.process_single_sample(
                self.mat_path,
                final_pts,
                target_w,
                target_h,
                progress_prefix="Current sample"
            )

            self.status_msg.set("Processing complete.")
            messagebox.showinfo(
                "Success",
                f"Files saved:\n{os.path.basename(xy_save_path)}\n{os.path.basename(new_save_path)}"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Processing failed: {e}")
            self.status_msg.set("Processing failed.")

if __name__ == "__main__":
    ModernPerspectiveGUI()
