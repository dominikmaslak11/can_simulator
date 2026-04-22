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
            # Odśwież listy w innych zakładkach
            if hasattr(app, "chart_tab") and hasattr(app.chart_tab, "signal_combo"):
                signals = app.dbc_manager.get_available_signals()
                app.chart_tab.signal_combo["values"] = signals
            if hasattr(app, "forecast_signal_combo"):
                signals = app.dbc_manager.get_available_signals()
                app.forecast_signal_combo["values"] = signals
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

    export_btn = ttk.Button(list_frame, text="Eksportuj listę sygnałów do CSV", command=lambda: export_signals(app))
    export_btn.pack(pady=5)

    # Podgląd szczegółów sygnału
    info_frame = ttk.LabelFrame(parent, text="Szczegóły sygnału", padding=10)
    info_frame.pack(fill=tk.X, padx=10, pady=5)
    info_text = tk.Text(info_frame, height=6, state=tk.DISABLED)
    info_text.pack(fill=tk.BOTH, expand=True)

    def on_signal_select(event):
        selection = signal_listbox.curselection()
        if not selection:
            return
        sig_name = signal_listbox.get(selection[0])
        info = app.dbc_manager.get_signal_info(sig_name)
        if info:
            text = f"Nazwa: {sig_name}\n"
            text += f"Minimum: {info['min']}\n"
            text += f"Maksimum: {info['max']}\n"
            text += f"Jednostka: {info['unit']}\n"
            text += f"Komentarz: {info['comment']}"
            info_text.config(state=tk.NORMAL)
            info_text.delete(1.0, tk.END)
            info_text.insert(tk.END, text)
            info_text.config(state=tk.DISABLED)

    signal_listbox.bind("<<ListboxSelect>>", on_signal_select)

    def export_signals(app):
        from tkinter import filedialog, messagebox
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if path:
            if app.dbc_manager.export_signals_to_csv(path):
                messagebox.showinfo("Sukces", f"Wyeksportowano do {path}")
            else:
                messagebox.showerror("Błąd", "Nie udało się wyeksportować.")

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
