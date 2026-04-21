import tkinter as tk
from tkinter import ttk

def setup_missing_tab(app, tab):
    frame = ttk.Frame(tab, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame, text="Interwał 0C00008F (s):").grid(row=0, column=0, sticky=tk.W)
    missing_8f = tk.DoubleVar(value=1.0)
    ttk.Spinbox(frame, from_=0.1, to=10.0, textvariable=missing_8f, width=10).grid(row=0, column=1)

    ttk.Label(frame, text="Interwał diagnostycznych (s):").grid(row=1, column=0, sticky=tk.W)
    missing_diag = tk.DoubleVar(value=30.0)
    ttk.Spinbox(frame, from_=1.0, to=120.0, textvariable=missing_diag, width=10).grid(row=1, column=1)

    ttk.Label(frame, text="Interwał sporadycznych (s):").grid(row=2, column=0, sticky=tk.W)
    missing_spor = tk.DoubleVar(value=60.0)
    ttk.Spinbox(frame, from_=1.0, to=300.0, textvariable=missing_spor, width=10).grid(row=2, column=1)

    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=3, column=0, columnspan=2, pady=20)

    start_btn = ttk.Button(btn_frame, text="Start symulacji", state='disabled')
    start_btn.pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Pauza", command=app.pause_sim).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Stop", command=app.stop_sim).pack(side=tk.LEFT, padx=5)

    app.missing_8f = missing_8f
    app.missing_diag = missing_diag
    app.missing_spor = missing_spor
    app.missing_start_btn = start_btn
    start_btn.config(command=app.missing_ctrl.start_missing)
