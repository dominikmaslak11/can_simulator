import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from parsers import load_frames_from_file
from session_manager import SessionManager

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

    timestamps_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(frame, text="Użyj oryginalnych odstępów czasowych (z logu)",
                    variable=timestamps_var).grid(row=2, column=2, columnspan=2, sticky=tk.W)

    ttk.Label(frame, text="Tryb:").grid(row=3, column=0, sticky=tk.W)
    mode_var = tk.StringVar(value="find_start")
    mode_frame = ttk.Frame(frame)
    mode_frame.grid(row=3, column=1, columnspan=3, sticky=tk.W)
    ttk.Radiobutton(mode_frame, text="Początek zjawiska", variable=mode_var, value="find_start").pack(side=tk.LEFT, padx=5)
    ttk.Radiobutton(mode_frame, text="Koniec zjawiska", variable=mode_var, value="find_end").pack(side=tk.LEFT, padx=5)
    ttk.Radiobutton(mode_frame, text="Ręczny podział na części", variable=mode_var, value="manual_parts").pack(side=tk.LEFT, padx=5)

    ttk.Label(frame, text="Liczba części:").grid(row=4, column=0, sticky=tk.W)
    parts_var = tk.IntVar(value=2)
    parts_spin = ttk.Spinbox(frame, from_=2, to=20, textvariable=parts_var, width=5, state='disabled')
    parts_spin.grid(row=4, column=1, sticky=tk.W)
    mode_var.trace('w', lambda *a: parts_spin.config(state='normal' if mode_var.get()=='manual_parts' else 'disabled'))

    canvas_frame = ttk.Frame(frame)
    canvas_frame.grid(row=5, column=0, columnspan=4, pady=5, sticky='ew')
    canvas = tk.Canvas(canvas_frame, height=30, bg='white', relief='sunken', borderwidth=1)
    canvas.pack(fill=tk.X, padx=5)

    progress_label = ttk.Label(frame, text="Zakres: --")
    progress_label.grid(row=6, column=0, columnspan=4, pady=5)

    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=7, column=0, columnspan=4, pady=10)

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
    export_btn = ttk.Button(btn_frame, text="Eksportuj sesję", state='disabled',
                            command=lambda: export_binary_session(app))
    export_btn.pack(side=tk.LEFT, padx=5)
    import_btn = ttk.Button(btn_frame, text="Importuj sesję",
                            command=lambda: import_binary_session(app))
    import_btn.pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Reset", command=lambda: reset_binary_search(app)).pack(side=tk.LEFT, padx=5)

    app.binary_file_var = file_var
    app.binary_info = info_label
    app.binary_interval = interval_var
    app.binary_use_timestamps = timestamps_var
    app.binary_mode = mode_var
    app.binary_parts = parts_var
    app.binary_canvas = canvas
    app.binary_progress = progress_label
    app.binary_start_btn = start_btn
    app.binary_yes_btn = yes_btn
    app.binary_no_btn = no_btn
    app.binary_stop_btn = stop_btn
    app.binary_undo_btn = undo_btn
    app.binary_export_btn = export_btn

    start_btn.config(command=app.binary_ctrl.start_binary_search)
    yes_btn.config(command=app.binary_ctrl.binary_answer_yes)
    no_btn.config(command=app.binary_ctrl.binary_answer_no)
    stop_btn.config(command=app.binary_ctrl.stop_binary_search)

def browse_binary_file(file_var):
    path = filedialog.askopenfilename(filetypes=[("Logi", "*.txt *.log"), ("Wszystkie", "*.*")])
    if path: file_var.set(path)

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
    app.binary_export_btn.config(state='disabled')
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

def export_binary_session(app):
    if not app.binary_thread or not app.binary_thread.history:
        messagebox.showwarning("Eksport", "Brak aktywnej sesji do wyeksportowania.")
        return
    filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
    if not filepath:
        return
    settings = {
        "interval": app.binary_interval.get(),
        "use_timestamps": app.binary_use_timestamps.get(),
        "mode": app.binary_mode.get(),
        "num_parts": app.binary_parts.get() if app.binary_mode.get() == 'manual_parts' else None
    }
    source = app.binary_file_var.get()
    session = app.binary_thread.export_session(settings, source)
    SessionManager.save_to_file(session, filepath)
    app.log(f"[Binary] Sesja wyeksportowana do {filepath}")

def import_binary_session(app):
    filepath = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
    if not filepath:
        return
    try:
        session = SessionManager.load_from_file(filepath)
    except Exception as e:
        messagebox.showerror("Import", f"Błąd odczytu pliku: {e}")
        return

    if not app.binary_frames:
        messagebox.showwarning("Import", "Najpierw wczytaj plik z ramkami.")
        return

    app.binary_interval.set(session['settings']['interval'])
    app.binary_use_timestamps.set(session['settings'].get('use_timestamps', False))
    app.binary_mode.set(session['settings']['mode'])
    if session['settings'].get('num_parts'):
        app.binary_parts.set(session['settings']['num_parts'])

    app._start_binary_thread(lambda *a, **kw: None)  # uproszczony callback – w praktyce trzeba odtworzyć ask_callback
    SessionManager.restore_state(app.binary_thread, session)
    app._update_binary_progress()
    app.binary_export_btn.config(state='normal')
    app.binary_yes_btn.config(state='normal')
    app.binary_no_btn.config(state='normal')
    app.binary_stop_btn.config(state='normal')
    app.binary_undo_btn.config(state='normal')
    app.log(f"[Binary] Sesja zaimportowana z {filepath}")
