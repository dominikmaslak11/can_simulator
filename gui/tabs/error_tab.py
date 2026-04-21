import tkinter as tk
from tkinter import ttk

def setup_error_tab(app, tab):
    frame = ttk.Frame(tab, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame, text="Interwał (s):").grid(row=0, column=0, sticky=tk.W)
    error_interval = tk.DoubleVar(value=10.0)
    ttk.Spinbox(frame, from_=0.5, to=60.0, textvariable=error_interval, width=10).grid(row=0, column=1)

    ttk.Label(frame, text="Kod startowy (hex):").grid(row=1, column=0, sticky=tk.W)
    error_code = tk.StringVar(value="19")
    ttk.Entry(frame, textvariable=error_code, width=10).grid(row=1, column=1)

    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=2, column=0, columnspan=2, pady=20)

    start_btn = ttk.Button(btn_frame, text="Start symulacji", state='disabled')
    start_btn.pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Pauza", command=app.pause_sim).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Stop", command=app.stop_sim).pack(side=tk.LEFT, padx=5)

    app.error_interval = error_interval
    app.error_code = error_code
    app.error_start_btn = start_btn
    start_btn.config(command=app.error_ctrl.start_error)
