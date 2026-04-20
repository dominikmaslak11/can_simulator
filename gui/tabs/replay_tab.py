import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from parsers import load_frames_from_file
from log_profiler import LogProfiler


def setup_replay_tab(app, tab):
    frame = ttk.Frame(tab, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)

    # Wybór pliku
    ttk.Label(frame, text="Plik candump/log:").grid(row=0, column=0, sticky=tk.W)
    file_var = tk.StringVar()
    ttk.Entry(frame, textvariable=file_var, width=50).grid(row=0, column=1, padx=5)
    ttk.Button(frame, text="Przeglądaj", command=lambda: browse_replay_file(file_var)).grid(row=0, column=2)
    ttk.Button(frame, text="Wczytaj plik", command=lambda: load_replay_file(app, file_var, info_label)).grid(row=0, column=3, padx=5)

    info_label = ttk.Label(frame, text="Nie wczytano pliku")
    info_label.grid(row=1, column=0, columnspan=3, pady=5, sticky=tk.W)
    ttk.Button(frame, text="Analizuj profil", command=lambda: show_profile(app)).grid(row=1, column=3, padx=5)

    # Interwał i przyspieszenie
    ttk.Label(frame, text="Interwał (s):").grid(row=2, column=0, sticky=tk.W)
    interval_var = tk.DoubleVar(value=0.5)
    ttk.Spinbox(frame, from_=0.01, to=10.0, increment=0.1, textvariable=interval_var, width=10).grid(row=2, column=1, sticky=tk.W)

    ttk.Label(frame, text="Przyspieszenie:").grid(row=2, column=2, sticky=tk.W)
    speed_var = tk.DoubleVar(value=1.0)
    ttk.Spinbox(frame, from_=0.1, to=10.0, increment=0.1, textvariable=speed_var, width=10).grid(row=2, column=3, sticky=tk.W)

    # Pętla
    loop_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(frame, text="Pętla", variable=loop_var).grid(row=3, column=0, columnspan=2, sticky=tk.W)

    # Przyciski sterujące
    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=4, column=0, columnspan=4, pady=10)

    start_btn = ttk.Button(btn_frame, text="Start", state='disabled')
    start_btn.pack(side=tk.LEFT, padx=5)
    pause_btn = ttk.Button(btn_frame, text="Pauza", state='disabled')
    pause_btn.pack(side=tk.LEFT, padx=5)
    stop_btn = ttk.Button(btn_frame, text="Stop", state='disabled')
    stop_btn.pack(side=tk.LEFT, padx=5)

    # Logowanie do pliku
    ttk.Label(frame, text="Zapisz log do:").grid(row=5, column=0, sticky=tk.W)
    log_var = tk.StringVar()
    ttk.Entry(frame, textvariable=log_var, width=50).grid(row=5, column=1, padx=5)
    ttk.Button(frame, text="Wybierz", command=lambda: browse_log_file(log_var)).grid(row=5, column=2)
    log_enable = tk.BooleanVar(value=False)
    ttk.Checkbutton(frame, text="Włącz logowanie", variable=log_enable).grid(row=5, column=3)

    # Przypisanie do obiektu app
    app.replay_file_var = file_var
    app.replay_info = info_label
    app.replay_interval = interval_var
    app.replay_speed = speed_var
    app.replay_loop = loop_var
    app.replay_start_btn = start_btn
    app.replay_pause_btn = pause_btn
    app.replay_stop_btn = stop_btn
    app.replay_log_var = log_var
    app.replay_log_enable = log_enable

    start_btn.config(command=app.start_replay)
    pause_btn.config(command=app.pause_sim)
    stop_btn.config(command=app.stop_sim)


def browse_replay_file(file_var):
    path = filedialog.askopenfilename(filetypes=[("Logi", "*.txt *.log"), ("Wszystkie", "*.*")])
    if path:
        file_var.set(path)


def browse_log_file(log_var):
    path = filedialog.asksaveasfilename(defaultextension=".log", filetypes=[("Logi", "*.log")])
    if path:
        log_var.set(path)


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


def show_profile(app):
    if not app.loaded_frames:
        messagebox.showinfo("Brak danych", "Najpierw wczytaj plik z logiem.")
        return
    profiler = LogProfiler(app.loaded_frames)
    report = profiler.generate_report()

    win = tk.Toplevel(app.root)
    win.title("Profil logu CAN")
    text = scrolledtext.ScrolledText(win, width=90, height=25, font=('Courier', 10))
    text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    text.insert(tk.END, report)
    text.config(state='disabled')
