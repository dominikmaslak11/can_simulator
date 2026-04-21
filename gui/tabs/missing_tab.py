import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

def setup_missing_tab(app, tab):
    frame = ttk.Frame(tab, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)

    # --- Panel referencyjny dla timestampów ---
    ref_frame = ttk.LabelFrame(frame, text="Oryginalne odstępy czasowe", padding=5)
    ref_frame.pack(fill=tk.X, pady=(0, 10))

    ttk.Label(ref_frame, text="Plik referencyjny:").grid(row=0, column=0, sticky=tk.W)
    ref_file_var = tk.StringVar()
    ttk.Entry(ref_frame, textvariable=ref_file_var, width=50).grid(row=0, column=1, padx=5)
    ttk.Button(ref_frame, text="Przeglądaj", command=lambda: browse_missing_ref(ref_file_var)).grid(row=0, column=2)
    ttk.Button(ref_frame, text="Analizuj", command=lambda: app.missing_ctrl.analyze_reference_file()).grid(row=0, column=3, padx=5)

    use_timestamps_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(ref_frame, text="Użyj oryginalnych odstępów czasowych z pliku",
                    variable=use_timestamps_var).grid(row=1, column=0, columnspan=4, pady=5)

    # --- Tabela ramek ---
    table_frame = ttk.LabelFrame(frame, text="Ramki do wysłania", padding=5)
    table_frame.pack(fill=tk.BOTH, expand=True)

    columns = ('id', 'data', 'ext', 'interval')
    tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=10)
    tree.heading('id', text='ID (hex)')
    tree.heading('data', text='Dane (hex)')
    tree.heading('ext', text='EXT')
    tree.heading('interval', text='Interwał [s]')

    tree.column('id', width=100)
    tree.column('data', width=200)
    tree.column('ext', width=50)
    tree.column('interval', width=100)

    vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.grid(row=0, column=0, sticky=tk.NSEW)
    vsb.grid(row=0, column=1, sticky=tk.NS)
    table_frame.grid_rowconfigure(0, weight=1)
    table_frame.grid_columnconfigure(0, weight=1)

    btn_frame = ttk.Frame(frame)
    btn_frame.pack(pady=5)
    ttk.Button(btn_frame, text="Dodaj", command=lambda: add_missing_frame(app, tree)).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Usuń", command=lambda: delete_missing_frame(app, tree)).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Edytuj", command=lambda: edit_missing_frame(app, tree)).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Wyczyść", command=lambda: clear_missing_frames(app, tree)).pack(side=tk.LEFT, padx=2)

    ctrl_frame = ttk.Frame(frame)
    ctrl_frame.pack(pady=10)
    start_btn = ttk.Button(ctrl_frame, text="Start symulacji", state='disabled')
    start_btn.pack(side=tk.LEFT, padx=5)
    ttk.Button(ctrl_frame, text="Pauza", command=app.pause_sim).pack(side=tk.LEFT, padx=5)
    ttk.Button(ctrl_frame, text="Stop", command=app.stop_sim).pack(side=tk.LEFT, padx=5)

    app.missing_ref_file = ref_file_var
    app.missing_use_timestamps = use_timestamps_var
    app.missing_tree = tree
    app.missing_start_btn = start_btn
    start_btn.config(command=lambda: app.missing_ctrl.start_missing())

def browse_missing_ref(file_var):
    path = filedialog.askopenfilename(filetypes=[("Logi", "*.txt *.log"), ("Wszystkie", "*.*")])
    if path:
        file_var.set(path)

# --- Funkcje obsługi tabeli (dodaj, usuń, edytuj, wyczyść) – bez zmian ---
def add_missing_frame(app, tree):
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

    ext_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(dialog, text="Ramka rozszerzona", variable=ext_var).grid(row=2, column=0, columnspan=2)

    ttk.Label(dialog, text="Interwał (s):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
    interval_var = tk.DoubleVar(value=1.0)
    ttk.Entry(dialog, textvariable=interval_var, width=10).grid(row=3, column=1, sticky=tk.W, padx=5)

    def save():
        try:
            cid = int(id_var.get().strip(), 16)
            data = bytes.fromhex(data_var.get().strip())
        except ValueError:
            messagebox.showerror("Błąd", "Nieprawidłowy format ID lub danych.")
            return
        is_ext = ext_var.get()
        interval = interval_var.get()
        app.missing_ctrl.add_frame(cid, data, is_ext, interval)
        tree.insert("", tk.END, values=(f"0x{cid:08X}", data.hex().upper(), "X" if is_ext else "", f"{interval:.3f}"))
        dialog.destroy()

    ttk.Button(dialog, text="Zapisz", command=save).grid(row=4, column=0, columnspan=2, pady=10)

def delete_missing_frame(app, tree):
    sel = tree.selection()
    if not sel:
        messagebox.showinfo("Brak zaznaczenia", "Zaznacz ramkę do usunięcia.")
        return
    item = sel[0]
    idx = tree.index(item)
    app.missing_ctrl.remove_frame(idx)
    tree.delete(item)

def edit_missing_frame(app, tree):
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
    interval = float(values[3])

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

    ttk.Label(dialog, text="Interwał (s):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
    interval_var = tk.DoubleVar(value=interval)
    ttk.Entry(dialog, textvariable=interval_var, width=10).grid(row=3, column=1, sticky=tk.W, padx=5)

    def save():
        try:
            new_cid = int(id_var.get().strip(), 16)
            new_data = bytes.fromhex(data_var.get().strip())
        except ValueError:
            messagebox.showerror("Błąd", "Nieprawidłowy format ID lub danych.")
            return
        new_ext = ext_var.get()
        new_interval = interval_var.get()
        app.missing_ctrl.update_frame(idx, new_cid, new_data, new_ext, new_interval)
        tree.item(item, values=(f"0x{new_cid:08X}", new_data.hex().upper(), "X" if new_ext else "", f"{new_interval:.3f}"))
        dialog.destroy()

    ttk.Button(dialog, text="Zapisz", command=save).grid(row=4, column=0, columnspan=2, pady=10)

def clear_missing_frames(app, tree):
    app.missing_ctrl.clear_frames()
    tree.delete(*tree.get_children())
