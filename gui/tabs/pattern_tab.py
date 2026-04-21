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
from ml.pattern_detector import PatternDetector


def setup_pattern_tab(app, tab):
    if not MATPLOTLIB_AVAILABLE:
        ttk.Label(tab, text="Brak biblioteki matplotlib.", foreground="red").pack(pady=20)
        return

    frame = ttk.Frame(tab, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)
    frame.grid_rowconfigure(6, weight=1)
    frame.grid_columnconfigure(1, weight=1)

    row = 0

    # Plik treningowy
    ttk.Label(frame, text="Log normalny (treningowy):").grid(row=row, column=0, sticky=tk.W, pady=5)
    train_var = tk.StringVar()
    ttk.Entry(frame, textvariable=train_var, width=50).grid(row=row, column=1, padx=5, sticky=tk.EW)
    ttk.Button(frame, text="Przeglądaj", command=lambda: browse_file(train_var)).grid(row=row, column=2, padx=5)
    row += 1

    ttk.Button(frame, text="Trenuj autoenkoder", command=lambda: train_pattern_model(app, train_var.get())).grid(row=row, column=1, pady=5)
    row += 1

    # Plik testowy
    ttk.Label(frame, text="Log do analizy:").grid(row=row, column=0, sticky=tk.W, pady=5)
    test_var = tk.StringVar()
    ttk.Entry(frame, textvariable=test_var, width=50).grid(row=row, column=1, padx=5, sticky=tk.EW)
    ttk.Button(frame, text="Przeglądaj", command=lambda: browse_file(test_var)).grid(row=row, column=2, padx=5)
    row += 1

    # Przycisk wykrywania
    ttk.Button(frame, text="Wykryj anomalie wzorca", command=lambda: detect_pattern_anomalies(app, test_var.get())).grid(row=row, column=1, pady=5)
    row += 1

    # Przyciski akcji (eksport, symulacja) w jednym wierszu
    action_frame = ttk.Frame(frame)
    action_frame.grid(row=row, column=0, columnspan=3, pady=5)
    ttk.Button(action_frame, text="Eksportuj zaznaczone okno", command=lambda: export_window(app)).pack(side=tk.LEFT, padx=5)
    ttk.Button(action_frame, text="Dodaj do symulacji modułu", command=lambda: send_to_missing_sim(app)).pack(side=tk.LEFT, padx=5)
    row += 1

    # Wykres
    fig = Figure(figsize=(8, 4))
    ax = fig.add_subplot(111)
    ax.set_xlabel("Okno")
    ax.set_ylabel("Błąd rekonstrukcji")
    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.grid(row=row, column=0, columnspan=3, sticky=tk.NSEW, pady=10)
    row += 1

    # Tabela anomalii
    table_frame = ttk.LabelFrame(frame, text="Wykryte anomalie")
    table_frame.grid(row=row, column=0, columnspan=3, sticky=tk.NSEW, pady=5)
    table_frame.grid_rowconfigure(0, weight=1)
    table_frame.grid_columnconfigure(0, weight=1)

    columns = ('start', 'end', 'error', 'cause')
    tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=6)
    tree.heading('start', text='Początek [s]')
    tree.heading('end', text='Koniec [s]')
    tree.heading('error', text='Błąd rekonstr.')
    tree.heading('cause', text='Przyczyna')
    tree.column('start', width=120)
    tree.column('end', width=120)
    tree.column('error', width=100)
    tree.column('cause', width=350)

    vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.grid(row=0, column=0, sticky=tk.NSEW)
    vsb.grid(row=0, column=1, sticky=tk.NS)
    row += 1

    # Status
    status_var = tk.StringVar(value="Gotowy")
    ttk.Label(frame, textvariable=status_var).grid(row=row, column=0, columnspan=3, pady=5)

    # Przechowywanie danych
    app.pattern_train_var = train_var
    app.pattern_test_var = test_var
    app.pattern_fig = fig
    app.pattern_ax = ax
    app.pattern_canvas = canvas
    app.pattern_tree = tree
    app.pattern_status = status_var
    app.pattern_detector = PatternDetector()
    app.pattern_test_frames = None
    app.pattern_windows = []
    app.pattern_errors = []

    fig.canvas.mpl_connect('button_press_event', lambda event: on_plot_click(app, event))
    tree.bind('<<TreeviewSelect>>', lambda e: on_tree_select(app))


def browse_file(var):
    path = filedialog.askopenfilename(filetypes=[("Logi", "*.txt *.log"), ("Wszystkie", "*.*")])
    if path:
        var.set(path)


def train_pattern_model(app, train_path):
    if not train_path:
        messagebox.showerror("Błąd", "Wybierz plik treningowy.")
        return
    try:
        frames = load_frames_from_file(train_path)
    except Exception as e:
        messagebox.showerror("Błąd", f"Nie udało się wczytać pliku: {e}")
        return

    app.pattern_status.set("Trenowanie autoenkodera...")
    app.root.update()

    def train():
        success = app.pattern_detector.train(frames)
        app.root.after(0, lambda: finish_training(success, frames))

    def finish_training(success, frames):
        if success:
            app.pattern_train_frames = frames
            app.pattern_status.set("Model wytrenowany pomyślnie.")
            app.log("[Pattern] Autoenkoder wytrenowany.")
        else:
            app.pattern_status.set("Błąd trenowania.")

    threading.Thread(target=train, daemon=True).start()


def detect_pattern_anomalies(app, test_path):
    if not test_path:
        messagebox.showerror("Błąd", "Wybierz plik testowy.")
        return
    try:
        frames = load_frames_from_file(test_path)
        app.pattern_test_frames = frames
    except Exception as e:
        messagebox.showerror("Błąd", f"Nie udało się wczytać pliku: {e}")
        return

    app.pattern_status.set("Wykrywanie anomalii wzorca...")
    app.root.update()

    def detect():
        errors, _ = app.pattern_detector.detect_anomalies(frames)
        app.pattern_errors = errors
        threshold = app.pattern_detector.threshold
        if threshold is None:
            threshold = np.percentile(errors, 95) if len(errors) > 0 else 0
        windows = app.pattern_detector.get_anomalous_windows(frames, errors, threshold)
        app.pattern_windows = windows
        app.root.after(0, lambda: plot_results(app, errors, windows))

    threading.Thread(target=detect, daemon=True).start()


def plot_results(app, errors, windows):
    ax = app.pattern_ax
    ax.clear()
    if len(errors) > 0:
        ax.plot(errors, 'b-')
        thr = app.pattern_detector.threshold
        if thr is not None:
            ax.axhline(y=thr, color='r', linestyle='--', label=f"Próg {thr:.3f}")
        for w in windows:
            ax.axvspan(w['start_idx'], w['end_idx'], alpha=0.3, color='red')
    ax.set_xlabel("Okno")
    ax.set_ylabel("Błąd rekonstrukcji")
    ax.legend()
    app.pattern_canvas.draw()

    tree = app.pattern_tree
    tree.delete(*tree.get_children())
    t0 = app.pattern_test_frames[0][3] if app.pattern_test_frames and app.pattern_test_frames[0][3] is not None else 0

    train_frames = getattr(app, 'pattern_train_frames', None)
    for w in windows:
        # Diagnoza
        causes = []
        if train_frames and app.pattern_test_frames:
            window_frames = [f for f in app.pattern_test_frames if w['start_time'] <= f[3] <= w['end_time']]
            causes = app.pattern_detector.diagnose_window(train_frames, window_frames)
        cause_str = ", ".join(causes) if causes else "Analizuję..."
        tree.insert("", tk.END, values=(
            f"{w['start_time'] - t0:.3f}",
            f"{w['end_time'] - t0:.3f}",
            f"{w['error']:.4f}",
            cause_str
        ))

    app.pattern_status.set(f"Wykryto {len(windows)} anomalnych okien.")
    app.log(f"[Pattern] Wykryto {len(windows)} anomalii wzorca.")


def on_plot_click(app, event):
    if event.inaxes != app.pattern_ax:
        return
    x = event.xdata
    if x is None:
        return
    for w in app.pattern_windows:
        if w['start_idx'] <= x <= w['end_idx']:
            highlight_window(app, w)
            break


def on_tree_select(app):
    sel = app.pattern_tree.selection()
    if not sel:
        return
    idx = app.pattern_tree.index(sel[0])
    if idx < len(app.pattern_windows):
        w = app.pattern_windows[idx]
        highlight_window(app, w)


def highlight_window(app, w):
    if hasattr(app, 'sniffer_ctrl') and app.pattern_test_frames:
        start_time = w['start_time']
        end_time = w['end_time']
        app.sniffer_ctrl.highlight_time_range(start_time, end_time)
        app.log(f"[Pattern] Podświetlono ramki w oknie {start_time:.3f} – {end_time:.3f}")


def export_window(app):
    sel = app.pattern_tree.selection()
    if not sel:
        messagebox.showinfo("Brak zaznaczenia", "Zaznacz okno anomalii w tabeli.")
        return
    idx = app.pattern_tree.index(sel[0])
    if idx >= len(app.pattern_windows):
        return
    w = app.pattern_windows[idx]
    frames = app.pattern_test_frames
    if not frames:
        return
    window_frames = [f for f in frames if w['start_time'] <= f[3] <= w['end_time']]
    if not window_frames:
        messagebox.showinfo("Brak ramek", "Wybrane okno nie zawiera ramek.")
        return

    filepath = filedialog.asksaveasfilename(defaultextension=".log", filetypes=[("Logi", "*.log")])
    if not filepath:
        return
    with open(filepath, 'w') as f:
        for frm in window_frames:
            ts = datetime.fromtimestamp(frm[3]).strftime("%H:%M:%S.%f")[:-3]
            f.write(f"({frm[3]:.6f}) can0 {frm[0]:08X}#{frm[1].hex().upper()}\n")
    app.log(f"[Pattern] Wyeksportowano {len(window_frames)} ramek do {filepath}")
    messagebox.showinfo("Sukces", f"Wyeksportowano {len(window_frames)} ramek.")


def send_to_missing_sim(app):
    sel = app.pattern_tree.selection()
    if not sel:
        messagebox.showinfo("Brak zaznaczenia", "Zaznacz okno anomalii w tabeli.")
        return
    idx = app.pattern_tree.index(sel[0])
    if idx >= len(app.pattern_windows):
        return
    w = app.pattern_windows[idx]
    frames = app.pattern_test_frames
    if not frames:
        return
    window_frames = [f for f in frames if w['start_time'] <= f[3] <= w['end_time']]
    if not window_frames:
        messagebox.showinfo("Brak ramek", "Wybrane okno nie zawiera ramek.")
        return

    added = set()
    for frm in window_frames:
        cid = frm[0]
        data = frm[1]
        is_ext = frm[2]
        key = (cid, data, is_ext)
        if key not in added:
            app.missing_ctrl.add_custom_frame(cid, data, is_ext)
            added.add(key)

    app.notebook.select(app.tab_missing)
    app.log(f"[Pattern] Dodano {len(added)} unikalnych ramek do symulacji modułu.")
    messagebox.showinfo("Sukces", f"Dodano {len(added)} ramek do symulacji modułu.")
