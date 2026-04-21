import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import numpy as np
from datetime import datetime

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from parsers import load_frames_from_file
from ml.session_classifier import SessionClassifier


def setup_ml_tab(app, tab):
    if not MATPLOTLIB_AVAILABLE:
        ttk.Label(tab, text="Brak biblioteki matplotlib. Zainstaluj ją (pip install matplotlib).",
                  foreground="red").pack(pady=20)
        return

    frame = ttk.Frame(tab, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)

    # Panel wyboru plików
    file_frame = ttk.LabelFrame(frame, text="Dane treningowe i testowe", padding=5)
    file_frame.pack(fill=tk.X, pady=(0, 10))

    ttk.Label(file_frame, text="Log normalny (referencyjny):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
    normal_var = tk.StringVar()
    ttk.Entry(file_frame, textvariable=normal_var, width=50).grid(row=0, column=1, padx=5)
    ttk.Button(file_frame, text="Przeglądaj", command=lambda: browse_file(normal_var)).grid(row=0, column=2, padx=2)

    ttk.Label(file_frame, text="Log z anomaliami (opcjonalny):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
    anomaly_var = tk.StringVar()
    ttk.Entry(file_frame, textvariable=anomaly_var, width=50).grid(row=1, column=1, padx=5)
    ttk.Button(file_frame, text="Przeglądaj", command=lambda: browse_file(anomaly_var)).grid(row=1, column=2, padx=2)

    ttk.Label(file_frame, text="Log do analizy:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
    test_var = tk.StringVar()
    ttk.Entry(file_frame, textvariable=test_var, width=50).grid(row=2, column=1, padx=5)
    ttk.Button(file_frame, text="Przeglądaj", command=lambda: browse_file(test_var)).grid(row=2, column=2, padx=2)

    # Przyciski akcji
    btn_frame = ttk.Frame(frame)
    btn_frame.pack(fill=tk.X, pady=5)

    train_btn = ttk.Button(btn_frame, text="Trenuj model",
                           command=lambda: train_model(app, normal_var.get(), anomaly_var.get()))
    train_btn.pack(side=tk.LEFT, padx=5)

    analyze_btn = ttk.Button(btn_frame, text="Analizuj log (nadzorowane)",
                             command=lambda: analyze_log(app, test_var.get()))
    analyze_btn.pack(side=tk.LEFT, padx=5)

    unsupervised_btn = ttk.Button(btn_frame, text="Wykryj anomalie (bez nadzoru)",
                                  command=lambda: detect_anomalies(app, test_var.get()))
    unsupervised_btn.pack(side=tk.LEFT, padx=5)

    report_btn = ttk.Button(btn_frame, text="Pokaż raport anomalii",
                            command=lambda: show_anomaly_report(app), state='disabled')
    report_btn.pack(side=tk.LEFT, padx=5)

    ttk.Label(btn_frame, text="Próg anomalii:").pack(side=tk.LEFT, padx=(20, 5))
    threshold_var = tk.DoubleVar(value=0.5)
    threshold_scale = ttk.Scale(btn_frame, from_=0.0, to=1.0, variable=threshold_var,
                                orient=tk.HORIZONTAL, length=150)
    threshold_scale.pack(side=tk.LEFT, padx=5)
    threshold_label = ttk.Label(btn_frame, text="0.50")
    threshold_label.pack(side=tk.LEFT)
    threshold_var.trace('w', lambda *a: threshold_label.config(text=f"{threshold_var.get():.2f}"))

    # Wykres
    chart_frame = ttk.Frame(frame)
    chart_frame.pack(fill=tk.BOTH, expand=True)

    fig = Figure(figsize=(8, 4), dpi=100)
    ax = fig.add_subplot(111)
    ax.set_xlabel("Czas [s]")
    ax.set_ylabel("Prawdopodobieństwo anomalii")
    ax.grid(True, linestyle='--', alpha=0.7)
    canvas = FigureCanvasTkAgg(fig, master=chart_frame)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    status_var = tk.StringVar(value="Gotowy")
    status_label = ttk.Label(frame, textvariable=status_var)
    status_label.pack(fill=tk.X, pady=(5, 0))

    # Przechowaj referencje
    app.ml_normal_var = normal_var
    app.ml_anomaly_var = anomaly_var
    app.ml_test_var = test_var
    app.ml_fig = fig
    app.ml_ax = ax
    app.ml_canvas = canvas
    app.ml_status = status_var
    app.ml_threshold = threshold_var
    app.ml_report_btn = report_btn
    app.ml_classifier = SessionClassifier()
    app.ml_train_frames = None
    app.ml_test_frames = None
    app.ml_anomaly_frames = None

    app.ml_last_windows = []
    app.ml_last_rel_times = []
    app.ml_last_probs = []
    app.ml_last_report = []

    fig.canvas.mpl_connect('button_press_event', lambda event: on_plot_click(app, event))


def browse_file(var):
    path = filedialog.askopenfilename(filetypes=[("Logi", "*.txt *.log"), ("Wszystkie", "*.*")])
    if path:
        var.set(path)


def train_model(app, normal_path, anomaly_path):
    if not normal_path:
        messagebox.showerror("Błąd", "Wybierz log normalny (referencyjny).")
        return
    try:
        normal_frames = load_frames_from_file(normal_path)
        anomaly_frames = load_frames_from_file(anomaly_path) if anomaly_path else None
    except Exception as e:
        messagebox.showerror("Błąd", f"Nie udało się wczytać plików:\n{e}")
        return

    app.ml_status.set("Trenowanie modelu...")
    app.root.update()

    def train_thread():
        success = app.ml_classifier.train(normal_frames, anomaly_frames)
        app.root.after(0, lambda: finish_training(success))

    def finish_training(success):
        if success:
            app.ml_train_frames = normal_frames
            app.ml_anomaly_frames = anomaly_frames
            app.ml_status.set("Model wytrenowany pomyślnie.")
            app.log("[ML] Model wytrenowany.")
        else:
            app.ml_status.set("Błąd trenowania – za mało danych.")
            app.log("[ML] Błąd trenowania.")

    threading.Thread(target=train_thread, daemon=True).start()


def analyze_log(app, test_path):
    if not test_path:
        messagebox.showerror("Błąd", "Wybierz log do analizy.")
        return
    try:
        test_frames = load_frames_from_file(test_path)
    except Exception as e:
        messagebox.showerror("Błąd", f"Nie udało się wczytać pliku:\n{e}")
        return

    app.ml_status.set("Analiza w toku...")
    app.root.update()

    def analyze_thread():
        times, probs, windows = app.ml_classifier.predict_proba(test_frames)
        app.root.after(0, lambda: draw_results(app, times, probs, windows, test_frames, "Analiza nadzorowana"))

    threading.Thread(target=analyze_thread, daemon=True).start()


def detect_anomalies(app, test_path):
    if not test_path:
        messagebox.showerror("Błąd", "Wybierz log do analizy.")
        return
    try:
        test_frames = load_frames_from_file(test_path)
    except Exception as e:
        messagebox.showerror("Błąd", f"Nie udało się wczytać pliku:\n{e}")
        return

    app.ml_status.set("Wykrywanie anomalii (bez nadzoru)...")
    app.root.update()

    def detect_thread():
        times, probs, windows = app.ml_classifier.detect_anomalies_unsupervised(test_frames)
        app.root.after(0, lambda: draw_results(app, times, probs, windows, test_frames, "Wykrywanie anomalii (bez nadzoru)"))

    threading.Thread(target=detect_thread, daemon=True).start()


def draw_results(app, times, probs, windows, test_frames, title="Analiza"):
    if len(times) == 0:
        app.ml_status.set("Brak danych do wyświetlenia.")
        return

    t0 = times[0]
    rel_times = [t - t0 for t in times]

    ax = app.ml_ax
    ax.clear()
    ax.plot(rel_times, probs, 'b-', linewidth=1)
    ax.axhline(y=app.ml_threshold.get(), color='r', linestyle='--', label=f"Próg {app.ml_threshold.get():.2f}")
    ax.fill_between(rel_times, 0, probs, where=(np.array(probs) >= app.ml_threshold.get()),
                    color='red', alpha=0.3, label='Anomalia')
    ax.set_xlabel("Czas [s]")
    ax.set_ylabel("Prawdopodobieństwo anomalii")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.7)
    app.ml_canvas.draw()

    app.ml_last_rel_times = rel_times
    app.ml_last_probs = probs
    app.ml_last_windows = windows
    app.ml_test_frames = test_frames

    # Generuj raport
    app.ml_last_report = app.ml_classifier.generate_report(
        test_frames, times, probs, windows, app.ml_threshold.get()
    )

    anomaly_count = sum(1 for p in probs if p >= app.ml_threshold.get())
    app.ml_status.set(f"Analiza zakończona. Wykryto {anomaly_count} anomalii.")
    app.ml_report_btn.config(state='normal')
    app.log(f"[ML] {title} – wykryto {anomaly_count} anomalii.")


def on_plot_click(app, event):
    if event.inaxes != app.ml_ax:
        return
    if not hasattr(app, 'ml_last_windows') or not app.ml_last_windows:
        return
    x = event.xdata
    if x is None:
        return

    rel_times = app.ml_last_rel_times
    windows = app.ml_last_windows

    idx = np.argmin(np.abs(np.array(rel_times) - x))
    window = windows[idx]
    if not window:
        return

    timestamps_in_window = [f[3] for f in window if f[3] is not None]
    if not timestamps_in_window:
        return

    start_time = min(timestamps_in_window)
    end_time = max(timestamps_in_window)

    if hasattr(app, 'sniffer_ctrl'):
        app.sniffer_ctrl.highlight_time_range(start_time, end_time)
        app.log(f"[ML] Podświetlono ramki w zakresie {start_time:.3f} – {end_time:.3f}")


def show_anomaly_report(app):
    if not app.ml_last_report:
        messagebox.showinfo("Brak raportu", "Najpierw przeprowadź analizę.")
        return

    win = tk.Toplevel(app.root)
    win.title("Raport anomalii")
    win.geometry("1000x500")
    win.transient(app.root)
    win.grab_set()

    frame = ttk.Frame(win, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)

    columns = ('start', 'end', 'prob', 'cause')
    tree = ttk.Treeview(frame, columns=columns, show='headings', height=12)
    tree.heading('start', text='Początek [s]')
    tree.heading('end', text='Koniec [s]')
    tree.heading('prob', text='Prawdop.')
    tree.heading('cause', text='Przyczyna')

    tree.column('start', width=120)
    tree.column('end', width=120)
    tree.column('prob', width=80)
    tree.column('cause', width=500)

    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)

    for r in app.ml_last_report:
        start = r['start_time']
        end = r['end_time']
        t0 = app.ml_last_windows[0][0][3] if app.ml_last_windows[0] else start
        tree.insert("", tk.END, values=(
            f"{start - t0:.3f}",
            f"{end - t0:.3f}",
            f"{r['probability']:.2f}",
            r['cause']
        ))

    def on_select(event):
        sel = tree.selection()
        if not sel:
            return
        idx = tree.index(sel[0])
        if idx < len(app.ml_last_report):
            r = app.ml_last_report[idx]
            if hasattr(app, 'sniffer_ctrl'):
                app.sniffer_ctrl.highlight_time_range(r['start_time'], r['end_time'])

    tree.bind('<<TreeviewSelect>>', on_select)

    btn_frame = ttk.Frame(win)
    btn_frame.pack(pady=10)
    ttk.Button(btn_frame, text="Eksportuj raport", command=lambda: export_report(app)).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Zamknij", command=win.destroy).pack(side=tk.LEFT, padx=5)


def export_report(app):
    if not app.ml_last_report:
        return
    filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
    if not filepath:
        return
    import csv
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Start [s]', 'Koniec [s]', 'Prawdopodobieństwo', 'Przyczyna'])
        t0 = app.ml_last_windows[0][0][3] if app.ml_last_windows[0] else 0
        for r in app.ml_last_report:
            writer.writerow([
                f"{r['start_time'] - t0:.3f}",
                f"{r['end_time'] - t0:.3f}",
                f"{r['probability']:.3f}",
                r['cause']
            ])
    app.log(f"[ML] Raport wyeksportowany do {filepath}")
