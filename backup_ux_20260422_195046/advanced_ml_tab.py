import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import threading
import numpy as np
from collections import defaultdict

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import seaborn as sns
    SEABORN_AVAILABLE = True
except ImportError:
    SEABORN_AVAILABLE = False

from parsers import load_frames_from_file
from ml.advanced_models import SignalForecaster



class ProgressDialog(tk.Toplevel):
    """Okno dialogowe z paskiem postępu i przyciskiem Anuluj."""
    def __init__(self, parent, title="Operacja w toku", maximum=100):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)

        self.cancel_event = threading.Event()

        self.label = ttk.Label(self, text="Proszę czekać...")
        self.label.pack(pady=10, padx=20)

        self.progress = ttk.Progressbar(self, length=300, mode='determinate', maximum=maximum)
        self.progress.pack(pady=5, padx=20)

        self.cancel_btn = ttk.Button(self, text="Anuluj", command=self.on_cancel)
        self.cancel_btn.pack(pady=10)

        self.update_idletasks()
        self.geometry(f"+{parent.winfo_rootx()+50}+{parent.winfo_rooty()+50}")

    def on_cancel(self):
        self.cancel_event.set()
        self.label.config(text="Anulowanie...")
        self.cancel_btn.config(state='disabled')

    def update_progress(self, value, text=None):
        if not self.cancel_event.is_set():
            self.progress['value'] = value
            if text:
                self.label.config(text=text)
            self.update_idletasks()

    def close(self):
        self.destroy()

def setup_advanced_ml_tab(app, tab):
    if not MATPLOTLIB_AVAILABLE:
        ttk.Label(tab, text="Brak matplotlib.", foreground="red").pack(pady=20)
        return

    sub_notebook = ttk.Notebook(tab)
    sub_notebook.pack(fill=tk.BOTH, expand=True)

    # Podzakładka 1: Prognozowanie
    forecast_frame = ttk.Frame(sub_notebook)
    sub_notebook.add(forecast_frame, text="Prognozowanie (LSTM)")
    setup_forecast_tab(app, forecast_frame)

    # Podzakładka 2: Korelacja
    corr_frame = ttk.Frame(sub_notebook)
    sub_notebook.add(corr_frame, text="Korelacja sygnałów")
    setup_correlation_tab(app, corr_frame)

    # Podzakładka 3: Eksplorator
    explore_frame = ttk.Frame(sub_notebook)
    sub_notebook.add(explore_frame, text="Eksplorator danych")
    setup_explorer_tab(app, explore_frame)


def setup_forecast_tab(app, frame):
    ttk.Label(frame, text="Plik z danymi:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
    file_var = tk.StringVar()
    ttk.Entry(frame, textvariable=file_var, width=50).grid(row=0, column=1, padx=5)
    ttk.Button(frame, text="Przeglądaj", command=lambda: browse_file(file_var)).grid(row=0, column=2)

    ttk.Label(frame, text="ID ramki:").grid(row=1, column=0, sticky=tk.W, padx=5)
    id_var = tk.StringVar()
    ttk.Entry(frame, textvariable=id_var, width=15).grid(row=1, column=1, sticky=tk.W, padx=5)

    ttk.Label(frame, text="Bajt:").grid(row=2, column=0, sticky=tk.W, padx=5)
    byte_var = tk.IntVar(value=0)
    ttk.Spinbox(frame, from_=0, to=7, textvariable=byte_var, width=5).grid(row=2, column=1, sticky=tk.W, padx=5)

    ttk.Label(frame, text="Liczba kroków prognozy:").grid(row=3, column=0, sticky=tk.W, padx=5)
    steps_var = tk.IntVar(value=50)
    ttk.Spinbox(frame, from_=10, to=500, textvariable=steps_var, width=5).grid(row=3, column=1, sticky=tk.W, padx=5)

    ttk.Label(frame, text="lub sygnał z DBC:").grid(row=4, column=0, sticky=tk.W, padx=5)
    forecast_signal_combo = ttk.Combobox(frame, state="readonly", width=40)
    forecast_signal_combo.bind("<Button-1>", lambda e: forecast_signal_combo.configure(values=app.dbc_signals if hasattr(app, "dbc_signals") else []))

    def on_signal_selected(event):
        selected = forecast_signal_combo.get()
        if not selected or not hasattr(app, 'dbc_manager'):
            return
        try:
            msg_name, sig_name = selected.split('.')
            db = app.dbc_manager.db
            msg = db.get_message_by_name(msg_name)
            id_var.set(hex(msg.frame_id))
            sig = msg.get_signal_by_name(sig_name)
            byte_var.set(sig.start // 8)
        except:
            pass
    forecast_signal_combo.bind("<<ComboboxSelected>>", on_signal_selected)
    forecast_signal_combo.grid(row=4, column=1, columnspan=2, sticky=tk.W, padx=5)

    ttk.Button(frame, text="Trenuj i prognozuj", command=lambda: run_forecast(app, file_var.get(), id_var.get(), byte_var.get(), steps_var.get())).grid(row=4, column=1, pady=10)

    fig = Figure(figsize=(8, 4))
    ax = fig.add_subplot(111)
    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.get_tk_widget().grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
    frame.grid_rowconfigure(1, weight=1)
    frame.grid_columnconfigure(0, weight=1)
    frame.grid_columnconfigure(1, weight=1)

    app.forecast_fig = fig
    app.forecast_ax = ax
    app.forecast_canvas = canvas
    app.forecaster = SignalForecaster()


def setup_correlation_tab(app, frame):
    ttk.Label(frame, text="Plik z danymi:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
    file_var = tk.StringVar()
    ttk.Entry(frame, textvariable=file_var, width=50).grid(row=0, column=1, padx=5)
    ttk.Button(frame, text="Przeglądaj", command=lambda: browse_file(file_var)).grid(row=0, column=2)

    ttk.Button(frame, text="Oblicz korelację", command=lambda: run_correlation(app, file_var.get())).grid(row=1, column=1, pady=10)

    fig = Figure(figsize=(8, 6))
    ax = fig.add_subplot(111)
    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.get_tk_widget().grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
    frame.grid_rowconfigure(1, weight=1)
    frame.grid_columnconfigure(0, weight=1)
    frame.grid_columnconfigure(1, weight=1)

    app.corr_fig = fig
    app.corr_ax = ax
    app.corr_canvas = canvas


def setup_explorer_tab(app, frame):
    ttk.Label(frame, text="Plik z danymi:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
    file_var = tk.StringVar()
    ttk.Entry(frame, textvariable=file_var, width=50).grid(row=0, column=1, padx=5)
    ttk.Button(frame, text="Przeglądaj", command=lambda: browse_file(file_var)).grid(row=0, column=2)

    ttk.Label(frame, text="ID 1:").grid(row=1, column=0, sticky=tk.W, padx=5)
    id1_var = tk.StringVar()
    ttk.Entry(frame, textvariable=id1_var, width=15).grid(row=1, column=1, sticky=tk.W, padx=5)
    ttk.Label(frame, text="Bajt 1:").grid(row=1, column=2, sticky=tk.W, padx=5)
    byte1_var = tk.IntVar(value=0)
    ttk.Spinbox(frame, from_=0, to=7, textvariable=byte1_var, width=5).grid(row=1, column=3, sticky=tk.W, padx=5)

    ttk.Label(frame, text="ID 2:").grid(row=2, column=0, sticky=tk.W, padx=5)
    id2_var = tk.StringVar()
    ttk.Entry(frame, textvariable=id2_var, width=15).grid(row=2, column=1, sticky=tk.W, padx=5)
    ttk.Label(frame, text="Bajt 2:").grid(row=2, column=2, sticky=tk.W, padx=5)
    byte2_var = tk.IntVar(value=0)
    ttk.Spinbox(frame, from_=0, to=7, textvariable=byte2_var, width=5).grid(row=2, column=3, sticky=tk.W, padx=5)

    ttk.Button(frame, text="Rysuj wykres punktowy", command=lambda: run_explorer(app, file_var.get(), id1_var.get(), byte1_var.get(), id2_var.get(), byte2_var.get())).grid(row=3, column=1, pady=10)

    fig = Figure(figsize=(8, 6))
    ax = fig.add_subplot(111)
    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.get_tk_widget().grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
    frame.grid_rowconfigure(1, weight=1)
    frame.grid_columnconfigure(0, weight=1)
    frame.grid_columnconfigure(1, weight=1)

    app.explorer_fig = fig
    app.explorer_ax = ax
    app.explorer_canvas = canvas


def browse_file(var):
    path = filedialog.askopenfilename(filetypes=[("Logi", "*.txt *.log"), ("Wszystkie", "*.*")])
    if path:
        var.set(path)



def run_forecast(app, file_path, id_str, byte_idx, steps):
    if not file_path:
        messagebox.showerror("Błąd", "Wybierz plik.")
        return
    try:
        cid = int(id_str, 16)
    except:
        messagebox.showerror("Błąd", "Nieprawidłowy format ID.")
        return

    # Okno postępu
    progress = ProgressDialog(app.root, "Trenowanie LSTM", maximum=100)
    progress.update_progress(0, "Wczytywanie danych...")

    def task():
        try:
            frames = load_frames_from_file(file_path)
            if progress.cancel_event.is_set():
                return
            progress.update_progress(20, "Przetwarzanie sygnału...")
            values = []
            for f in frames:
                if f[0] == cid and len(f[1]) > byte_idx:
                    values.append(f[1][byte_idx])
            if len(values) < 30:
                app.root.after(0, lambda: messagebox.showerror("Błąd", "Zbyt mało danych."))
                progress.close()
                return
            progress.update_progress(40, "Trenowanie modelu LSTM...")
            # Zakładamy, że train() nie ma callbacka – pomijamy na razie
            app.forecaster.train(values)
            if progress.cancel_event.is_set():
                return
            progress.update_progress(80, "Generowanie prognozy...")
            forecast = app.forecaster.forecast(values, steps)
            if progress.cancel_event.is_set():
                return
            progress.update_progress(100, "Zakończono")
            app.root.after(0, lambda: plot_forecast(app, values, forecast))
        finally:
            app.root.after(0, progress.close)

    threading.Thread(target=task, daemon=True).start()

def plot_forecast(app, history, forecast):
    ax = app.forecast_ax
    ax.clear()
    ax.plot(history, label='Historia')
    if forecast:
        ax.plot(range(len(history), len(history)+len(forecast)), forecast, label='Prognoza', linestyle='--')
    ax.legend()
    ax.set_xlabel("Krok")
    ax.set_ylabel("Wartość")
    app.forecast_canvas.draw()


def run_correlation(app, file_path):
    if not file_path:
        messagebox.showerror("Błąd", "Wybierz plik.")
        return

    def task():
        frames = load_frames_from_file(file_path)
        signals = defaultdict(list)
        timestamps = []
        for f in frames:
            cid = f[0]
            data = f[1]
            ts = f[3] if f[3] is not None else 0.0
            timestamps.append(ts)
            for i, byte in enumerate(data):
                signals[f"{cid}_B{i}"].append(byte)

        # Wyrównanie długości
        min_len = min(len(v) for v in signals.values())
        matrix = []
        names = []
        for name, vals in signals.items():
            if len(vals) >= min_len:
                matrix.append(vals[:min_len])
                names.append(name)
        if not matrix:
            app.root.after(0, lambda: messagebox.showerror("Błąd", "Brak danych."))
            return
        corr = np.corrcoef(matrix)
        app.root.after(0, lambda: plot_correlation(app, corr, names))

    threading.Thread(target=task, daemon=True).start()


def plot_correlation(app, corr, names):
    ax = app.corr_ax
    ax.clear()
    if SEABORN_AVAILABLE:
        sns.heatmap(corr, xticklabels=names, yticklabels=names, ax=ax, cmap='coolwarm', center=0)
    else:
        ax.imshow(corr, cmap='coolwarm', aspect='auto')
    app.corr_canvas.draw()


def run_explorer(app, file_path, id1_str, byte1, id2_str, byte2):
    if not file_path:
        messagebox.showerror("Błąd", "Wybierz plik.")
        return
    try:
        cid1 = int(id1_str, 16)
        cid2 = int(id2_str, 16)
    except:
        messagebox.showerror("Błąd", "Nieprawidłowy format ID.")
        return

    def task():
        frames = load_frames_from_file(file_path)
        x_vals, y_vals = [], []
        for f in frames:
            if f[0] == cid1 and len(f[1]) > byte1:
                x_vals.append(f[1][byte1])
            if f[0] == cid2 and len(f[1]) > byte2:
                y_vals.append(f[1][byte2])
        min_len = min(len(x_vals), len(y_vals))
        x_vals, y_vals = x_vals[:min_len], y_vals[:min_len]
        app.root.after(0, lambda: plot_explorer(app, x_vals, y_vals))

    threading.Thread(target=task, daemon=True).start()


def plot_explorer(app, x_vals, y_vals):
    ax = app.explorer_ax
    ax.clear()
    ax.scatter(x_vals, y_vals, alpha=0.5, s=2)
    ax.set_xlabel("Sygnał 1")
    ax.set_ylabel("Sygnał 2")
    app.explorer_canvas.draw()
