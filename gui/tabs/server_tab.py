import tkinter as tk
from tkinter import ttk, messagebox
import threading

from server_mode import CanServer

def setup_server_tab(app, tab):
    frame = ttk.Frame(tab, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)

    config_frame = ttk.LabelFrame(frame, text="Konfiguracja serwera", padding=5)
    config_frame.pack(fill=tk.X, pady=(0,10))

    ttk.Label(config_frame, text="Port:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
    port_var = tk.IntVar(value=5555)
    ttk.Entry(config_frame, textvariable=port_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=5)

    start_btn = ttk.Button(config_frame, text="Start serwera", command=lambda: start_server(app, port_var.get()))
    start_btn.grid(row=0, column=2, padx=5)
    stop_btn = ttk.Button(config_frame, text="Stop serwera", command=lambda: stop_server(app), state='disabled')
    stop_btn.grid(row=0, column=3, padx=5)

    clients_frame = ttk.LabelFrame(frame, text="Aktywni klienci", padding=5)
    clients_frame.pack(fill=tk.BOTH, expand=True)

    clients_list = tk.Listbox(clients_frame, height=6)
    clients_list.pack(fill=tk.BOTH, expand=True)

    status_var = tk.StringVar(value="Serwer zatrzymany")
    ttk.Label(frame, textvariable=status_var).pack(fill=tk.X, pady=(5,0))

    app.server_port = port_var
    app.server_start_btn = start_btn
    app.server_stop_btn = stop_btn
    app.server_clients_list = clients_list
    app.server_status = status_var
    app.server_instance = None


def start_server(app, port):
    if app.server_instance is not None:
        return
    if not app.can.connected:
        messagebox.showerror("Błąd", "Połącz się z CAN przed uruchomieniem serwera.")
        return
    app.server_instance = CanServer(app.can, port)
    app.server_instance.start()
    app.server_start_btn.config(state='disabled')
    app.server_stop_btn.config(state='normal')
    app.server_status.set(f"Serwer działa na porcie {port}")
    app.log(f"[Server] Uruchomiono serwer na porcie {port}")


def stop_server(app):
    if app.server_instance:
        app.server_instance.stop()
        app.server_instance = None
    app.server_start_btn.config(state='normal')
    app.server_stop_btn.config(state='disabled')
    app.server_status.set("Serwer zatrzymany")
    app.server_clients_list.delete(0, tk.END)
    app.log("[Server] Serwer zatrzymany")
