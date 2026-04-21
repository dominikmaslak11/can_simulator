import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import logging
import threading
import time
from datetime import datetime

# Interfejsy CAN
from socketcan_interface import SocketCANInterface
from dummy_interface import DummyInterface

# Zakładki i mixiny
from gui.tabs import replay_tab, missing_tab, error_tab, step_tab, manual_tab, binary_tab
from gui.handlers import ConnectionHandlers
from gui.simulation_handlers import SimulationHandlers
from gui.binary_handlers import BinaryHandlers

# Nowe komponenty
from sequence_analyzer import SequenceAnalyzer
from session_manager import SessionManager
from report_generator import ReportGenerator

logger = logging.getLogger("App")


class CanSimulatorApp(ConnectionHandlers, SimulationHandlers, BinaryHandlers):
    def __init__(self, root):
        self.root = root
        self.root.title("CAN Simulator GUI")
        self.root.geometry("1000x850")

        # Interfejs CAN tworzony dynamicznie przy połączeniu
        self.can = None
        self.sim_thread = None
        self.binary_thread = None
        self.loaded_frames = []
        self.step_frames = []
        self.step_idx = 0
        self.binary_frames = []

        self.manual_cyclic_active = False
        self.manual_cyclic_thread = None

        # Analizator sekwencji (używany w BinaryHandlers)
        self.seq_analyzer = SequenceAnalyzer()

        self._create_widgets()
        self._create_menu()
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
                from gui.utils import write_log_to_file
                write_log_to_file(log_path, msg)

    def _create_widgets(self):
        # --- Ramka połączenia CAN ---
        frame_conn = ttk.LabelFrame(self.root, text="Połączenie CAN", padding=5)
        frame_conn.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(frame_conn, text="Interfejs:").grid(row=0, column=0, sticky=tk.W)
        self.entry_iface = ttk.Entry(frame_conn, width=15)
        self.entry_iface.insert(0, "can0")
        self.entry_iface.grid(row=0, column=1, padx=5)

        # Checkbox trybu offline
        self.offline_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame_conn, text="Tryb offline (bez CAN)", variable=self.offline_mode).grid(
            row=0, column=2, padx=5)

        self.btn_connect = ttk.Button(frame_conn, text="Połącz", command=self.toggle_connection)
        self.btn_connect.grid(row=0, column=3, padx=5)

        self.lbl_status = ttk.Label(frame_conn, text="Niepołączony", foreground="red")
        self.lbl_status.grid(row=0, column=4, padx=10)

        # --- Zakładki ---
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

        # --- Log ---
        frame_log = ttk.LabelFrame(self.root, text="Log", padding=5)
        frame_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.log_text = scrolledtext.ScrolledText(frame_log, height=12, state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.status_var = tk.StringVar(value="Gotowy.")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN).pack(fill=tk.X, padx=10, pady=2)

    def _create_menu(self):
        """Tworzy górne menu Plik."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Plik", menu=file_menu)
        file_menu.add_command(label="Zapisz sesję jako...", command=self.save_session)
        file_menu.add_command(label="Wczytaj sesję...", command=self.load_session)
        file_menu.add_separator()
        file_menu.add_command(label="Generuj raport...", command=self.generate_report)
        file_menu.add_separator()
        file_menu.add_command(label="Wyjście", command=self.on_closing)

    def toggle_connection(self):
        """Nadpisuje metodę z ConnectionHandlers, aby używała dynamicznego interfejsu."""
        if self.can and self.can.connected:
            self.can.disconnect()
            self.lbl_status.config(text="Niepołączony", foreground="red")
            self.btn_connect.config(text="Połącz")
            self._set_buttons_state('disabled')
        else:
            iface = self.entry_iface.get().strip()
            if not iface:
                messagebox.showerror("Błąd", "Podaj nazwę interfejsu")
                return

            # Wybór odpowiedniej implementacji interfejsu CAN
            if self.offline_mode.get():
                self.can = DummyInterface(iface)
            else:
                self.can = SocketCANInterface(iface)

            success, msg = self.can.connect()
            if success:
                self.lbl_status.config(text=f"Połączony: {iface}", foreground="green")
                self.btn_connect.config(text="Rozłącz")
                self._set_buttons_state('normal')
                self.log(msg)
            else:
                messagebox.showerror("Błąd", msg)

    # ----------------------------------------------------------------------
    # Zarządzanie sesjami
    # ----------------------------------------------------------------------
    def save_session(self):
        """Zapisuje stan aplikacji do pliku .cansession."""
        if not self.loaded_frames and not self.binary_frames:
            messagebox.showinfo("Brak danych", "Brak wczytanych ramek do zapisania.")
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".cansession",
            filetypes=[("Pliki sesji CAN Simulator", "*.cansession"), ("Wszystkie pliki", "*.*")]
        )
        if not filepath:
            return

        state = {
            "replay": {
                "file_path": self.replay_file_var.get(),
                "interval": self.replay_interval.get(),
                "speed": self.replay_speed.get(),
                "loop": self.replay_loop.get(),
                "log_enable": self.replay_log_enable.get(),
                "log_path": self.replay_log_var.get(),
            },
            "binary": {
                "file_path": self.binary_file_var.get(),
                "interval": self.binary_interval.get(),
                "mode": self.binary_mode.get(),
                "parts": self.binary_parts.get(),
                "hunt_alert_id": self.hunt_alert_id.get(),
                "hunt_period": self.hunt_period.get(),
                "hunt_tolerance": self.hunt_tolerance.get(),
                "hunt_start_index": self.hunt_start_index.get(),
            },
            "frames": {
                "loaded": [(cid, data.hex(), is_ext) for (cid, data, is_ext) in self.loaded_frames],
                "binary": [(cid, data.hex(), is_ext) for (cid, data, is_ext) in self.binary_frames],
            },
            "history": {
                "binary_history": getattr(self.binary_thread, 'history', []) if self.binary_thread else []
            }
        }
        SessionManager.save_session(filepath, state)
        self.log(f"Sesja zapisana do {filepath}")
        messagebox.showinfo("Sesja zapisana", f"Sesja została zapisana do:\n{filepath}")

    def load_session(self):
        """Wczytuje stan aplikacji z pliku .cansession."""
        filepath = filedialog.askopenfilename(
            filetypes=[("Pliki sesji CAN Simulator", "*.cansession"), ("Wszystkie pliki", "*.*")]
        )
        if not filepath:
            return
        state = SessionManager.load_session(filepath)
        if state is None:
            messagebox.showerror("Błąd", "Nie udało się wczytać pliku sesji.")
            return

        try:
            # Przywracanie stanu odtwarzania
            r = state.get("replay", {})
            self.replay_file_var.set(r.get("file_path", ""))
            self.replay_interval.set(r.get("interval", 0.5))
            self.replay_speed.set(r.get("speed", 1.0))
            self.replay_loop.set(r.get("loop", True))
            self.replay_log_enable.set(r.get("log_enable", False))
            self.replay_log_var.set(r.get("log_path", ""))

            # Przywracanie stanu wyszukiwania binarnego
            b = state.get("binary", {})
            self.binary_file_var.set(b.get("file_path", ""))
            self.binary_interval.set(b.get("interval", 0.1))
            self.binary_mode.set(b.get("mode", "find_start"))
            self.binary_parts.set(b.get("parts", 2))
            self.hunt_alert_id.set(b.get("hunt_alert_id", "0C00008F"))
            self.hunt_period.set(b.get("hunt_period", 1.0))
            self.hunt_tolerance.set(b.get("hunt_tolerance", 0.2))
            self.hunt_start_index.set(b.get("hunt_start_index", 0))

            # Przywracanie wczytanych ramek
            frames_data = state.get("frames", {})
            loaded = frames_data.get("loaded", [])
            if loaded:
                self.loaded_frames = [(cid, bytes.fromhex(data), is_ext) for (cid, data, is_ext) in loaded]
                self.replay_info.config(text=f"Wczytano {len(self.loaded_frames)} ramek (z sesji)")
            binary_frames = frames_data.get("binary", [])
            if binary_frames:
                self.binary_frames = [(cid, bytes.fromhex(data), is_ext) for (cid, data, is_ext) in binary_frames]
                self.binary_info.config(text=f"Wczytano {len(self.binary_frames)} ramek (z sesji)")
                self.binary_start_btn.config(state='normal')
                self._redraw_binary_progress()

            # Historia wyszukiwania
            hist = state.get("history", {}).get("binary_history", [])
            if self.binary_thread:
                self.binary_thread.history = hist
            elif hist:
                from threads import BinarySearchThread
                self.binary_thread = BinarySearchThread(self.can, self.log, None, lambda: None)
                self.binary_thread.history = hist

            self.log(f"Sesja wczytana z {filepath}")
            messagebox.showinfo("Sesja wczytana", f"Sesja została wczytana z:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się wczytać sesji: {e}")

    def use_in_simulation(self, can_id, data, is_extended):
        """Wypełnia pola w zakładce Symulacja modułu / Ręczne wysyłanie."""
        self.manual_id.set(f"{can_id:08X}")
        self.manual_data.set(data.hex().upper())
        self.manual_extended.set(is_extended)
        self.notebook.select(self.tab_manual)
        self.log(f"Przekazano ID=0x{can_id:08X} do symulacji.")

    def quick_test_alert(self, can_id, data, is_extended, period=1.0, duration=10.0):
        """
        Uruchamia krótki test wysyłania ramki przez określony czas.
        """
        if not self.can or not self.can.connected:
            messagebox.showerror("Błąd", "Połącz się z CAN przed testem.")
            return

        def _test_worker():
            self.log(f"[Test alertu] Rozpoczęto wysyłanie ID=0x{can_id:08X} co {period}s przez {duration}s")
            end_time = time.time() + duration
            while time.time() < end_time:
                success, msg = self.can.send_frame(can_id, data, is_extended)
                if success:
                    self.log(f"[Test alertu] {msg}")
                else:
                    self.log(f"[Test alertu] Błąd: {msg}")
                    break
                time.sleep(period)
            self.log("[Test alertu] Zakończono.")

        threading.Thread(target=_test_worker, daemon=True).start()

    def generate_report(self):
        """Generuje raport z bieżącej sesji i zapisuje do pliku."""
        state = {
            "replay": {
                "file_path": self.replay_file_var.get(),
                "interval": self.replay_interval.get(),
                "speed": self.replay_speed.get(),
                "loop": self.replay_loop.get(),
            },
            "binary": {
                "file_path": self.binary_file_var.get(),
                "interval": self.binary_interval.get(),
                "mode": self.binary_mode.get(),
                "hunt_alert_id": self.hunt_alert_id.get(),
                "hunt_period": self.hunt_period.get(),
                "hunt_tolerance": self.hunt_tolerance.get(),
                "hunt_start_index": self.hunt_start_index.get(),
            },
            "frames": {
                "loaded": [(cid, data.hex(), is_ext) for (cid, data, is_ext) in self.loaded_frames],
                "binary": [(cid, data.hex(), is_ext) for (cid, data, is_ext) in self.binary_frames],
            },
            "history": {
                "binary_history": getattr(self.binary_thread, 'history', []) if self.binary_thread else []
            }
        }

        report_text = ReportGenerator.generate(state)

        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Pliki tekstowe", "*.txt"), ("Wszystkie pliki", "*.*")]
        )
        if not filepath:
            return

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_text)
            self.log(f"Raport zapisany do {filepath}")
            messagebox.showinfo("Raport zapisany", f"Raport został zapisany do:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się zapisać raportu: {e}")

    def on_closing(self):
        self.manual_cyclic_active = False
        if self.sim_thread:
            self.sim_thread.stop()
        if self.binary_thread:
            self.binary_thread.stop()
        if self.can:
            self.can.disconnect()
        self.root.destroy()
