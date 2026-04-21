import tkinter as tk
from tkinter import ttk, filedialog


def setup_wizard_tab(app, tab):
    frame = ttk.Frame(tab, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame, text="Plik candump/log:").grid(row=0, column=0, sticky=tk.W)
    file_var = tk.StringVar()
    ttk.Entry(frame, textvariable=file_var, width=50).grid(row=0, column=1, padx=5)
    ttk.Button(frame, text="Przeglądaj", command=lambda: browse_wizard_file(file_var)).grid(row=0, column=2)
    ttk.Button(frame, text="Wczytaj plik",
               command=lambda: app.wizard_ctrl.load_file(file_var, info_label, start_btn)).grid(row=0, column=3, padx=5)

    info_label = ttk.Label(frame, text="Nie wczytano pliku")
    info_label.grid(row=1, column=0, columnspan=4, pady=5)

    ttk.Label(frame, text="Szukana ramka/sekwencja:").grid(row=2, column=0, sticky=tk.W, pady=5)
    search_frame = ttk.LabelFrame(frame, text="Definicja", padding=5)
    search_frame.grid(row=3, column=0, columnspan=4, sticky='ew', pady=5)

    ttk.Label(search_frame, text="Tryb:").grid(row=0, column=0, sticky=tk.W)
    mode_var = tk.StringVar(value="single")
    mode_frame = ttk.Frame(search_frame)
    mode_frame.grid(row=0, column=1, columnspan=3, sticky=tk.W)
    ttk.Radiobutton(mode_frame, text="Pojedyncza ramka", variable=mode_var, value="single").pack(side=tk.LEFT, padx=5)
    ttk.Radiobutton(mode_frame, text="Sekwencja ramek", variable=mode_var, value="sequence").pack(side=tk.LEFT, padx=5)

    single_frame = ttk.Frame(search_frame)
    single_frame.grid(row=1, column=0, columnspan=4, sticky='ew', pady=5)

    ttk.Label(single_frame, text="ID (hex):").grid(row=0, column=0, sticky=tk.W)
    id_var = tk.StringVar(value="0C00008F")
    ttk.Entry(single_frame, textvariable=id_var, width=15).grid(row=0, column=1, padx=5)

    ttk.Label(single_frame, text="Dane (hex, opcjonalnie):").grid(row=1, column=0, sticky=tk.W)
    data_var = tk.StringVar(value="")
    ttk.Entry(single_frame, textvariable=data_var, width=30).grid(row=1, column=1, padx=5)

    extended_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(single_frame, text="Ramka rozszerzona (29-bit)", variable=extended_var).grid(row=2, column=0, columnspan=2, pady=5)

    seq_frame = ttk.Frame(search_frame)
    seq_frame.grid(row=1, column=0, columnspan=4, sticky='ew', pady=5)

    seq_listbox = tk.Listbox(seq_frame, height=4)
    seq_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    seq_scroll = ttk.Scrollbar(seq_frame, orient=tk.VERTICAL, command=seq_listbox.yview)
    seq_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    seq_listbox.config(yscrollcommand=seq_scroll.set)

    seq_btn_frame = ttk.Frame(search_frame)
    seq_btn_frame.grid(row=2, column=0, columnspan=4, pady=5)
    ttk.Button(seq_btn_frame, text="Dodaj ramkę", command=app.wizard_ctrl.add_sequence_frame).pack(side=tk.LEFT, padx=5)
    ttk.Button(seq_btn_frame, text="Usuń zaznaczoną", command=app.wizard_ctrl.remove_sequence_frame).pack(side=tk.LEFT, padx=5)

    def toggle_mode(*args):
        if mode_var.get() == "single":
            single_frame.grid()
            seq_frame.grid_remove()
            seq_btn_frame.grid_remove()
        else:
            single_frame.grid_remove()
            seq_frame.grid()
            seq_btn_frame.grid()

    mode_var.trace('w', toggle_mode)
    toggle_mode()

    ttk.Label(frame, text="Liczba części do podziału:").grid(row=4, column=0, sticky=tk.W)
    parts_var = tk.IntVar(value=2)
    ttk.Spinbox(frame, from_=2, to=20, textvariable=parts_var, width=5).grid(row=4, column=1, sticky=tk.W)

    ttk.Label(frame, text="Interwał odtwarzania (s):").grid(row=5, column=0, sticky=tk.W)
    interval_var = tk.DoubleVar(value=0.1)
    ttk.Spinbox(frame, from_=0.001, to=1.0, increment=0.01, textvariable=interval_var, width=10).grid(
        row=5, column=1, sticky=tk.W)

    timestamps_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(frame, text="Użyj oryginalnych odstępów czasowych (z logu)",
                    variable=timestamps_var).grid(row=5, column=2, columnspan=2, sticky=tk.W)

    canvas_frame = ttk.Frame(frame)
    canvas_frame.grid(row=6, column=0, columnspan=4, pady=5, sticky='ew')
    canvas = tk.Canvas(canvas_frame, height=30, bg='white', relief='sunken', borderwidth=1)
    canvas.pack(fill=tk.X, padx=5)

    progress_label = ttk.Label(frame, text="Postęp: --")
    progress_label.grid(row=7, column=0, columnspan=4, pady=5)

    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=8, column=0, columnspan=4, pady=10)

    start_btn = ttk.Button(btn_frame, text="Rozpocznij wyszukiwanie", state='disabled')
    start_btn.pack(side=tk.LEFT, padx=5)
    yes_btn = ttk.Button(btn_frame, text="Tak (wystąpiło)", state='disabled')
    yes_btn.pack(side=tk.LEFT, padx=5)
    no_btn = ttk.Button(btn_frame, text="Nie (brak)", state='disabled')
    no_btn.pack(side=tk.LEFT, padx=5)
    stop_btn = ttk.Button(btn_frame, text="Stop", state='disabled')
    stop_btn.pack(side=tk.LEFT, padx=5)
    undo_btn = ttk.Button(btn_frame, text="Cofnij", state='disabled', command=app.wizard_ctrl.undo_step)
    undo_btn.pack(side=tk.LEFT, padx=5)
    export_btn = ttk.Button(btn_frame, text="Eksportuj sesję", state='disabled',
                            command=app.wizard_ctrl.export_session)
    export_btn.pack(side=tk.LEFT, padx=5)
    import_btn = ttk.Button(btn_frame, text="Importuj sesję",
                            command=app.wizard_ctrl.import_session)
    import_btn.pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Reset", command=app.wizard_ctrl.reset).pack(side=tk.LEFT, padx=5)

    app.wizard_file_var = file_var
    app.wizard_info = info_label
    app.wizard_id_var = id_var
    app.wizard_data_var = data_var
    app.wizard_extended_var = extended_var
    app.wizard_mode_var = mode_var
    app.wizard_seq_listbox = seq_listbox
    app.wizard_parts_var = parts_var
    app.wizard_interval = interval_var
    app.wizard_use_timestamps = timestamps_var
    app.wizard_canvas = canvas
    app.wizard_progress = progress_label
    app.wizard_start_btn = start_btn
    app.wizard_yes_btn = yes_btn
    app.wizard_no_btn = no_btn
    app.wizard_stop_btn = stop_btn
    app.wizard_undo_btn = undo_btn
    app.wizard_export_btn = export_btn

    start_btn.config(command=app.wizard_ctrl.start_search)
    yes_btn.config(command=app.wizard_ctrl.answer_yes)
    no_btn.config(command=app.wizard_ctrl.answer_no)
    stop_btn.config(command=app.wizard_ctrl.stop_search)


def browse_wizard_file(file_var):
    path = filedialog.askopenfilename(filetypes=[("Logi", "*.txt *.log"), ("Wszystkie", "*.*")])
    if path:
        file_var.set(path)


# Funkcje pomocnicze dla zgodności z app.py
def _update_wizard_progress(app):
    if app.wizard_frames:
        total = len(app.wizard_frames)
        app.wizard_progress.config(text=f"Zakres: [{app.wizard_left} .. {app.wizard_right}] (razem: {total})")
        _redraw_wizard_progress(app)


def _redraw_wizard_progress(app):
    canvas = app.wizard_canvas
    canvas.delete("all")
    total = len(app.wizard_frames)
    if total == 0:
        return
    width = canvas.winfo_width()
    if width <= 10:
        width = 600

    left, right = app.wizard_left, app.wizard_right

    def idx_to_x(idx):
        return int((idx / (total - 1)) * width) if total > 1 else 0

    x_left = idx_to_x(left)
    x_right = idx_to_x(right)
    mid = (left + right) // 2
    x_mid = idx_to_x(mid)

    canvas.create_rectangle(0, 0, width, 30, fill='lightgray', outline='')
    canvas.create_rectangle(x_left, 0, x_right, 30, fill='lightblue', outline='darkblue')
    canvas.create_line(x_mid, 0, x_mid, 30, fill='red', width=2)
    canvas.create_text(x_left, 15, text=str(left), anchor='e', font=('Arial', 8))
    canvas.create_text(x_right, 15, text=str(right), anchor='w', font=('Arial', 8))
    canvas.create_text(x_mid, 0, text=str(mid), anchor='s', font=('Arial', 8, 'bold'), fill='red')
