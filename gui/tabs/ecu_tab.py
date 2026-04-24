import tkinter as tk
from tkinter import ttk, messagebox
from controllers.ecu_emulator import EcuEmulator

class EcuTab(ttk.Frame):
    def __init__(self, app, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.emu = None
        self.create_widgets()

    def create_widgets(self):
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Emulator prostego ECU (OBD-II)").pack(anchor=tk.W)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)

        self.start_btn = ttk.Button(btn_frame, text="Start", command=self.start_emu)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop_emu, state='disabled')
        self.stop_btn.pack(side=tk.LEFT)

        self.status_lbl = ttk.Label(frame, text="Zatrzymany", foreground="red")
        self.status_lbl.pack(anchor=tk.W, pady=5)

    def start_emu(self):
        if not self.app.can.connected:
            messagebox.showerror("Błąd", "Połącz się z CAN przed uruchomieniem emulatora.")
            return
        self.emu = EcuEmulator(self.app.can)
        self.emu.start()
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.status_lbl.config(text="Pracuje", foreground="green")
        self.app.log("[ECU] Emulator uruchomiony")

    def stop_emu(self):
        if self.emu:
            self.emu.stop()
            self.emu = None
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.status_lbl.config(text="Zatrzymany", foreground="red")
        self.app.log("[ECU] Emulator zatrzymany")
