"""Zakładka uczenia asocjacyjnego – Faza 3."""
import tkinter as tk
from tkinter import ttk, messagebox

from controllers.associative_controller import AssociativeController


class AssociativeTab(ttk.Frame):
    def __init__(self, app, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.controller = None
        self.create_widgets()

    def create_widgets(self):
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # Nagłówek
        ttk.Label(frame, text="Interaktywne uczenie asocjacyjne",
                  font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=(0,10))

        # Sterowanie
        ctrl_frame = ttk.Frame(frame)
        ctrl_frame.pack(fill=tk.X, pady=5)

        self.btn_start = ttk.Button(ctrl_frame, text="Start uczenia",
                                    command=self.start_learning)
        self.btn_start.pack(side=tk.LEFT, padx=5)

        self.btn_stop = ttk.Button(ctrl_frame, text="Stop uczenia",
                                   command=self.stop_learning, state='disabled')
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        self.btn_clear = ttk.Button(ctrl_frame, text="Wyczyść dane",
                                    command=self.clear_data)
        self.btn_clear.pack(side=tk.LEFT, padx=5)

        # Checkbox zdarzenia
        self.check_var = tk.BooleanVar()
        self.checkbox = ttk.Checkbutton(ctrl_frame, text="Zdarzenie (np. Hamulec)",
                                        variable=self.check_var,
                                        command=self.toggle_event)
        self.checkbox.pack(side=tk.RIGHT, padx=5)

        # Okno tolerancji
        tolerance_frame = ttk.Frame(frame)
        tolerance_frame.pack(fill=tk.X, pady=5)
        ttk.Label(tolerance_frame, text="Tolerancja czasowa (±ms):").pack(side=tk.LEFT)
        self.tolerance_var = tk.IntVar(value=200)
        self.tolerance_spin = ttk.Spinbox(tolerance_frame, from_=0, to=5000,
                                          textvariable=self.tolerance_var, width=8,
                                          command=self.update_tolerance)
        self.tolerance_spin.pack(side=tk.LEFT, padx=5)

        # Tabela wyników (nowe kolumny: Bajt, Wartość, Tło)
        columns = ("id", "byte", "value", "background", "confidence")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=8)
        self.tree.heading("id", text="CAN ID")
        self.tree.heading("byte", text="Bajt")
        self.tree.heading("value", text="Wartość (zdarzenie)")
        self.tree.heading("background", text="Wartość (tło)")
        self.tree.heading("confidence", text="Pewność (%)")
        self.tree.column("id", width=80)
        self.tree.column("byte", width=50)
        self.tree.column("value", width=120)
        self.tree.column("background", width=100)
        self.tree.column("confidence", width=80)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=10)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Pasek postępu
        status_frame = ttk.Frame(frame)
        status_frame.pack(fill=tk.X, pady=5)
        ttk.Label(status_frame, text="Postęp:").pack(side=tk.LEFT)
        self.progress = ttk.Progressbar(status_frame, length=200, mode='determinate')
        self.progress.pack(side=tk.LEFT, padx=5)
        self.iter_label = ttk.Label(status_frame, text="Iteracje: 0")
        self.iter_label.pack(side=tk.LEFT, padx=5)

        # Podgląd bufora
        buffer_frame = ttk.LabelFrame(frame, text="Ostatnie ramki w buforze", padding=5)
        buffer_frame.pack(fill=tk.BOTH, expand=False, pady=5)
        self.buffer_list = tk.Listbox(buffer_frame, height=5)
        self.buffer_list.pack(fill=tk.BOTH, expand=True)

    # ---- Logika ----
    def start_learning(self):
        if not self.app.can.connected:
            messagebox.showerror("Błąd", "Połącz się z CAN przed rozpoczęciem uczenia.")
            return
        if self.controller is None:
            self.controller = AssociativeController(self.app)
        self.controller.set_tolerance(self.tolerance_var.get())
        self.controller.start()
        self.btn_start.config(state='disabled')
        self.btn_stop.config(state='normal')
        self.app.log("[Assoc] Rozpoczęto uczenie asocjacyjne")
        self._refresh_loop()
        self.update_sniffer_highlight()

    def stop_learning(self):
        if self.controller:
            self.controller.stop()
        self.btn_start.config(state='normal')
        self.btn_stop.config(state='disabled')
        self.app.log("[Assoc] Zatrzymano uczenie asocjacyjne")

    def clear_data(self):
        if self.controller:
            self.controller.stop()
        self.controller = None
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.buffer_list.delete(0, tk.END)
        self.progress['value'] = 0
        self.iter_label.config(text="Iteracje: 0")
        self.app.log("[Assoc] Wyczyszczono dane")
        self.check_var.set(False)

    def toggle_event(self):
        if self.controller:
            self.controller.toggle_event()
            self._update_iter_display()
            state = "ROZPOCZĘTE" if self.check_var.get() else "ZAKOŃCZONE"
            self.app.log(f"[Assoc] Zdarzenie {state}")
            if not self.check_var.get():
                self._update_candidates_table()
        else:
            messagebox.showwarning("Uwaga", "Najpierw rozpocznij uczenie.")

    def update_tolerance(self):
        if self.controller:
            self.controller.set_tolerance(self.tolerance_var.get())

    def _update_iter_display(self):
        if self.controller:
            count = self.controller.get_iteration_count()
            self.iter_label.config(text=f"Iteracje: {count}")
            self.progress['maximum'] = 10
            self.progress['value'] = min(count, 10)

    def _update_candidates_table(self):
        """Pobiera kandydatów bajtowych z kontrolera i wypełnia tabelę."""
        if not self.controller:
            return
        candidates = self.controller.get_candidates()
        for item in self.tree.get_children():
            self.tree.delete(item)
        for c in candidates:
            bg = f"0x{c['background']:02X}" if c['background'] is not None else "brak"
            self.tree.insert("", "end", values=(
                f"0x{c['id']:X}",
                c['byte'],
                f"0x{c['value']:02X}",
                bg,
                f"{c['confidence']:.1f}"
            ))


    def update_sniffer_highlight(self):
        """Wysyła listę ID do sniffera w celu podświetlenia."""
        if self.controller and self.controller.running:
            ids = self.controller.get_highlight_ids(threshold=80.0)
            # Próbujemy znaleźć sniffer controller
            if hasattr(self.app, 'sniffer_ctrl'):
                try:
                    self.app.sniffer_ctrl.sniffer.set_highlighted_ids(ids)
                except Exception:
                    pass
            self.after(2000, self.update_sniffer_highlight)

    def _refresh_loop(self):
        """Odświeża podgląd bufora co 500 ms."""
        if self.controller and self.controller.running:
            try:
                snap = self.controller.get_buffer_snapshot(max_items=50)
                self.buffer_list.delete(0, tk.END)
                for rec in snap:
                    info = f"ID=0x{rec['arb_id']:X} DLC={rec['dlc']} Data={bytes(rec['data']).hex()}"
                    self.buffer_list.insert(tk.END, info)
            except Exception:
                pass
            self.after(500, self._refresh_loop)
        else:
            self.buffer_list.delete(0, tk.END)
