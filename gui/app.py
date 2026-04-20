import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
from datetime import datetime
import threading
import time
import logging

from can_interface import CanInterface
from threads import SimulationThread, BinarySearchThread
from gui.tabs import replay_tab, missing_tab, error_tab, step_tab, manual_tab, binary_tab
from gui.utils import write_log_to_file

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
        frame_conn = ttk.LabelFrame(self.root, text="Połączenie CAN", padding=5)
        frame_conn.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(frame_conn, text="Interfejs:").grid(row=0, column=0, sticky=tk.W)
        self.entry_iface = ttk.Entry(frame_conn, width=15)
        self.entry_iface.insert(0, "can0")
        self.entry_iface.grid(row=0, column=1, padx=5)

        self.btn_connect = ttk.Button(frame_conn, text="Połącz", command=self.toggle_connection)
        self.btn_connect.grid(row=0, column=2, padx=5)

        self.lbl_status = ttk.Label(frame_conn, text="Niepołączony", foreground="red")
        self.lbl_status.grid(row=0, column=3, padx=10)

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

        frame_log = ttk.LabelFrame(self.root, text="Log", padding=5)
        frame_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.log_text = scrolledtext.ScrolledText(frame_log, height=12, state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.status_var = tk.StringVar(value="Gotowy.")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN).pack(fill=tk.X, padx=10, pady=2)

    def toggle_connection(self):
        if self.can.connected:
            self.can.disconnect()
            self.lbl_status.config(text="Niepołączony", foreground="red")
            self.btn_connect.config(text="Połącz")
            self._set_buttons_state('disabled')
        else:
            iface = self.entry_iface.get().strip()
            if not iface:
                messagebox.showerror("Błąd", "Podaj nazwę interfejsu")
                return
            success, msg = self.can.connect()
            if success:
                self.lbl_status.config(text=f"Połączony: {iface}", foreground="green")
                self.btn_connect.config(text="Rozłącz")
                self._set_buttons_state('normal')
                self.log(msg)
            else:
                messagebox.showerror("Błąd", msg)

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

    def step_next(self):
        if not self.step_frames or self.step_idx >= len(self.step_frames):
            messagebox.showinfo("Koniec", "Wszystkie ramki zostały wysłane")
            return
        if not self.can.connected:
            messagebox.showerror("Błąd", "Połącz się z CAN")
            return
        cid, data, is_ext = self.step_frames[self.step_idx]
        success, msg = self.can.send_frame(cid, data, is_ext)
        self.log(msg)
        self.step_idx += 1
        self.step_progress.config(text=f"{self.step_idx} / {len(self.step_frames)}")
        self._update_step_preview()

    def start_replay(self):
        if not self.loaded_frames:
            messagebox.showerror("Błąd", "Najpierw wczytaj plik")
            return
        self._start_sim()
        self.sim_thread.setup_replay(
            self.loaded_frames,
            self.replay_interval.get(),
            self.replay_loop.get(),
            self.replay_speed.get()
        )
        self.sim_thread.start()
        self._simulation_started()

    def start_missing(self):
        self._start_sim()
        self.sim_thread.setup_missing_module(
            self.missing_8f.get(),
            self.missing_diag.get(),
            self.missing_spor.get()
        )
        self.sim_thread.mode = 'missing'
        self.sim_thread.start()
        self._simulation_started()

    def start_error(self):
        self._start_sim()
        try:
            code = int(self.error_code.get().strip(), 16)
        except ValueError:
            code = 0x19
        self.sim_thread.setup_error_frames(self.error_interval.get(), code)
        self.sim_thread.mode = 'error'
        self.sim_thread.start()
        self._simulation_started()

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

    def manual_send_once(self):
        if not self.can.connected:
            messagebox.showerror("Błąd", "Połącz się z CAN")
            return
        try:
            can_id = int(self.manual_id.get().strip(), 16)
            data = bytes.fromhex(self.manual_data.get().strip())
        except ValueError:
            messagebox.showerror("Błąd", "Nieprawidłowy format ID lub danych")
            return
        success, msg = self.can.send_frame(can_id, data, self.manual_extended.get())
        self.log(msg)

    def manual_start_cyclic(self):
        if not self.can.connected:
            messagebox.showerror("Błąd", "Połącz się z CAN")
            return
        try:
            can_id = int(self.manual_id.get().strip(), 16)
            data = bytes.fromhex(self.manual_data.get().strip())
        except ValueError:
            messagebox.showerror("Błąd", "Nieprawidłowy format")
            return
        interval = self.manual_interval.get()
        if interval <= 0:
            messagebox.showerror("Błąd", "Interwał musi być > 0")
            return

        self.manual_cyclic_active = True
        self.manual_start_btn.config(state='disabled')
        self.manual_send_once_btn.config(state='disabled')
        self.manual_stop_btn.config(state='normal')

        def worker():
            while self.manual_cyclic_active:
                success, msg = self.can.send_frame(can_id, data, self.manual_extended.get())
                self.log(msg)
                time.sleep(interval)

        self.manual_cyclic_thread = threading.Thread(target=worker, daemon=True)
        self.manual_cyclic_thread.start()

    def manual_stop_cyclic(self):
        self.manual_cyclic_active = False
        self.manual_start_btn.config(state='normal')
        self.manual_send_once_btn.config(state='normal')
        self.manual_stop_btn.config(state='disabled')
        self.log("Zatrzymano wysyłanie cykliczne")

    # ---------- Wyszukiwanie binarne / polowanie ----------
    def start_binary_search(self):
        if not self.binary_frames:
            messagebox.showerror("Błąd", "Najpierw wczytaj plik")
            return
        if not self.can.connected:
            messagebox.showerror("Błąd", "Połącz się z CAN")
            return

        mode = self.binary_mode.get()
        if mode == 'hunt_deactivator':
            self._start_hunting()
            return

        self.binary_start_btn.config(state='disabled')
        self.binary_yes_btn.config(state='normal')
        self.binary_no_btn.config(state='normal')
        self.binary_stop_btn.config(state='normal')
        self.binary_undo_btn.config(state='normal')

        num_parts = self.binary_parts.get() if mode == 'manual_parts' else 2
        self.binary_answer = None
        self.binary_answer_event = threading.Event()

        def ask_callback(prompt="Czy zjawisko wystąpiło?", input_type='yesno', choices=None, default=None):
            self.binary_answer_event.clear()
            self.log(f"[Binary] {prompt}")
            if input_type == 'yesno':
                self.binary_answer_event.wait()
                return self.binary_answer
            elif input_type == 'choice':
                choice = simpledialog.askinteger("Wybór", prompt, minvalue=1, maxvalue=len(choices))
                self.binary_answer_event.set()
                return choice - 1 if choice is not None else None
            elif input_type == 'integer':
                val = simpledialog.askinteger("Liczba części", prompt, initialvalue=default)
                self.binary_answer_event.set()
                return val
            else:
                self.binary_answer_event.wait()
                return self.binary_answer

        self.binary_thread = BinarySearchThread(
            self.can, self.log, ask_callback, self._binary_done, self._update_binary_progress
        )
        self.binary_thread.setup(self.binary_frames, self.binary_interval.get(), mode, num_parts)
        self.binary_thread.start()
        self._update_binary_progress()

    def _start_hunting(self):
        try:
            alert_id = int(self.hunt_alert_id.get().strip(), 16)
        except ValueError:
            messagebox.showerror("Błąd", "Nieprawidłowy format ID alertu")
            return

        period = self.hunt_period.get()
        tolerance = self.hunt_tolerance.get()
        interval = self.binary_interval.get()

        self.binary_start_btn.config(state='disabled')
        self.binary_stop_btn.config(state='normal')
        self.binary_yes_btn.config(state='disabled')
        self.binary_no_btn.config(state='disabled')
        self.binary_undo_btn.config(state='disabled')

        self.binary_thread = BinarySearchThread(
            self.can, self.log, None, self._hunting_done, self._update_hunting_status
        )
        self.binary_thread.setup_hunting(self.binary_frames, interval, alert_id, period, tolerance)
        self.binary_thread.deactivation_callback = self._on_deactivation
        self.binary_thread.start()
        self.binary_progress.config(text="Tryb polowania aktywny...")
        self.log("[Polowanie] Rozpoczęto.")

    def _on_deactivation(self, candidates):
        self.log(f"[Polowanie] Wykryto dezaktywację! Znaleziono {len(candidates)} kandydatów.")
        for i, (cid, data, is_ext, ts) in enumerate(candidates[:5]):
            self.log(f"  Kandydat {i+1}: ID=0x{cid:08X} Data={data.hex().upper()}")
        self.binary_progress.config(text=f"Dezaktywacja! {len(candidates)} kandydatów.")

    def _hunting_done(self):
        self.binary_start_btn.config(state='normal')
        self.binary_stop_btn.config(state='disabled')
        self.binary_progress.config(text="Polowanie zakończone.")

    def _update_hunting_status(self):
        pass

    def binary_answer_yes(self):
        if self.binary_thread and self.binary_thread.is_alive():
            self.binary_answer = True
            self.binary_answer_event.set()
            self.log("[Binary] TAK")
            self._update_binary_progress()

    def binary_answer_no(self):
        if self.binary_thread and self.binary_thread.is_alive():
            self.binary_answer = False
            self.binary_answer_event.set()
            self.log("[Binary] NIE")
            self._update_binary_progress()

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
        self.binary_progress.config(text="Wyszukiwanie zakończone.")
        self._redraw_binary_progress()

    def stop_binary_search(self):
        if self.binary_thread:
            self.binary_thread.stop()
        self._binary_done()
        self.log("[Binary] Zatrzymano.")

    def on_closing(self):
        self.manual_cyclic_active = False
        if self.sim_thread:
            self.sim_thread.stop()
        if self.binary_thread:
            self.binary_thread.stop()
        self.can.disconnect()
        self.root.destroy()
