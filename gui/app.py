import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
import threading
import time
import logging

from can_interface import CanInterface
from threads import SimulationThread, BinarySearchThread
from gui.tabs import replay_tab, missing_tab, error_tab, step_tab, manual_tab, binary_tab, wizard_tab, sniffer_tab, chart_tab, ml_analysis_tab
from gui.utils import write_log_to_file
from controllers import (
    CanController, ReplayController, MissingController, ErrorController,
    StepController, ManualController, BinaryController, WizardController, SnifferController
)

logger = logging.getLogger("App")


class CanSimulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CAN Simulator GUI")
        self.root.geometry("1000x850")

        self.can = CanInterface()
        self.sim_thread = None
        self.binary_thread = None
        self.loaded_frames = []
        self.step_frames = []
        self.step_idx = 0
        self.binary_frames = []

        self.manual_cyclic_active = False
        self.manual_cyclic_thread = None

        self.replay_use_timestamps = tk.BooleanVar(value=False)

        # Kreator
        self.wizard_frames = []
        self.wizard_id_var = tk.StringVar()
        self.wizard_data_var = tk.StringVar()
        self.wizard_extended_var = tk.BooleanVar(value=False)
        self.wizard_mode_var = tk.StringVar(value="single")
        self.wizard_sequence = []
        self.wizard_target = None
        self.wizard_left = 0
        self.wizard_right = 0
        self.wizard_history = []
        self.wizard_answer = None
        self.wizard_answer_event = threading.Event()

        # Sniffer
        self.sniffer_running = False
        self.sniffer_filter_var = tk.BooleanVar(value=False)
        self.sniffer_queue = []
        self.sniffer_lock = threading.Lock()
        self.sniffer_last_data = {}

        # Kontrolery
        self.can_ctrl = CanController(self)
        self.replay_ctrl = ReplayController(self)
        self.missing_ctrl = MissingController(self)
        self.error_ctrl = ErrorController(self)
        self.step_ctrl = StepController(self)
        self.manual_ctrl = ManualController(self)
        self.binary_ctrl = BinaryController(self)
        self.wizard_ctrl = WizardController(self)
        self.sniffer_ctrl = SnifferController(self)

        self._create_widgets()
        logger.info("Interfejs GUI utworzony")

    def log(self, msg):
        logger.info(msg)
        self.log_text.config(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.status_var.set(msg)

        if hasattr(self, 'replay_log_enable') and self.replay_log_enable.get():
            log_path = self.replay_log_var.get()
            if log_path:
                write_log_to_file(log_path, msg)

    def _create_widgets(self):
        # Połączenie CAN
        frame_conn = ttk.LabelFrame(self.root, text="Połączenie CAN", padding=5)
        frame_conn.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(frame_conn, text="Interfejs:").grid(row=0, column=0, sticky=tk.W)
        self.entry_iface = ttk.Entry(frame_conn, width=15)
        self.entry_iface.insert(0, "can0")
        self.entry_iface.grid(row=0, column=1, padx=5)

        self.btn_connect = ttk.Button(frame_conn, text="Połącz", command=self.can_ctrl.toggle_connection)
        self.btn_connect.grid(row=0, column=2, padx=5)

        self.lbl_status = ttk.Label(frame_conn, text="Niepołączony", foreground="red")
        self.lbl_status.grid(row=0, column=3, padx=10)

        # Zakładki
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.tab_replay = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_replay, text="Odtwarzanie pliku")
        replay_tab.setup_replay_tab(self, self.tab_replay)

        self.tab_missing = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_missing, text="Symulacja modułu")
        missing_tab.setup_missing_tab(self, self.tab_missing)

        self.tab_error = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_error, text="Ramki błędu")
        error_tab.setup_error_tab(self, self.tab_error)

        self.tab_step = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_step, text="Tryb krokowy")
        step_tab.setup_step_tab(self, self.tab_step)

        self.tab_manual = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_manual, text="Wysyłanie ręczne")
        manual_tab.setup_manual_tab(self, self.tab_manual)

        self.tab_binary = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_binary, text="Wyszukiwanie binarne")
        binary_tab.setup_binary_tab(self, self.tab_binary)

        self.tab_wizard = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_wizard, text="Kreator wyszukiwania")
        wizard_tab.setup_wizard_tab(self, self.tab_wizard)

        self.tab_sniffer = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_sniffer, text="Sniffer CAN")
        sniffer_tab.setup_sniffer_tab(self, self.tab_sniffer)

        self.tab_chart = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_chart, text="Wykresy")
        chart_tab.setup_chart_tab(self, self.tab_chart)

        self.tab_ml = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ml, text="Analiza ML")
        ml_analysis_tab.setup_ml_tab(self, self.tab_ml)

        # Log
        frame_log = ttk.LabelFrame(self.root, text="Log", padding=5)
        frame_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.log_text = scrolledtext.ScrolledText(frame_log, height=12, state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.status_var = tk.StringVar(value="Gotowy.")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN).pack(fill=tk.X, padx=10, pady=2)

    def _set_buttons_state(self, state):
        buttons = [
            self.replay_start_btn, self.missing_start_btn, self.error_start_btn,
            self.manual_send_once_btn, self.manual_start_btn, self.binary_start_btn
        ]
        for btn in buttons:
            btn.config(state=state)

        if state == 'disabled':
            disable_buttons = [
                self.replay_pause_btn, self.replay_stop_btn, self.manual_stop_btn,
                self.binary_yes_btn, self.binary_no_btn, self.binary_stop_btn, self.binary_undo_btn
            ]
            for btn in disable_buttons:
                btn.config(state=state)

    def _update_step_preview(self):
        if self.step_frames and self.step_idx < len(self.step_frames):
            cid, data, is_ext = self.step_frames[self.step_idx]
            ext_str = " (EXT)" if is_ext else ""
            self.step_preview.config(text=f"Następna: ID=0x{cid:08X}{ext_str} Data={data.hex().upper()}")
        else:
            self.step_preview.config(text="Koniec listy")

    def _start_sim(self):
        if self.sim_thread and self.sim_thread.is_alive():
            self.sim_thread.stop()
            self.sim_thread.join(timeout=0.5)
        self.sim_thread = SimulationThread(self.can, self.log)

    def _simulation_started(self):
        self.replay_start_btn.config(text="Wznów", state='normal')
        self.replay_pause_btn.config(state='normal')
        self.replay_stop_btn.config(state='normal')

    def pause_sim(self):
        if self.sim_thread:
            self.sim_thread.pause()
            self.replay_start_btn.config(text="Wznów", state='normal')
            self.log("Pauza")

    def stop_sim(self):
        if self.sim_thread:
            self.sim_thread.stop()
            self.log("Zatrzymano")
        self.replay_start_btn.config(text="Start", state='normal')
        self.replay_pause_btn.config(state='disabled')
        self.replay_stop_btn.config(state='disabled')

    # Wyszukiwanie binarne – pomocnicze
    def _start_binary_thread(self, ask_callback):
        mode = self.binary_mode.get()
        num_parts = self.binary_parts.get() if mode == 'manual_parts' else 2
        self.binary_thread = BinarySearchThread(
            self.can, self.log, ask_callback, self._binary_done, self._update_binary_progress
        )
        self.binary_thread.setup(
            self.binary_frames,
            self.binary_interval.get(),
            mode=mode,
            num_parts=num_parts,
            use_timestamps=self.binary_use_timestamps.get()
        )

    def _update_binary_progress(self):
        if self.binary_thread:
            left = self.binary_thread.left
            right = self.binary_thread.right
            mid = self.binary_thread.mid
            total = len(self.binary_frames)
            self.binary_progress.config(text=f"Zakres: [{left} .. {right}]  środek: {mid}  (razem: {total})")
            self._redraw_binary_progress()

    def _redraw_binary_progress(self):
        if not hasattr(self, 'binary_canvas') or not self.binary_frames:
            return
        canvas = self.binary_canvas
        canvas.delete("all")
        total = len(self.binary_frames)
        if total == 0:
            return
        width = canvas.winfo_width()
        if width <= 10:
            width = 600

        if self.binary_thread and self.binary_thread.running:
            left = self.binary_thread.left
            right = self.binary_thread.right
            mid = self.binary_thread.mid
        else:
            left, right = 0, total - 1
            mid = (left + right) // 2

        def idx_to_x(idx):
            return int((idx / (total - 1)) * width) if total > 1 else 0

        x_left = idx_to_x(left)
        x_right = idx_to_x(right)
        x_mid = idx_to_x(mid)

        canvas.create_rectangle(0, 0, width, 30, fill='lightgray', outline='')
        canvas.create_rectangle(x_left, 0, x_right, 30, fill='lightgreen', outline='darkgreen')
        canvas.create_line(x_mid, 0, x_mid, 30, fill='red', width=2)
        canvas.create_text(x_left, 15, text=str(left), anchor='e', font=('Arial', 8))
        canvas.create_text(x_right, 15, text=str(right), anchor='w', font=('Arial', 8))
        canvas.create_text(x_mid, 0, text=str(mid), anchor='s', font=('Arial', 8, 'bold'), fill='red')

    def _binary_done(self):
        self.binary_start_btn.config(state='normal')
        for btn in [self.binary_yes_btn, self.binary_no_btn, self.binary_stop_btn, self.binary_undo_btn]:
            btn.config(state='disabled')
        if hasattr(self, 'binary_export_btn') and self.binary_export_btn:
            self.binary_export_btn.config(state='disabled')
        self.binary_progress.config(text="Wyszukiwanie zakończone.")
        self._redraw_binary_progress()

    # Kreator
    def _update_wizard_progress(self):
        if self.wizard_frames:
            total = len(self.wizard_frames)
            self.wizard_progress.config(text=f"Zakres: [{self.wizard_left} .. {self.wizard_right}] (razem: {total})")
            self._redraw_wizard_progress()

    def _redraw_wizard_progress(self):
        canvas = self.wizard_canvas
        canvas.delete("all")
        total = len(self.wizard_frames)
        if total == 0:
            return
        width = canvas.winfo_width()
        if width <= 10:
            width = 600

        left, right = self.wizard_left, self.wizard_right

        def idx_to_x(idx):
            return int((idx / (total - 1)) * width) if total > 1 else 0

        x_left = idx_to_x(left)
        x_right = idx_to_x(right)
        mid = (left + right) // 2
        x_mid = idx_to_x(mid)

        canvas.create_rectangle(0, 0, width, 30, fill='lightgray', outline='')
        canvas.create_rectangle(x_left, 0, x_right, 30, fill='lightblue', outline='darkblue')
        canvas.create_line(x_mid, 0, x_mid, 30, fill='red', width=2)
        canvas.create_text(x_left, 15, text=str(left), anchor='e', font=('Arial', 8))
        canvas.create_text(x_right, 15, text=str(right), anchor='w', font=('Arial', 8))
        canvas.create_text(x_mid, 0, text=str(mid), anchor='s', font=('Arial', 8, 'bold'), fill='red')

    def on_closing(self):
        self.manual_cyclic_active = False
        if self.sim_thread:
            self.sim_thread.stop()
        if self.binary_thread:
            self.binary_thread.stop()
        self.can.disconnect()
        self.root.destroy()
