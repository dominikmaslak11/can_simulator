import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import logging
from datetime import datetime

from can_interface import CanInterface
from gui.tabs import replay_tab, missing_tab, error_tab, step_tab, manual_tab, binary_tab
from gui.handlers import ConnectionHandlers
from gui.simulation_handlers import SimulationHandlers
from gui.binary_handlers import BinaryHandlers

logger = logging.getLogger("App")


class CanSimulatorApp(ConnectionHandlers, SimulationHandlers, BinaryHandlers):
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
                from gui.utils import write_log_to_file
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

    def on_closing(self):
        self.manual_cyclic_active = False
        if self.sim_thread:
            self.sim_thread.stop()
        if self.binary_thread:
            self.binary_thread.stop()
        self.can.disconnect()
        self.root.destroy()
