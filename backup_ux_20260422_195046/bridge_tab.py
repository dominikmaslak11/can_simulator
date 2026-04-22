import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from bridge_client import VCanBridge

logger = logging.getLogger(__name__)


class BridgeTab:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.bridge = None
        self.bridge_thread = None
        self.status_queue = queue.Queue()
        self.running = False

        self._create_widgets()
        self._process_queue()

    def _create_widgets(self):
        frame = ttk.LabelFrame(self.parent, text="Mostek WebSocket → vcan0", padding=10)
        frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(frame, text="Adres WebSocket:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.url_var = tk.StringVar(value="ws://localhost:8765")
        ttk.Entry(frame, textvariable=self.url_var, width=40).grid(row=0, column=1, padx=5)

        ttk.Label(frame, text="Token (opcjonalny):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.token_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.token_var, width=30, show="*").grid(row=1, column=1, padx=5)

        ttk.Label(frame, text="Filtruj ID (opcjonalnie):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.filter_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.filter_var, width=40).grid(row=2, column=1, padx=5)
        ttk.Label(frame, text="(lista oddzielona przecinkami, np. 0x123,0x456)").grid(row=3, column=1, sticky=tk.W, padx=5)

        self.auto_reconnect_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="Automatycznie ponawiaj połączenie", variable=self.auto_reconnect_var).grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)

        self.start_btn = ttk.Button(btn_frame, text="Start mostka", command=self.start_bridge)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.stop_btn = ttk.Button(btn_frame, text="Stop mostka", command=self.stop_bridge, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        status_frame = ttk.LabelFrame(self.parent, text="Status", padding=10)
        status_frame.pack(fill=tk.X, padx=10, pady=5)

        self.status_var = tk.StringVar(value="Zatrzymany")
        ttk.Label(status_frame, textvariable=self.status_var).pack(anchor=tk.W)

        log_frame = ttk.LabelFrame(self.parent, text="Log", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.log_text = tk.Text(log_frame, height=10, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _process_queue(self):
        try:
            while True:
                msg = self.status_queue.get_nowait()
                self._append_log(msg)
        except queue.Empty:
            pass
        finally:
            self.parent.after(100, self._process_queue)

    def _append_log(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _status_callback(self, msg):
        self.status_queue.put(msg)

    def start_bridge(self):
        url = self.url_var.get().strip()
        token = self.token_var.get().strip() or None

        # Parsowanie filtrów ID
        filter_str = self.filter_var.get().strip()
        filter_ids = None
        if filter_str:
            try:
                filter_ids = [int(x.strip(), 16) if x.strip().startswith('0x') else int(x.strip())
                              for x in filter_str.split(',')]
            except ValueError:
                messagebox.showerror("Błąd", "Nieprawidłowy format listy ID. Użyj liczb dziesiętnych lub szesnastkowych z 0x.")
                return

        self.bridge = VCanBridge(
            url=url,
            token=token,
            filter_ids=filter_ids,
            auto_reconnect=self.auto_reconnect_var.get(),
            status_callback=self._status_callback
        )
        self.bridge_thread = threading.Thread(target=self._run_bridge, daemon=True)
        self.bridge_thread.start()

        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_var.set("Uruchomiony")
        self._append_log("Mostek uruchomiony.")

    def _run_bridge(self):
        self.bridge.start()
        self.parent.after(0, self._bridge_stopped)

    def stop_bridge(self):
        if self.bridge:
            self.bridge.stop()
        self._bridge_stopped()

    def _bridge_stopped(self):
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set("Zatrzymany")
        self._append_log("Mostek zatrzymany.")


def setup_bridge_tab(app, parent):
    BridgeTab(parent, app)
