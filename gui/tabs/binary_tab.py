import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from parsers import load_frames_from_file


def setup_binary_tab(app, tab):
    frame = ttk.Frame(tab, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame, text="Plik candump/log:").grid(row=0, column=0, sticky=tk.W)
    file_var = tk.StringVar()
    ttk.Entry(frame, textvariable=file_var, width=50).grid(row=0, column=1, padx=5)
    ttk.Button(frame, text="Przeglądaj", command=lambda: browse_binary_file(file_var)).grid(row=0, column=2)
    ttk.Button(frame, text="Wczytaj plik", command=lambda: load_binary_file(app, file_var, info_label, start_btn)).grid(row=0, column=3, padx=5)

    info_label = ttk.Label(frame, text="Nie wczytano pliku")
    info_label.grid(row=1, column=0, columnspan=4, pady=5)

    ttk.Label(frame, text="Interwał odtwarzania (s):").grid(row=2, column=0, sticky=tk.W)
    interval_var = tk.DoubleVar(value=0.1)
    ttk.Spinbox(frame, from_=0.001, to=1.0, increment=0.01, textvariable=interval_var, width=10).grid(row=2, column=1, sticky=tk.W)

    ttk.Label(frame, text="Tryb:").grid(row=3, column=0, sticky=tk.W)
    mode_var = tk.StringVar(value="find_start")
    mode_frame = ttk.Frame(frame)
    mode_frame.grid(row=3, column=1, columnspan=3, sticky=tk.W)
    ttk.Radiobutton(mode_frame, text="Początek zjawiska", variable=mode_var, value="find_start").pack(side=tk.LEFT, padx=5)
    ttk.Radiobutton(mode_frame, text="Koniec zjawiska", variable=mode_var, value="find_end").pack(side=tk.LEFT, padx=5)
    ttk.Radiobutton(mode_frame, text="Ręczny podział na części", variable=mode_var, value="manual_parts").pack(side=tk.LEFT, padx=5)
    ttk.Radiobutton(mode_frame, text="Automatyczne polowanie", variable=mode_var, value="hunt_deactivator").pack(side=tk.LEFT, padx=5)
    ttk.Radiobutton(mode_frame, text="Polowanie z RL", variable=mode_var, value="rl_hunt").pack(side=tk.LEFT, padx=5)

    # Ramka dla parametrów polowania (ukrywana, gdy niepotrzebna)
    hunt_frame = ttk.LabelFrame(frame, text="Parametry polowania", padding=5)
    hunt_frame.grid(row=4, column=0, columnspan=4, pady=5, sticky='ew')
    ttk.Label(hunt_frame, text="ID alertu (hex):").grid(row=0, column=0, sticky=tk.W)
    alert_id_var = tk.StringVar(value="0C00008F")
    ttk.Entry(hunt_frame, textvariable=alert_id_var, width=15).grid(row=0, column=1, padx=5)
    ttk.Label(hunt_frame, text="Okres (s):").grid(row=0, column=2, sticky=tk.W)
    period_var = tk.DoubleVar(value=1.0)
    ttk.Spinbox(hunt_frame, from_=0.01, to=60.0, increment=0.1, textvariable=period_var, width=10).grid(row=0, column=3)
    ttk.Label(hunt_frame, text="Tolerancja (±):").grid(row=1, column=0, sticky=tk.W)
    tolerance_var = tk.DoubleVar(value=0.2)
    ttk.Spinbox(hunt_frame, from_=0.0, to=1.0, increment=0.05, textvariable=tolerance_var, width=10).grid(row=1, column=1)
    ttk.Label(hunt_frame, text="Start (indeks):").grid(row=1, column=2, sticky=tk.W)
    start_index_var = tk.IntVar(value=0)
    ttk.Spinbox(hunt_frame, from_=0, to=999999, textvariable=start_index_var, width=10).grid(row=1, column=3)

    def on_mode_change(*args):
        if mode_var.get() in ('hunt_deactivator', 'rl_hunt'):
            hunt_frame.grid()
        else:
            hunt_frame.grid_remove()
        if mode_var.get() == 'manual_parts':
            parts_spin.config(state='normal')
        else:
            parts_spin.config(state='disabled')
    mode_var.trace('w', on_mode_change)

    ttk.Label(frame, text="Liczba części:").grid(row=5, column=0, sticky=tk.W)
    parts_var = tk.IntVar(value=2)
    parts_spin = ttk.Spinbox(frame, from_=2, to=20, textvariable=parts_var, width=5, state='disabled')
    parts_spin.grid(row=5, column=1, sticky=tk.W)

    canvas_frame = ttk.Frame(frame)
    canvas_frame.grid(row=6, column=0, columnspan=4, pady=5, sticky='ew')
    canvas = tk.Canvas(canvas_frame, height=30, bg='white', relief='sunken', borderwidth=1)
    canvas.pack(fill=tk.X, padx=5)

    progress_label = ttk.Label(frame, text="Zakres: --")
    progress_label.grid(row=7, column=0, columnspan=4, pady=5)

    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=8, column=0, columnspan=4, pady=10)

    start_btn = ttk.Button(btn_frame, text="Start", state='disabled')
    start_btn.pack(side=tk.LEFT, padx=5)
    yes_btn = ttk.Button(btn_frame, text="Tak (zjawisko wystąpiło)", state='disabled')
    yes_btn.pack(side=tk.LEFT, padx=5)
    no_btn = ttk.Button(btn_frame, text="Nie (brak zjawiska)", state='disabled')
    no_btn.pack(side=tk.LEFT, padx=5)
    stop_btn = ttk.Button(btn_frame, text="Stop", state='disabled')
    stop_btn.pack(side=tk.LEFT, padx=5)
    undo_btn = ttk.Button(btn_frame, text="Cofnij", state='disabled', command=lambda: undo_binary_search(app))
    undo_btn.pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Reset", command=lambda: reset_binary_search(app)).pack(side=tk.LEFT, padx=5)

    app.binary_file_var = file_var
    app.binary_info = info_label
    app.binary_interval = interval_var
    app.binary_mode = mode_var
    app.binary_parts = parts_var
    app.binary_canvas = canvas
    app.binary_progress = progress_label
    app.binary_start_btn = start_btn
    app.binary_yes_btn = yes_btn
    app.binary_no_btn = no_btn
    app.binary_stop_btn = stop_btn
    app.binary_undo_btn = undo_btn
    app.hunt_alert_id = alert_id_var
    app.hunt_period = period_var
    app.hunt_tolerance = tolerance_var
    app.hunt_start_index = start_index_var

    start_btn.config(command=app.start_binary_search)
    yes_btn.config(command=app.binary_answer_yes)
    no_btn.config(command=app.binary_answer_no)
    stop_btn.config(command=app.stop_binary_search)

    on_mode_change()


def browse_binary_file(file_var):
    path = filedialog.askopenfilename(filetypes=[("Logi", "*.txt *.log"), ("Wszystkie", "*.*")])
    if path:
        file_var.set(path)


def load_binary_file(app, file_var, info_label, start_btn):
    path = file_var.get()
    if not path:
        messagebox.showerror("Błąd", "Wybierz plik")
        return
    try:
        app.binary_frames = load_frames_from_file(path)
        info_label.config(text=f"Wczytano {len(app.binary_frames)} ramek")
        app.log(f"[Binary] Wczytano {len(app.binary_frames)} ramek z {path}")
        start_btn.config(state='normal')
        app._redraw_binary_progress()
    except Exception as e:
        messagebox.showerror("Błąd", f"Nie udało się wczytać pliku: {e}")


def reset_binary_search(app):
    if app.binary_thread:
        app.binary_thread.stop()
    app.binary_start_btn.config(state='normal')
    app.binary_yes_btn.config(state='disabled')
    app.binary_no_btn.config(state='disabled')
    app.binary_stop_btn.config(state='disabled')
    app.binary_undo_btn.config(state='disabled')
    app.binary_progress.config(text="Zakres: --")
    app._redraw_binary_progress()
    app.log("[Binary] Reset.")


def undo_binary_search(app):
    if app.binary_thread:
        if app.binary_thread.undo():
            app._update_binary_progress()
            app.log("[Binary] Cofnięto.")
        else:
            messagebox.showinfo("Cofnij", "Brak wcześniejszego stanu.")
