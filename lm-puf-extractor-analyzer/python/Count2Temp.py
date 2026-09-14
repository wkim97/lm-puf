import fnv.file
import fnv
import numpy as np
import scipy.io as sio
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import gc

# --- 스타일 설정 ---
BG_COLOR = "#2e2e2e"       
PANEL_COLOR = "#3c3f41"    
TEXT_COLOR = "#ffffff"     
ACCENT_COLOR = "#3a96dd"   # 파란색 (일반 버튼)
ACTION_COLOR = "#e67e22"   # 주황색 (작업 버튼)
SUCCESS_COLOR = "#27ae60"  # 녹색 (완료/실행)
STOP_COLOR = "#c0392b"     # 빨간색 (중지/삭제)
ENTRY_BG = "#45494a"       
LIST_BG = "#2b2b2b"

class ModernSeqConverterGUI:
    def __init__(self):
        # 1. 메인 윈도우 설정
        self.root = tk.Tk()
        self.root.title("SEQ to MAT Converter Pro")
        self.root.geometry("900x700")
        self.root.configure(bg=BG_COLOR)
        
        self.selected_files = []
        self.is_processing = False
        
        self.setup_style()
        self.create_layout()
        
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
        
        # 프로그레스바 스타일
        style.configure("Horizontal.TProgressbar", background=SUCCESS_COLOR, troughcolor=ENTRY_BG, bordercolor=PANEL_COLOR, lightcolor=SUCCESS_COLOR, darkcolor=SUCCESS_COLOR)

    def create_layout(self):
        # 메인 패널
        main_frame = tk.Frame(self.root, bg=BG_COLOR)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # 1. 파일 관리 영역
        frame_file = ttk.LabelFrame(main_frame, text=" 1. File Selection ", padding=15)
        frame_file.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # 버튼 영역 (파일 추가/삭제)
        btn_frame = tk.Frame(frame_file, bg=PANEL_COLOR)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.btn_add = tk.Button(btn_frame, text="📂 Add SEQ Files", 
                                 font=("Segoe UI", 10, "bold"), bg=ACCENT_COLOR, fg="white", 
                                 activebackground="#2980b9", activeforeground="white", relief="flat", padx=15, pady=5,
                                 command=self.select_files)
        self.btn_add.pack(side=tk.LEFT, padx=(0, 5))
        
        self.btn_clear = tk.Button(btn_frame, text="🗑️ Clear List", 
                                   font=("Segoe UI", 10, "bold"), bg=STOP_COLOR, fg="white", 
                                   activebackground="#a93226", activeforeground="white", relief="flat", padx=15, pady=5,
                                   command=self.clear_files)
        self.btn_clear.pack(side=tk.LEFT)

        # 리스트박스 (스크롤바 포함)
        list_container = tk.Frame(frame_file, bg=PANEL_COLOR)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        scrollbar_y = tk.Scrollbar(list_container, orient=tk.VERTICAL)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.file_listbox = tk.Listbox(list_container, 
                                       bg=LIST_BG, fg=TEXT_COLOR, 
                                       selectbackground=ACCENT_COLOR, selectforeground="white",
                                       font=("Consolas", 10), bd=0, highlightthickness=0,
                                       yscrollcommand=scrollbar_y.set)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.config(command=self.file_listbox.yview)
        
        # 2. 실행 영역
        frame_run = ttk.LabelFrame(main_frame, text=" 2. Execution ", padding=15)
        frame_run.pack(fill=tk.X, pady=(0, 15))
        
        info_lbl = ttk.Label(frame_run, text="* Converted .mat files will be saved in the same directory as the source files.")
        info_lbl.pack(anchor='w', pady=(0, 10))
        
        self.btn_convert = tk.Button(frame_run, text="🚀 Start Conversion", 
                                     font=("Segoe UI", 14, "bold"), bg=ACTION_COLOR, fg="white", 
                                     activebackground="#d35400", activeforeground="white", relief="flat",
                                     state="disabled", cursor="hand2",
                                     command=self.start_conversion)
        self.btn_convert.pack(fill=tk.X, ipady=10)

        # 3. 상태 및 진행률
        frame_status = ttk.LabelFrame(main_frame, text=" 3. Progress ", padding=15)
        frame_status.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.lbl_status = ttk.Label(frame_status, text="Ready.", font=("Segoe UI", 11, "bold"), foreground="#aaaaaa")
        self.lbl_status.pack(anchor='w', pady=(0, 5))
        
        self.progress_bar = ttk.Progressbar(frame_status, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.lbl_detail = ttk.Label(frame_status, text="", font=("Segoe UI", 9), foreground="#888888")
        self.lbl_detail.pack(anchor='w')

    # =========================================================
    # 기능 로직
    # =========================================================
    def select_files(self):
        files = filedialog.askopenfilenames(
            title="Select SEQ files",
            filetypes=[("SEQ Files", "*.seq"), ("All Files", "*.*")]
        )
        
        if files:
            for file in files:
                if file not in self.selected_files:
                    self.selected_files.append(file)
                    self.file_listbox.insert(tk.END, os.path.basename(file))
            
            self.update_ui_state()

    def clear_files(self):
        self.selected_files = []
        self.file_listbox.delete(0, tk.END)
        self.update_ui_state()

    def update_ui_state(self):
        if self.selected_files and not self.is_processing:
            self.btn_convert.config(state="normal", bg=ACTION_COLOR)
            self.lbl_status.config(text=f"{len(self.selected_files)} files ready.")
        else:
            self.btn_convert.config(state="disabled", bg="#7f8c8d")
            if not self.is_processing:
                self.lbl_status.config(text="Please add files.")

    def start_conversion(self):
        if self.is_processing: return
        
        self.is_processing = True
        self.btn_convert.config(state="disabled", text="⏳ Processing...", bg="#7f8c8d")
        self.btn_add.config(state="disabled")
        self.btn_clear.config(state="disabled")
        
        # 스레드 실행
        thread = threading.Thread(target=self.process_files)
        thread.daemon = True
        thread.start()

    def process_files(self):
        total_files = len(self.selected_files)
        self.progress_bar['maximum'] = total_files
        self.progress_bar['value'] = 0
        
        success_count = 0
        error_files = []
        
        for idx, seq_path in enumerate(self.selected_files):
            filename = os.path.basename(seq_path)
            self.update_labels(f"Processing ({idx+1}/{total_files}): {filename}", "Initializing reader...")
            
            try:
                # 출력 경로 설정
                folder = os.path.dirname(seq_path)
                base_name = os.path.splitext(filename)[0]
                output_mat_path = os.path.join(folder, f"{base_name}.mat")
                
                # 변환 로직 수행
                self.convert_seq_to_mat(seq_path, output_mat_path)
                
                success_count += 1
                
                # 메모리 정리
                gc.collect()
                
            except Exception as e:
                error_files.append((filename, str(e)))
                print(f"Error processing {filename}: {e}")
            
            # 진행률 업데이트
            self.progress_bar['value'] = idx + 1
            self.root.update_idletasks()

        # 완료 처리
        self.is_processing = False
        self.finish_processing(success_count, total_files, error_files)

    def convert_seq_to_mat(self, seq_path, output_mat_path):
        """메모리 효율적인 변환 로직 (기존 로직 유지)"""
        im = None
        try:
            im = fnv.file.ImagerFile(seq_path)
            
            # Unit 설정
            units = im.supported_units
            temp_unit = next((u for u in units if 'temp' in u.name.lower()), None)
            if not temp_unit and units: temp_unit = units[0]
            if not temp_unit: raise ValueError("Temperature unit not found.")
            
            im.unit = temp_unit
            im.temp_type = fnv.TempType.CELSIUS
            
            # 첫 프레임 확인
            frame, _ = im.first_frame_number(fnv.Preset.ANY)
            if frame is None: raise ValueError("No valid frames found.")
            frame = int(frame)
            
            im.get_frame(frame)
            width, height = im.width, im.height
            
            # 전체 프레임 인덱스 수집
            frame_numbers = []
            curr = frame
            while curr is not None:
                frame_numbers.append(int(curr))
                curr, _ = im.next_frame_number(curr, fnv.Preset.ANY)
            
            num_frames = len(frame_numbers)
            if num_frames == 0: raise ValueError("Empty video.")
            
            # 데이터 적재
            all_frames = np.zeros((num_frames, height, width), dtype=np.float32)
            
            for i, f_num in enumerate(frame_numbers):
                # 단위 재설정 (안전장치)
                im.unit = temp_unit
                im.temp_type = fnv.TempType.CELSIUS
                
                im.get_frame(f_num)
                # im.update_frame() # 필요 시 주석 해제 (일부 버전에서 필요)
                
                # 데이터 변환
                data = np.array(im.final, dtype=np.float32).reshape((height, width))
                all_frames[i, :, :] = data
                
                if i % 10 == 0:
                    self.update_detail_safe(f"Reading frame {i+1}/{num_frames}...")
            
            # 저장
            self.update_detail_safe("Saving MAT file...")
            sio.savemat(output_mat_path, {'temperature_frames': all_frames})
            del all_frames

        finally:
            if im:
                try: im.close()
                except: pass

    # =========================================================
    # UI 업데이트 헬퍼 (스레드 안전)
    # =========================================================
    def update_labels(self, status, detail):
        self.lbl_status.config(text=status)
        self.lbl_detail.config(text=detail)
        self.root.update_idletasks()

    def update_detail_safe(self, message):
        self.lbl_detail.config(text=message)
        self.root.update_idletasks()

    def finish_processing(self, success, total, errors):
        self.btn_convert.config(state="normal", text="🚀 Start Conversion", bg=ACTION_COLOR)
        self.btn_add.config(state="normal")
        self.btn_clear.config(state="normal")
        
        if errors:
            msg = f"Completed: {success}/{total} successful.\n\nFailed Files:\n"
            for fname, err in errors[:5]:
                msg += f"• {fname}: {err}\n"
            if len(errors) > 5: msg += "..."
            messagebox.showwarning("Completed with Errors", msg)
            self.update_labels("Completed with errors.", "Check popup for details.")
        else:
            messagebox.showinfo("Success", f"All {total} files converted successfully!")
            self.update_labels("All tasks completed successfully.", "Ready for next batch.")

def main():
    ModernSeqConverterGUI()

if __name__ == "__main__":
    main()