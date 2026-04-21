import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

def setup_manual_tab(app, tab):
    frame = ttk.Frame(tab, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame, text="ID (hex):").grid(row=0, column=0, sticky=tk.W, pady=5)
    id_var = tk.StringVar(value="0C00008F")
    ttk.Entry(frame, textvariable=id_var, width=15).grid(row=0, column=1, padx=5)

    ttk.Label(frame, text="Dane (hex):").grid(row=1, column=0, sticky=tk.W, pady=5)
    data_var = tk.StringVar(value="0101")
    ttk.Entry(frame, textvariable=data_var, width=30).grid(row=1, column=1, padx=5)

    extended_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(frame, text="Ramka rozszerzona (29-bit)", variable=extended_var).grid(row=2, column=0, columnspan=2, pady=5)

    ttk.Label(frame, text="Interwał cykliczny (s, 0 = jednorazowo):").grid(row=3, column=0, sticky=tk.W, pady=5)
    interval_var = tk.DoubleVar(value=1.0)
    ttk.Spinbox(frame, from_=0.0, to=60.0, increment=0.1, textvariable=interval_var, width=10).grid(row=3, column=1, sticky=tk.W, padx=5)

    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=4, column=0, columnspan=2, pady=20)

    send_once_btn = ttk.Button(btn_frame, text="Wyślij raz", state='disabled')
    send_once_btn.pack(side=tk.LEFT, padx=5)
    start_cyclic_btn = ttk.Button(btn_frame, text="Start cykliczny", state='disabled')
    start_cyclic_btn.pack(side=tk.LEFT, padx=5)
    stop_cyclic_btn = ttk.Button(btn_frame, text="Stop", state='disabled')
    stop_cyclic_btn.pack(side=tk.LEFT, padx=5)

    app.manual_id = id_var
    app.manual_data = data_var
    app.manual_extended = extended_var
    app.manual_interval = interval_var
    app.manual_send_once_btn = send_once_btn
    app.manual_start_btn = start_cyclic_btn
    app.manual_stop_btn = stop_cyclic_btn

    send_once_btn.config(command=app.manual_ctrl.manual_send_once)
    start_cyclic_btn.config(command=app.manual_ctrl.manual_start_cyclic)
    stop_cyclic_btn.config(command=app.manual_ctrl.manual_stop_cyclic)
