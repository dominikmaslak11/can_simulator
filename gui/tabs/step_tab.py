import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from parsers import load_frames_from_file

def setup_step_tab(app, tab):
    frame = ttk.Frame(tab, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame, text="Plik candump/log:").grid(row=0, column=0, sticky=tk.W)
    file_var = tk.StringVar()
    ttk.Entry(frame, textvariable=file_var, width=50).grid(row=0, column=1, padx=5)
    ttk.Button(frame, text="Przeglądaj", command=lambda: browse_step_file(file_var)).grid(row=0, column=2)

    reverse_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(frame, text="Odwrotna kolejność", variable=reverse_var).grid(row=1, column=0, columnspan=2, sticky=tk.W)

    ttk.Button(frame, text="Wczytaj plik", command=lambda: load_step_file(app, file_var, reverse_var)).grid(row=1, column=2, pady=5)

    info_label = ttk.Label(frame, text="Nie wczytano pliku")
    info_label.grid(row=2, column=0, columnspan=3)
    progress_label = ttk.Label(frame, text="0 / 0")
    progress_label.grid(row=3, column=0, columnspan=3, pady=5)
    preview_label = ttk.Label(frame, text="Kliknij 'Dalej' aby wysłać", foreground="blue")
    preview_label.grid(row=4, column=0, columnspan=3, pady=10)

    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=5, column=0, columnspan=3)

    next_btn = ttk.Button(btn_frame, text="Dalej (Enter)", state='disabled')
    next_btn.pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Reset", command=lambda: step_reset(app)).pack(side=tk.LEFT, padx=5)

    app.step_file_var = file_var
    app.step_reverse = reverse_var
    app.step_info = info_label
    app.step_progress = progress_label
    app.step_preview = preview_label
    app.step_next_btn = next_btn
    next_btn.config(command=app.step_next)
    app.root.bind('<Return>', lambda e: app.step_next())

def browse_step_file(file_var):
    path = filedialog.askopenfilename(filetypes=[("Logi", "*.txt *.log"), ("Wszystkie", "*.*")])
    if path:
        file_var.set(path)

def load_step_file(app, file_var, reverse_var):
    path = file_var.get()
    if not path:
        messagebox.showerror("Błąd", "Wybierz plik")
        return
    try:
        frames = load_frames_from_file(path)
        if reverse_var.get():
            frames.reverse()
        app.step_frames = frames
        app.step_idx = 0
        app.step_info.config(text=f"Wczytano {len(frames)} ramek")
        app.step_progress.config(text=f"0 / {len(frames)}")
        app.step_next_btn.config(state='normal')
        app._update_step_preview()
        app.log(f"Tryb krokowy: wczytano {len(frames)} ramek")
    except Exception as e:
        messagebox.showerror("Błąd", f"Nie udało się wczytać pliku: {e}")

def step_reset(app):
    app.step_idx = 0
    app.step_progress.config(text=f"0 / {len(app.step_frames)}")
    app._update_step_preview()
