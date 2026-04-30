"""Zakładka uczenia asocjacyjnego – Faza 3."""
import tkinter as tk
from tkinter import ttk, messagebox

from controllers.associative_controller import AssociativeController
from controllers.j1939_associative_controller import J1939AssociativeController


class AssociativeTab(ttk.Frame):
    def __init__(self, app, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.controller = None
        self.bus_mode_var = tk.StringVar(value="can")
        self.create_widgets()

    def create_widgets(self):
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # Nagłówek
        ttk.Label(frame, text="Interaktywne uczenie asocjacyjne",
                  font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=(0,10))

        # --- Tryb magistrali (CAN / J1939) ---
        mode_frame = ttk.LabelFrame(frame, text="Tryb magistrali", padding=5)
        mode_frame.pack(fill=tk.X, pady=5)
        ttk.Radiobutton(mode_frame, text="CAN 2.0 (11/29-bit)", variable=self.bus_mode_var,
                        value="can", command=self.on_bus_mode_changed).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="J1939", variable=self.bus_mode_var,
                        value="j1939", command=self.on_bus_mode_changed).pack(side=tk.LEFT, padx=5)


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

        self.btn_export = ttk.Button(ctrl_frame, text="Eksportuj wzorzec",
                                      command=self.export_pattern)
        self.btn_export.pack(side=tk.LEFT, padx=5)

        self.btn_export_csv = ttk.Button(ctrl_frame, text="Eksport CSV",
                                         command=self.export_csv)
        self.btn_export_csv.pack(side=tk.LEFT, padx=5)
        self.btn_export_html = ttk.Button(ctrl_frame, text="Eksport HTML",
                                          command=self.export_html)
        self.btn_export_html.pack(side=tk.LEFT, padx=5)

        self.btn_sequence = ttk.Button(ctrl_frame, text="Szukaj sekwencji",
                                        command=self.search_sequence)
        self.btn_sequence.pack(side=tk.LEFT, padx=5)

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

        # --- Tryb wartościowy ---
        value_frame = ttk.LabelFrame(frame, text="Tryb wartościowy (np. temperatura)", padding=5)
        value_frame.pack(fill=tk.X, pady=10)

        val_entry_frame = ttk.Frame(value_frame)
        val_entry_frame.pack(fill=tk.X, pady=2)
        ttk.Label(val_entry_frame, text="Wartość referencyjna:").pack(side=tk.LEFT)
        self.value_var = tk.StringVar()
        self.value_entry = ttk.Entry(val_entry_frame, textvariable=self.value_var, width=10)
        self.value_entry.pack(side=tk.LEFT, padx=5)
        self.value_entry.bind("<Return>", self.commit_value)
        self.btn_commit_value = ttk.Button(val_entry_frame, text="Zatwierdź",
                                           command=self.commit_value)
        self.btn_commit_value.pack(side=tk.LEFT, padx=5)

        # Historia wartości
        hist_frame = ttk.Frame(value_frame)
        hist_frame.pack(fill=tk.X, pady=2)
        ttk.Label(hist_frame, text="Historia:").pack(side=tk.LEFT)
        self.history_var = tk.StringVar(value="(pusta)")
        ttk.Label(hist_frame, textvariable=self.history_var, foreground="gray").pack(side=tk.LEFT, padx=5)
        self.btn_undo_value = ttk.Button(hist_frame, text="Cofnij ostatnią",
                                         command=self.undo_last_value)
        self.btn_undo_value.pack(side=tk.RIGHT, padx=5)

        # Nazwa zmiennej
        name_frame = ttk.Frame(value_frame)
        name_frame.pack(fill=tk.X, pady=2)
        ttk.Label(name_frame, text="Nazwa zmiennej:").pack(side=tk.LEFT)
        self.variable_name_var = tk.StringVar(value="")
        ttk.Entry(name_frame, textvariable=self.variable_name_var, width=20).pack(side=tk.LEFT, padx=5)

        # Typ zależności
        type_frame = ttk.Frame(value_frame)
        type_frame.pack(fill=tk.X, pady=2)
        ttk.Label(type_frame, text="Typ zależności:").pack(side=tk.LEFT)
        self.correlation_type_var = tk.StringVar(value="linear")
        ttk.Radiobutton(type_frame, text="Liniowa", variable=self.correlation_type_var,
                        value="linear").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(type_frame, text="Dowolna zmiana", variable=self.correlation_type_var,
                        value="any_change").pack(side=tk.LEFT, padx=5)

        # Filtr źródła
        filter_frame = ttk.Frame(value_frame)
        filter_frame.pack(fill=tk.X, pady=2)
        self.filter_var = tk.StringVar(value="all")
        ttk.Radiobutton(filter_frame, text="Wszystkie", variable=self.filter_var,
                        value="all", command=self._update_candidates_table).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(filter_frame, text="Tylko zdarzenia", variable=self.filter_var,
                        value="zdarzenie", command=self._update_candidates_table).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(filter_frame, text="Tylko wartości", variable=self.filter_var,
                        value="wartosc", command=self._update_candidates_table).pack(side=tk.LEFT, padx=5)



        # Tabela wyników (nowe kolumny: Bajt, Wartość, Tło)
        columns = ("id", "byte", "value", "background", "confidence", "source", "sequence")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=8)
        self.tree.heading("id", text="CAN ID")
        self.tree.heading("byte", text="Bajt")
        self.tree.heading("value", text="Wartość (zdarzenie)")
        self.tree.heading("background", text="Wartość (tło)")
        self.tree.heading("confidence", text="Pewność (%)")
        self.tree.heading("source", text="Źródło")
        self.tree.heading("sequence", text="Sekwencja")
        self.tree.column("id", width=80)
        self.tree.column("byte", width=50)
        self.tree.column("value", width=120)
        self.tree.column("background", width=100)
        self.tree.column("confidence", width=80)
        self.tree.column("source", width=100)
        self.tree.column("sequence", width=150)
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

    def on_bus_mode_changed(self):
        """Reaguje na zmianę trybu CAN / J1939."""
        mode = self.bus_mode_var.get()
        self.app.log(f"[Assoc] Przełączono tryb magistrali: {mode}")
        # Zatrzymaj obecny kontroler, jeśli działa
        if self.controller and self.controller.running:
            self.controller.stop()
        # Utwórz nowy kontroler odpowiedniego typu
        if mode == "j1939":
            self.controller = J1939AssociativeController(self.app)
        else:
            self.controller = AssociativeController(self.app)
        self.controller.set_tolerance(self.tolerance_var.get())
        # Jeśli uczenie było włączone, uruchom ponownie
        if self.btn_start['state'] == 'disabled':
            self.controller.start()
        self.app.log(f"[Assoc] Używany kontroler: {type(self.controller).__name__}")

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
        self.bus_mode_var = tk.StringVar(value="can")
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
        mode = self.bus_mode_var.get() if hasattr(self, 'bus_mode_var') else "can"
        for c in candidates:
            bg = f"0x{c['background']:02X}" if c['background'] is not None else "brak"
            src = c.get("source", "zdarzenie")
            seq_str = c.get("ids_order", "")
            if isinstance(seq_str, list):
                seq_str = " -> ".join(str(i) for i in seq_str)
            if mode == "j1939":
                pgn = c.get("pgn", "")
                pgn_name = c.get("pgn_name", "")
                pgn_display = f"0x{pgn:04X}" if isinstance(pgn, int) else str(pgn)
                if pgn_name:
                    pgn_display += f" ({pgn_name})"
                self.tree.insert("", "end", values=(
                    pgn_display,
                    f"0x{c['id']:X}",
                    c.get("source_address", ""),
                    c['byte'],
                    f"0x{c['value']:02X}",
                    bg,
                    f"{c['confidence']:.1f}",
                    src,
                    seq_str
                ))
            else:
                self.tree.insert("", "end", values=(
                    f"0x{c['id']:X}",
                    c['byte'],
                    f"0x{c['value']:02X}",
                    bg,
                    f"{c['confidence']:.1f}",
                    src,
                    seq_str
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


    def export_pattern(self):
        """Eksportuje najlepszy wzorzec do pliku JSON."""
        if not self.controller or not self.controller.get_best_candidate():
            messagebox.showwarning("Brak danych", "Nie znaleziono jeszcze żadnego wzorca.")
            return
        from tkinter import filedialog
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            title="Zapisz wzorzec asocjacyjny"
        )
        if not filepath:
            return
        try:
            self.controller.export_pattern(filepath)
            self.app.log(f"[Assoc] Wzorzec wyeksportowany do {filepath}")
        except Exception as e:
            messagebox.showerror("Błąd eksportu", str(e))


    def commit_value(self, event=None):
        """Zatwierdza wartość referencyjną i przekazuje do kontrolera."""
        if not self.controller or not self.controller.running:
            messagebox.showwarning("Uwaga", "Najpierw rozpocznij uczenie.")
            return
        val_str = self.value_var.get().strip()
        if not val_str:
            return
        try:
            val = float(val_str)
        except ValueError:
            messagebox.showerror("Błąd", "Wartość musi być liczbą.")
            return
        self.controller.commit_value(val)
        self.value_var.set("")
        self.app.log(f"[Assoc] Zatwierdzono wartość referencyjną: {val}")
        # Aktualizuj historię
        self._update_value_history()

    def undo_last_value(self):
        """Cofa ostatnią zatwierdzoną wartość."""
        if self.controller:
            self.controller.undo_last_value()
            self._update_value_history()
            self.app.log("[Assoc] Cofnięto ostatnią wartość referencyjną.")

    def _update_value_history(self):
        """Odświeża etykietę historii wartości."""
        if self.controller:
            vals = self.controller.get_value_history()
            if vals:
                self.history_var.set(" → ".join(str(v) for v in vals[-5:]))
            else:
                self.history_var.set("(pusta)")


    def search_sequence(self):
        """Uruchamia wyszukiwanie sekwencji na podstawie najlepszego kandydata."""
        if not self.controller or not self.controller.running:
            messagebox.showwarning("Uwaga", "Najpierw rozpocznij uczenie.")
            return
        best = self.controller.get_best_candidate()
        if not best:
            messagebox.showinfo("Brak", "Nie znaleziono jeszcze głównego kandydata do sekwencji.")
            return
        sequences = self.controller.find_sequences(best, tolerance_ms=self.tolerance_var.get())
        if sequences:
            self._update_candidates_table_with_sequences(sequences)
            self.app.log(f"[Assoc] Znaleziono {len(sequences)} sekwencję(e).")
        else:
            self.app.log("[Assoc] Nie znaleziono żadnej powtarzalnej sekwencji.")

    def _update_candidates_table_with_sequences(self, sequences):
        """Wypełnia tabelę sekwencjami (zastępuje bieżącą zawartość)."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        for seq in sequences:
            main_id = seq.get("main_id", "")
            main_byte = seq.get("main_byte", "")
            seq_str = " -> ".join(seq.get("ids_order", []))
            self.tree.insert("", "end", values=(
                f"0x{main_id:X}" if isinstance(main_id, int) else str(main_id),
                main_byte,
                "sekw.",
                "-",
                f"{seq.get('confidence', 0):.1f}",
                "sekwencja",
                seq_str
            ))


    def export_csv(self):
        """Eksportuje wyniki do CSV."""
        if not self.controller or not self.controller.candidates:
            messagebox.showwarning("Brak danych", "Brak wyników do eksportu.")
            return
        from tkinter import filedialog
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not filepath:
            return
        try:
            self.controller.export_to_csv(filepath)
            self.app.log(f"[Assoc] Wyniki wyeksportowane do CSV: {filepath}")
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def export_html(self):
        """Eksportuje wyniki do HTML."""
        if not self.controller or not self.controller.candidates:
            messagebox.showwarning("Brak danych", "Brak wyników do eksportu.")
            return
        from tkinter import filedialog
        filepath = filedialog.asksaveasfilename(defaultextension=".html", filetypes=[("HTML", "*.html")])
        if not filepath:
            return
        try:
            self.controller.export_to_html(filepath)
            self.app.log(f"[Assoc] Wyniki wyeksportowane do HTML: {filepath}")
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

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
