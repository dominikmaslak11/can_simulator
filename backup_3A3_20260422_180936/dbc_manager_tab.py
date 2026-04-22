import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging

logger = logging.getLogger(__name__)


def setup_dbc_manager_tab(app, parent):
    frame = ttk.LabelFrame(parent, text="Plik DBC", padding=10)
    frame.pack(fill=tk.X, padx=10, pady=5)

    dbc_path_var = tk.StringVar()
    ttk.Label(frame, text="Ścieżka DBC:").grid(row=0, column=0, sticky=tk.W)
    ttk.Entry(frame, textvariable=dbc_path_var, width=50).grid(row=0, column=1, padx=5)
    ttk.Button(frame, text="Przeglądaj", command=lambda: browse_dbc(dbc_path_var)).grid(row=0, column=2)

    status_var = tk.StringVar(value="Nie wczytano DBC")
    ttk.Label(frame, textvariable=status_var).grid(row=1, column=0, columnspan=3, pady=5)

    def browse_dbc(var):
        path = filedialog.askopenfilename(filetypes=[("DBC files", "*.dbc"), ("All files", "*.*")])
        if path:
            var.set(path)
            load_dbc(path)

    def load_dbc(path):
        from dbc_manager import DBCManager
        if not hasattr(app, 'dbc_manager'):
            app.dbc_manager = DBCManager()
        if app.dbc_manager.load_dbc(path):
            status_var.set(f"Wczytano: {path}")
            app.log(f"DBC wczytany: {path}")
            update_signal_list()
        # Odśwież listy sygnałów w innych zakładkach
        if hasattr(app, "chart_tab") and hasattr(app.chart_tab, "signal_combo"):
            signals = app.dbc_manager.get_available_signals()
            app.chart_tab.signal_combo["values"] = signals

        else:
            messagebox.showerror("Błąd", "Nie udało się wczytać pliku DBC.")
            status_var.set("Błąd wczytywania")

    # Lista sygnałów (do wykorzystania w innych zakładkach)
    list_frame = ttk.LabelFrame(parent, text="Dostępne sygnały", padding=10)
    list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    signal_listbox = tk.Listbox(list_frame)
    signal_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=signal_listbox.yview)
    signal_listbox.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def update_signal_list():
        signal_listbox.delete(0, tk.END)
        if hasattr(app, 'dbc_manager') and app.dbc_manager.db:
            for sig in app.dbc_manager.get_available_signals():
                signal_listbox.insert(tk.END, sig)

    # Zapisz referencję do listboxa w app, aby inne zakładki mogły z niego korzystać
    app.dbc_signal_listbox = signal_listbox
