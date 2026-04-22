import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import time
import logging
from collections import deque

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

logger = logging.getLogger(__name__)


class AnomalyTab:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.detector = None
        self.monitoring = False
        self.anomaly_scores = deque(maxlen=200)
        self.timestamps = deque(maxlen=200)
        self.start_time = None

        if MATPLOTLIB_AVAILABLE:
            self._setup_plot()          # <-- najpierw tworzymy fig
        self._create_widgets()          # potem widgety (użyją self.fig)

    def _create_widgets(self):
        control_frame = ttk.LabelFrame(self.parent, text="Kontrola", padding=10)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(control_frame, text="Wielkość okna:").grid(row=0, column=0, sticky=tk.W)
        self.window_var = tk.IntVar(value=10)
        ttk.Spinbox(control_frame, from_=5, to=50, textvariable=self.window_var, width=5).grid(row=0, column=1, padx=5)

        ttk.Label(control_frame, text="Próg percentyla:").grid(row=0, column=2, sticky=tk.W, padx=(20,0))
        self.threshold_var = tk.IntVar(value=95)
        ttk.Spinbox(control_frame, from_=80, to=99, textvariable=self.threshold_var, width=5).grid(row=0, column=3, padx=5)

        self.monitor_btn = ttk.Button(control_frame, text="Start monitorowania", command=self.toggle_monitoring)
        self.monitor_btn.grid(row=0, column=4, padx=20)

        self.status_var = tk.StringVar(value="Zatrzymane")
        ttk.Label(control_frame, textvariable=self.status_var).grid(row=0, column=5, padx=10)

        # Wykres
        if MATPLOTLIB_AVAILABLE:
            plot_frame = ttk.LabelFrame(self.parent, text="Anomaly Score", padding=10)
            plot_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Log anomalii
        log_frame = ttk.LabelFrame(self.parent, text="Wykryte anomalie", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text = tk.Text(log_frame, height=8, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _setup_plot(self):
        self.fig = Figure(figsize=(6, 3), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel("Czas (s)")
        self.ax.set_ylabel("Anomaly Score")
        self.ax.grid(True)
        self.threshold_line = self.ax.axhline(y=0, color='r', linestyle='--', label='Próg')
        self.line, = self.ax.plot([], [], 'b-', label='Score')
        self.ax.legend()

    def toggle_monitoring(self):
        if not self.monitoring:
            self.start_monitoring()
        else:
            self.stop_monitoring()

    def start_monitoring(self):
        from ml.advanced_models import CANAnomalyDetector
        self.detector = CANAnomalyDetector(
            window_size=self.window_var.get(),
            threshold_percentile=self.threshold_var.get()
        )
        if hasattr(self.app, 'can') and hasattr(self.app.can, 'add_frame_callback'):
            self.app.can.add_frame_callback(self._on_can_frame)
        else:
            messagebox.showerror("Błąd", "Interfejs CAN nie obsługuje callbacków.")
            return

        self.monitoring = True
        self.start_time = time.time()
        self.monitor_btn.config(text="Stop monitorowania")
        self.status_var.set("Monitorowanie aktywne")
        self._log("Monitorowanie rozpoczęte.")

    def stop_monitoring(self):
        self.monitoring = False
        self.monitor_btn.config(text="Start monitorowania")
        self.status_var.set("Zatrzymane")
        self._log("Monitorowanie zatrzymane.")

    def _on_can_frame(self, frame):
        if not self.monitoring or not self.detector:
            return
        score = self.detector.process_frame(frame)
        if score is not None:
            t = time.time() - self.start_time
            self.anomaly_scores.append(score)
            self.timestamps.append(t)
            self.parent.after(0, self._update_plot)
            if self.detector.is_anomaly(score):
                self.parent.after(0, lambda: self._log_anomaly(score, frame))

    def _update_plot(self):
        if not MATPLOTLIB_AVAILABLE or not self.timestamps:
            return
        self.line.set_data(list(self.timestamps), list(self.anomaly_scores))
        if self.detector and self.detector.threshold:
            self.threshold_line.set_ydata([self.detector.threshold, self.detector.threshold])
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()

    def _log_anomaly(self, score, frame):
        msg = f"ANOMALIA: score={score:.4f} (próg={self.detector.threshold:.4f}), ID={frame['id']}, data={frame['data']}"
        self._log(msg)
        if hasattr(self.app, 'remote_monitor_tab') and self.app.remote_monitor_tab.server:
            self.app.remote_monitor_tab.server._send_telegram(f"⚠️ {msg}")

    def _log(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)


def setup_anomaly_tab(app, parent):
    AnomalyTab(parent, app)
