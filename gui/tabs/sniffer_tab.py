import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import threading

def setup_sniffer_tab(app, tab):
    frame = ttk.Frame(tab, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)

    # Pasek narzędzi
    toolbar = ttk.Frame(frame)
    toolbar.pack(fill=tk.X, pady=(0, 5))

    start_btn = ttk.Button(toolbar, text="Start", command=app.sniffer_ctrl.start_sniffer)
    start_btn.pack(side=tk.LEFT, padx=2)
    stop_btn = ttk.Button(toolbar, text="Stop", command=app.sniffer_ctrl.stop_sniffer, state='disabled')
    stop_btn.pack(side=tk.LEFT, padx=2)
    clear_btn = ttk.Button(toolbar, text="Wyczyść", command=app.sniffer_ctrl.clear_sniffer)
    clear_btn.pack(side=tk.LEFT, padx=2)
    export_btn = ttk.Button(toolbar, text="Eksportuj", command=app.sniffer_ctrl.export_sniffer)
    export_btn.pack(side=tk.LEFT, padx=2)

    filter_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(toolbar, text="Filtruj ID", variable=filter_var,
                    command=app.sniffer_ctrl.toggle_filter).pack(side=tk.LEFT, padx=5)
    filter_entry = ttk.Entry(toolbar, width=20, state='disabled')
    filter_entry.pack(side=tk.LEFT, padx=2)
    ttk.Button(toolbar, text="Ustaw filtr", command=app.sniffer_ctrl.apply_filter).pack(side=tk.LEFT, padx=2)

    keep_alive_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(toolbar, text="Nigdy nie gasnąca ramka", variable=keep_alive_var,
                    command=app.sniffer_ctrl.toggle_keep_alive).pack(side=tk.LEFT, padx=5)

    overwrite_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(toolbar, text="Tryb nadpisywania", variable=overwrite_var,
                    command=app.sniffer_ctrl.toggle_overwrite).pack(side=tk.LEFT, padx=5)

    bit_view_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(toolbar, text="Widok bitowy", variable=bit_view_var,
                    command=app.sniffer_ctrl.toggle_bit_view).pack(side=tk.LEFT, padx=5)

    # Tabela ramek
    tree_frame = ttk.Frame(frame)
    tree_frame.pack(fill=tk.BOTH, expand=True)

    # Definiujemy dwie konfiguracje kolumn: normalną i bitową
    columns_normal = ('timestamp', 'id', 'ext', 'dlc', 'data')
    columns_bit = ('timestamp', 'id', 'ext', 'dlc', 'bits')

    tree = ttk.Treeview(tree_frame, columns=columns_normal, show='headings', height=20)
    tree.heading('timestamp', text='Czas')
    tree.heading('id', text='ID')
    tree.heading('ext', text='EXT')
    tree.heading('dlc', text='DLC')
    tree.heading('data', text='Dane (hex)')

    tree.column('timestamp', width=100)
    tree.column('id', width=100)
    tree.column('ext', width=50)
    tree.column('dlc', width=50)
    tree.column('data', width=300)

    vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.grid(row=0, column=0, sticky='nsew')
    vsb.grid(row=0, column=1, sticky='ns')

    tree_frame.grid_rowconfigure(0, weight=1)
    tree_frame.grid_columnconfigure(0, weight=1)

    # Pasek statusu
    status_var = tk.StringVar(value="Zatrzymany")
    status_label = ttk.Label(frame, textvariable=status_var)
    status_label.pack(fill=tk.X, pady=(5, 0))

    # Zapis referencji do obiektu app
    app.sniffer_tree = tree
    app.sniffer_start_btn = start_btn
    app.sniffer_stop_btn = stop_btn
    app.sniffer_status = status_var
    app.sniffer_filter_var = filter_var
    app.sniffer_filter_entry = filter_entry
    app.sniffer_keep_alive_var = keep_alive_var
    app.sniffer_overwrite_var = overwrite_var
    app.sniffer_bit_view_var = bit_view_var
    app.sniffer_columns_normal = columns_normal
    app.sniffer_columns_bit = columns_bit
