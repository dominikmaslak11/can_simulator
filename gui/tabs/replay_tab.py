import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from parsers import load_frames_from_file


def export_replay_asc(app):
    """Eksportuje wczytany plik do formatu ASC."""
    from tkinter import filedialog
    import datetime
    import os

    if not app.loaded_frames:
        messagebox.showerror("Błąd", "Najpierw wczytaj plik.")
        return

    filepath = filedialog.asksaveasfilename(defaultextension=".asc", filetypes=[("Pliki ASC", "*.asc")])
    if not filepath:
        return

    frames = app.loaded_frames
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("date %s\n" % datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Y"))
        f.write("base hex  timestamps absolute\n")
        f.write("internal events logged\n")
        f.write("// Eksport z CAN Simulator GUI\n")

        if frames:
            start_ts = frames[0][3] if frames[0][3] is not None else 0.0
        else:
            start_ts = 0.0

        for can_id, data, is_ext, ts in frames:
            if ts is None:
                ts = 0.0
            relative_time = ts - start_ts
            id_str = f"{can_id:08X}"
            dlc = len(data)
            line = f" {relative_time:12.6f} 1  {id_str}x  Rx  d {dlc}"
            for byte in data:
                line += f" {byte:02X}"
            f.write(line + "\n")
    app.log(f"Wyeksportowano {len(frames)} ramek do ASC: {filepath}")


def setup_replay_tab(app, tab):
    frame = ttk.Frame(tab, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame, text="Plik candump/log:").grid(row=0, column=0, sticky=tk.W)
    file_var = tk.StringVar()
    ttk.Entry(frame, textvariable=file_var, width=50).grid(row=0, column=1, padx=5)
    ttk.Button(frame, text="Przeglądaj", command=lambda: browse_replay_file(file_var)).grid(row=0, column=2)
    ttk.Button(frame, text="Wczytaj plik", command=lambda: load_replay_file(app, file_var, info_label)).grid(row=0, column=3, padx=5)

    info_label = ttk.Label(frame, text="Nie wczytano pliku")
    info_label.grid(row=1, column=0, columnspan=4, pady=5)

    ttk.Label(frame, text="Interwał (s):").grid(row=2, column=0, sticky=tk.W)
    interval_var = tk.DoubleVar(value=0.5)
    ttk.Spinbox(frame, from_=0.01, to=10.0, increment=0.1, textvariable=interval_var, width=10).grid(row=2, column=1, sticky=tk.W)

    ttk.Label(frame, text="Przyspieszenie:").grid(row=2, column=2, sticky=tk.W)
    speed_var = tk.DoubleVar(value=1.0)
    ttk.Spinbox(frame, from_=0.1, to=10.0, increment=0.1, textvariable=speed_var, width=10).grid(row=2, column=3, sticky=tk.W)

    loop_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(frame, text="Pętla", variable=loop_var).grid(row=3, column=0, columnspan=2, sticky=tk.W)

    timestamps_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(frame, text="Użyj oryginalnych odstępów czasowych (z logu)",
                    variable=timestamps_var).grid(row=3, column=2, columnspan=2, sticky=tk.W)

    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=4, column=0, columnspan=4, pady=10)

    start_btn = ttk.Button(btn_frame, text="Start", state='disabled')
    start_btn.pack(side=tk.LEFT, padx=5)
    pause_btn = ttk.Button(btn_frame, text="Pauza", state='disabled')
    pause_btn.pack(side=tk.LEFT, padx=5)
    stop_btn = ttk.Button(btn_frame, text="Stop", state='disabled')
    stop_btn.pack(side=tk.LEFT, padx=5)

    ttk.Label(frame, text="Zapisz log do:").grid(row=5, column=0, sticky=tk.W)
    log_var = tk.StringVar()
    ttk.Entry(frame, textvariable=log_var, width=50).grid(row=5, column=1, padx=5)
    ttk.Button(frame, text="Wybierz", command=lambda: browse_log_file(log_var)).grid(row=5, column=2)
    log_enable = tk.BooleanVar(value=False)
    ttk.Checkbutton(frame, text="Włącz logowanie", variable=log_enable).grid(row=5, column=3)

    app.replay_file_var = file_var
    app.replay_info = info_label
    app.replay_interval = interval_var
    app.replay_speed = speed_var
    app.replay_loop = loop_var
    app.replay_use_timestamps = timestamps_var
    app.replay_start_btn = start_btn
    app.replay_pause_btn = pause_btn
    app.replay_stop_btn = stop_btn
    app.replay_log_var = log_var
    app.replay_log_enable = log_enable

    start_btn.config(command=app.replay_ctrl.start_replay)
    pause_btn.config(command=app.pause_sim)
    stop_btn.config(command=app.stop_sim)

def browse_replay_file(file_var):
    path = filedialog.askopenfilename(filetypes=[("Logi", "*.txt *.log"), ("Wszystkie", "*.*")])
    if path: file_var.set(path)

def browse_log_file(log_var):
    path = filedialog.asksaveasfilename(defaultextension=".log", filetypes=[("Logi", "*.log")])
    if path: log_var.set(path)

def load_replay_file(app, file_var, info_label):
    path = file_var.get()
    if not path:
        messagebox.showerror("Błąd", "Wybierz plik")
        return
    try:
        app.loaded_frames = load_frames_from_file(path)
        info_label.config(text=f"Wczytano {len(app.loaded_frames)} ramek")
        app.log(f"Wczytano {len(app.loaded_frames)} ramek z {path}")
    except Exception as e:
        messagebox.showerror("Błąd", f"Nie udało się wczytać pliku: {e}")
