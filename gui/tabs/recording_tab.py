import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import os
from datetime import datetime

class RecordingTab:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.recording = False
        self.record_thread = None
        self.output_file = None
        self.start_time = None
        self.frame_count = 0

        self._create_widgets()

    def _create_widgets(self):
        frame = ttk.LabelFrame(self.parent, text="Nagrywanie sesji CAN", padding=10)
        frame.pack(fill=tk.X, padx=5, pady=5)

        # Wybór pliku
        ttk.Label(frame, text="Plik wyjściowy:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.file_var = tk.StringVar(value=f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.candump")
        ttk.Entry(frame, textvariable=self.file_var, width=40).grid(row=0, column=1, padx=5)
        ttk.Button(frame, text="Przeglądaj", command=self._browse_file).grid(row=0, column=2, padx=5)

        # Czas nagrywania
        ttk.Label(frame, text="Czas nagrywania (s, 0 = bez limitu):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.duration_var = tk.IntVar(value=0)
        ttk.Spinbox(frame, from_=0, to=3600, textvariable=self.duration_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=5)

        # Przyciski
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=3, pady=10)
        self.record_btn = ttk.Button(btn_frame, text="Rozpocznij nagrywanie", command=self.toggle_recording)
        self.record_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Odtwórz nagranie", command=self._replay_recording).pack(side=tk.LEFT, padx=5)

        # Status
        self.status_var = tk.StringVar(value="Zatrzymane")
        ttk.Label(frame, textvariable=self.status_var).grid(row=3, column=0, columnspan=3, pady=5)

        # Licznik ramek
        self.count_var = tk.StringVar(value="Zapisane ramki: 0")
        ttk.Label(frame, textvariable=self.count_var).grid(row=4, column=0, columnspan=3)

    def _browse_file(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".candump",
            filetypes=[("Candump files", "*.candump"), ("All files", "*.*")]
        )
        if path:
            self.file_var.set(path)

    def toggle_recording(self):
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        if not hasattr(self.app, 'can') or not hasattr(self.app.can, 'add_frame_callback'):
            messagebox.showerror("Błąd", "Interfejs CAN nie obsługuje nagrywania.")
            return

        self.output_file = self.file_var.get().strip()
        if not self.output_file:
            messagebox.showerror("Błąd", "Wybierz plik wyjściowy.")
            return

        try:
            # Otwórz plik do zapisu
            self.fd = open(self.output_file, 'w', encoding='utf-8')
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie można utworzyć pliku: {e}")
            return

        # Rejestruj callback
        self.app.can.add_frame_callback(self._on_frame)

        self.recording = True
        self.start_time = time.time()
        self.frame_count = 0
        self.record_btn.config(text="Zatrzymaj nagrywanie")
        self.status_var.set("Nagrywanie...")
        self.count_var.set("Zapisane ramki: 0")

        # Wątek do automatycznego zatrzymania po czasie
        duration = self.duration_var.get()
        if duration > 0:
            self.stop_timer = threading.Timer(duration, self.stop_recording)
            self.stop_timer.start()

    def _on_frame(self, frame):
        if not self.recording:
            return
        try:
            # Format candump: (timestamp) interface id#data
            ts = frame.get('timestamp', time.time())
            can_id = frame['id']
            if isinstance(can_id, str):
                can_id = int(can_id, 16) if can_id.startswith('0x') else int(can_id)
            data_str = ''.join(f'{b:02X}' for b in frame['data'])
            line = f"({ts:.6f}) vcan0 {can_id:03X}#{data_str}\n"
            self.fd.write(line)
            self.fd.flush()
            self.frame_count += 1
            # Aktualizuj GUI co 10 ramek
            if self.frame_count % 10 == 0:
                self.parent.after(0, lambda: self.count_var.set(f"Zapisane ramki: {self.frame_count}"))
        except Exception as e:
            pass

    def stop_recording(self):
        if not self.recording:
            return
        self.recording = False
        if hasattr(self, 'stop_timer'):
            self.stop_timer.cancel()
        if hasattr(self, 'fd'):
            self.fd.close()
        self.record_btn.config(text="Rozpocznij nagrywanie")
        self.status_var.set("Zatrzymane")
        self.count_var.set(f"Zapisane ramki: {self.frame_count}")
        self.app.log(f"Nagrano {self.frame_count} ramek do {self.output_file}")

    def _replay_recording(self):
        filepath = self.file_var.get().strip()
        if not filepath or not os.path.exists(filepath):
            messagebox.showerror("Błąd", "Plik nie istnieje.")
            return
        # Przekieruj do zakładki odtwarzania
        self.app.notebook.select(self.app.tab_replay)
        if hasattr(self.app, 'replay_file_var'):
            self.app.replay_file_var.set(filepath)
        self.app.log(f"Wybrano plik do odtworzenia: {filepath}")

def setup_recording_tab(app, parent):
    RecordingTab(parent, app)
