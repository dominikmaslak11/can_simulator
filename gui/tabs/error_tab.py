import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

def setup_error_tab(app, tab):
    frame = ttk.Frame(tab, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)

    # Interwał powtarzania sekwencji
    ttk.Label(frame, text="Interwał powtarzania sekwencji (s):").grid(row=0, column=0, sticky=tk.W, pady=5)
    error_interval = tk.DoubleVar(value=10.0)
    ttk.Spinbox(frame, from_=0.5, to=60.0, textvariable=error_interval, width=10).grid(row=0, column=1, sticky=tk.W)

    # --- Panel referencyjny dla timestampów ---
    ref_frame = ttk.LabelFrame(frame, text="Oryginalne odstępy czasowe", padding=5)
    ref_frame.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(10, 10))

    ttk.Label(ref_frame, text="Plik referencyjny:").grid(row=0, column=0, sticky=tk.W)
    ref_file_var = tk.StringVar()
    ttk.Entry(ref_frame, textvariable=ref_file_var, width=50).grid(row=0, column=1, padx=5)
    ttk.Button(ref_frame, text="Przeglądaj", command=lambda: browse_error_ref(ref_file_var)).grid(row=0, column=2)
    ttk.Button(ref_frame, text="Analizuj", command=lambda: app.error_ctrl.analyze_reference_file()).grid(row=0, column=3, padx=5)

    use_timestamps_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(ref_frame, text="Użyj oryginalnych odstępów czasowych z pliku",
                    variable=use_timestamps_var).grid(row=1, column=0, columnspan=4, pady=5)

    # --- Tabela ramek ---
    table_frame = ttk.LabelFrame(frame, text="Sekwencja ramek do wysłania", padding=5)
    table_frame.grid(row=2, column=0, columnspan=2, sticky=tk.NSEW, pady=10)
    frame.grid_rowconfigure(2, weight=1)
    frame.grid_columnconfigure(0, weight=1)

    columns = ('id', 'data', 'ext', 'delay')
    tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=10)
    tree.heading('id', text='ID (hex)')
    tree.heading('data', text='Dane (hex)')
    tree.heading('ext', text='EXT')
    tree.heading('delay', text='Opóźnienie [s]')

    tree.column('id', width=100)
    tree.column('data', width=200)
    tree.column('ext', width=50)
    tree.column('delay', width=100)

    vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.grid(row=0, column=0, sticky=tk.NSEW)
    vsb.grid(row=0, column=1, sticky=tk.NS)
    table_frame.grid_rowconfigure(0, weight=1)
    table_frame.grid_columnconfigure(0, weight=1)

    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=3, column=0, columnspan=2, pady=5)
    ttk.Button(btn_frame, text="Dodaj", command=lambda: add_error_frame(app, tree)).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Usuń", command=lambda: delete_error_frame(app, tree)).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Edytuj", command=lambda: edit_error_frame(app, tree)).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Wyczyść", command=lambda: clear_error_frames(app, tree)).pack(side=tk.LEFT, padx=2)

    ctrl_frame = ttk.Frame(frame)
    ctrl_frame.grid(row=4, column=0, columnspan=2, pady=10)
    start_btn = ttk.Button(ctrl_frame, text="Start symulacji", state='disabled')
    start_btn.pack(side=tk.LEFT, padx=5)
    ttk.Button(ctrl_frame, text="Pauza", command=app.pause_sim).pack(side=tk.LEFT, padx=5)
    ttk.Button(ctrl_frame, text="Stop", command=app.stop_sim).pack(side=tk.LEFT, padx=5)

    app.error_interval = error_interval
    app.error_ref_file = ref_file_var
    app.error_use_timestamps = use_timestamps_var
    app.error_tree = tree
    app.error_start_btn = start_btn
    start_btn.config(command=lambda: app.error_ctrl.start_error())

def browse_error_ref(file_var):
    path = filedialog.askopenfilename(filetypes=[("Logi", "*.txt *.log"), ("Wszystkie", "*.*")])
    if path:
        file_var.set(path)

# --- Funkcje tabeli (dodaj, usuń, edytuj, wyczyść) – bez zmian ---
def add_error_frame(app, tree):
    dialog = tk.Toplevel(app.root)
    dialog.title("Dodaj ramkę")
    dialog.geometry("300x250")
    dialog.transient(app.root)
    dialog.grab_set()

    ttk.Label(dialog, text="ID (hex):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
    id_var = tk.StringVar()
    ttk.Entry(dialog, textvariable=id_var, width=15).grid(row=0, column=1, padx=5)

    ttk.Label(dialog, text="Dane (hex):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
    data_var = tk.StringVar()
    ttk.Entry(dialog, textvariable=data_var, width=30).grid(row=1, column=1, padx=5)

    ext_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(dialog, text="Ramka rozszerzona", variable=ext_var).grid(row=2, column=0, columnspan=2)

    ttk.Label(dialog, text="Opóźnienie po poprzedniej (s):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
    delay_var = tk.DoubleVar(value=0.25)
    ttk.Entry(dialog, textvariable=delay_var, width=10).grid(row=3, column=1, sticky=tk.W, padx=5)

    def save():
        try:
            cid = int(id_var.get().strip(), 16)
            data = bytes.fromhex(data_var.get().strip())
        except ValueError:
            messagebox.showerror("Błąd", "Nieprawidłowy format ID lub danych.")
            return
        is_ext = ext_var.get()
        delay = delay_var.get()
        app.error_ctrl.add_frame(cid, data, is_ext, delay)
        tree.insert("", tk.END, values=(f"0x{cid:08X}", data.hex().upper(), "X" if is_ext else "", f"{delay:.3f}"))
        dialog.destroy()

    ttk.Button(dialog, text="Zapisz", command=save).grid(row=4, column=0, columnspan=2, pady=10)

def delete_error_frame(app, tree):
    sel = tree.selection()
    if not sel:
        messagebox.showinfo("Brak zaznaczenia", "Zaznacz ramkę do usunięcia.")
        return
    item = sel[0]
    idx = tree.index(item)
    app.error_ctrl.remove_frame(idx)
    tree.delete(item)

def edit_error_frame(app, tree):
    sel = tree.selection()
    if not sel:
        messagebox.showinfo("Brak zaznaczenia", "Zaznacz ramkę do edycji.")
        return
    item = sel[0]
    idx = tree.index(item)
    values = tree.item(item, 'values')
    cid = int(values[0], 16)
    data = bytes.fromhex(values[1])
    is_ext = values[2] == "X"
    delay = float(values[3])

    dialog = tk.Toplevel(app.root)
    dialog.title("Edytuj ramkę")
    dialog.geometry("300x250")
    dialog.transient(app.root)
    dialog.grab_set()

    ttk.Label(dialog, text="ID (hex):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
    id_var = tk.StringVar(value=f"{cid:08X}")
    ttk.Entry(dialog, textvariable=id_var, width=15).grid(row=0, column=1, padx=5)

    ttk.Label(dialog, text="Dane (hex):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
    data_var = tk.StringVar(value=data.hex().upper())
    ttk.Entry(dialog, textvariable=data_var, width=30).grid(row=1, column=1, padx=5)

    ext_var = tk.BooleanVar(value=is_ext)
    ttk.Checkbutton(dialog, text="Ramka rozszerzona", variable=ext_var).grid(row=2, column=0, columnspan=2)

    ttk.Label(dialog, text="Opóźnienie (s):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
    delay_var = tk.DoubleVar(value=delay)
    ttk.Entry(dialog, textvariable=delay_var, width=10).grid(row=3, column=1, sticky=tk.W, padx=5)

    def save():
        try:
            new_cid = int(id_var.get().strip(), 16)
            new_data = bytes.fromhex(data_var.get().strip())
        except ValueError:
            messagebox.showerror("Błąd", "Nieprawidłowy format ID lub danych.")
            return
        new_ext = ext_var.get()
        new_delay = delay_var.get()
        app.error_ctrl.update_frame(idx, new_cid, new_data, new_ext, new_delay)
        tree.item(item, values=(f"0x{new_cid:08X}", new_data.hex().upper(), "X" if new_ext else "", f"{new_delay:.3f}"))
        dialog.destroy()

    ttk.Button(dialog, text="Zapisz", command=save).grid(row=4, column=0, columnspan=2, pady=10)

def clear_error_frames(app, tree):
    app.error_ctrl.clear_frames()
    tree.delete(*tree.get_children())
