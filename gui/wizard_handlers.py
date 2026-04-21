import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from parsers import load_frames_from_file
from log_profiler import LogProfiler


class WizardHandlers:
    """Mixin zawierający logikę kreatora diagnostyki."""

    def wizard_browse_file(self):
        """Krok 1: Wczytaj plik."""
        path = filedialog.askopenfilename(
            filetypes=[("Logi CAN", "*.txt *.log"), ("Wszystkie pliki", "*.*")]
        )
        if not path:
            return
        try:
            self.wizard_loaded_frames = load_frames_from_file(path)
            self.wizard_file_label.config(text=f"Wczytano: {path} ({len(self.wizard_loaded_frames)} ramek)")
            self.log(f"[Kreator] Wczytano {len(self.wizard_loaded_frames)} ramek z {path}")
            # Odśwież listę ID
            self.wizard_refresh_id_list()
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się wczytać pliku: {e}")

    def wizard_refresh_id_list(self):
        """Krok 2: Odświeża listę najczęstszych ID z checkboxami."""
        if not hasattr(self, 'wizard_loaded_frames') or not self.wizard_loaded_frames:
            messagebox.showinfo("Brak danych", "Najpierw wczytaj plik.")
            return
        profiler = LogProfiler(self.wizard_loaded_frames)
        top_ids = profiler.get_top_ids(15)

        # Wyczyść poprzednią zawartość
        for widget in self.wizard_id_frame.winfo_children():
            widget.destroy()

        self.wizard_id_vars = {}
        for i, (cid, count) in enumerate(top_ids):
            ext_str = "EXT" if cid > 0x7FF else "STD"
            var = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(
                self.wizard_id_frame,
                text=f"0x{cid:08X} ({ext_str}) – {count} razy",
                variable=var
            )
            cb.grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            self.wizard_id_vars[cid] = var

        self.log("[Kreator] Odświeżono listę ID.")

    def wizard_skip_alert_selection(self):
        """Odznacza wszystkie checkboxy."""
        if hasattr(self, 'wizard_id_vars'):
            for var in self.wizard_id_vars.values():
                var.set(False)
        self.log("[Kreator] Odznaczono wszystkie alerty.")

    def wizard_start_find_alert(self):
        """Krok 3: Uruchamia wyszukiwanie binarne dla wybranego alertu (lub wielu)."""
        if not hasattr(self, 'wizard_loaded_frames') or not self.wizard_loaded_frames:
            messagebox.showerror("Błąd", "Najpierw wczytaj plik.")
            return
        if not self.can or not self.can.connected:
            messagebox.showerror("Błąd", "Połącz się z CAN przed wyszukiwaniem.")
            return

        # Pobierz zaznaczone ID
        selected_ids = [cid for cid, var in self.wizard_id_vars.items() if var.get()]
        if not selected_ids:
            # Jeśli nic nie zaznaczono, zapytaj o ręczne wpisanie
            from tkinter import simpledialog
            id_input = simpledialog.askstring("ID alertu", "Podaj identyfikator alertu (hex):")
            if not id_input:
                return
            try:
                alert_id = int(id_input.strip(), 16)
                selected_ids = [alert_id]
            except ValueError:
                messagebox.showerror("Błąd", "Nieprawidłowy format ID.")
                return

        if len(selected_ids) == 1:
            # Jeden alert – standardowe wyszukiwanie
            self._start_single_alert_search(selected_ids[0])
        else:
            # Wiele alertów – analiza sekwencyjna
            self._analyze_multiple_alerts(selected_ids)

    def _start_single_alert_search(self, alert_id):
        """Uruchamia wyszukiwanie binarne dla pojedynczego alertu."""
        self.binary_frames = self.wizard_loaded_frames.copy()
        self.binary_info.config(text=f"Wczytano {len(self.binary_frames)} ramek (z kreatora)")
        self.binary_start_btn.config(state='normal')
        self.binary_mode.set('find_start')
        self._redraw_binary_progress()
        self.start_binary_search()
        self._wizard_awaiting_alert_result = True
        self.log(f"[Kreator] Rozpoczęto wyszukiwanie alertu ID=0x{alert_id:08X}")

    def _analyze_multiple_alerts(self, alert_ids):
        """Uruchamia wyszukiwanie dla wielu alertów i zapisuje wyniki."""
        if not self.wizard_loaded_frames:
            return

        self.log(f"[Kreator] Rozpoczynanie analizy {len(alert_ids)} alertów...")
        results = []

        # Wyłącz GUI podczas analizy
        self.wizard_file_label.config(text="Analiza wielu alertów w toku...")
        self.root.update()

        for alert_id in alert_ids:
            from threads.binary_search_thread import BinarySearchThread
            from dummy_interface import DummyInterface

            can = DummyInterface()
            can.connect()

            done_event = threading.Event()
            log = []

            def log_cb(msg):
                log.append(msg)

            ask_counter = 0

            def ask_cb(prompt="", **kwargs):
                nonlocal ask_counter
                ask_counter += 1
                # Prosta heurystyka: pierwsze dwa pytania TAK, potem NIE
                return ask_counter <= 2

            def done_cb():
                done_event.set()

            thread = BinarySearchThread(can, log_cb, ask_cb, done_cb)
            thread.setup(self.wizard_loaded_frames, interval=0.01, mode='find_start')
            thread.start()
            done_event.wait(timeout=10.0)

            if thread.left == thread.right:
                idx = thread.left
                cid, data, is_ext = self.wizard_loaded_frames[idx]
                results.append((alert_id, cid, data.hex().upper(), idx))
                self.log(f"[Kreator] Alert 0x{alert_id:08X} -> znaleziono ramkę ID=0x{cid:08X} na pozycji {idx}")
            else:
                results.append((alert_id, None, None, None))
                self.log(f"[Kreator] Alert 0x{alert_id:08X} -> nie znaleziono")

            can.disconnect()

        self._show_multiple_results(results)
        self.wizard_file_label.config(text=f"Analiza zakończona. Przetworzono {len(alert_ids)} alertów.")

    def _show_multiple_results(self, results):
        win = tk.Toplevel(self.root)
        win.title("Wyniki analizy wielu alertów")
        text = tk.scrolledtext.ScrolledText(win, width=100, height=20)
        text.pack(fill=tk.BOTH, expand=True)
        text.insert(tk.END, "Wyniki wyszukiwania dla wybranych alertów:\n\n")
        for alert_id, found_id, data, idx in results:
            if found_id:
                text.insert(tk.END, f"Alert 0x{alert_id:08X}: znaleziono ramkę ID=0x{found_id:08X}, dane={data}, indeks={idx}\n")
            else:
                text.insert(tk.END, f"Alert 0x{alert_id:08X}: nie znaleziono\n")
        text.config(state='disabled')

        btn_frame = ttk.Frame(win)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Eksportuj do CSV", command=lambda: self._export_results_csv(results)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Zamknij", command=win.destroy).pack(side=tk.LEFT, padx=5)

    def _export_results_csv(self, results):
        from export_utils import export_frames_to_csv
        frames = []
        for alert_id, found_id, data, idx in results:
            if found_id:
                frames.append((found_id, bytes.fromhex(data), found_id > 0x7FF))
        if frames:
            filename = export_frames_to_csv(frames)
            self.log(f"Wyeksportowano wyniki do {filename}")
            messagebox.showinfo("Eksport CSV", f"Zapisano do pliku:\n{filename}")
        else:
            messagebox.showinfo("Brak danych", "Brak ramek do eksportu.")

    def wizard_on_alert_found(self, cid, data, is_ext):
        """Wywoływane, gdy wyszukiwanie binarne znajdzie ramkę alertu."""
        self.wizard_alert_result_label.config(
            text=f"Znaleziono: ID=0x{cid:08X}, dane={data.hex().upper()}, {'EXT' if is_ext else 'STD'}"
        )
        self.wizard_found_alert = (cid, data, is_ext)
        self.log(f"[Kreator] Znaleziono alert: ID=0x{cid:08X}")

    def wizard_test_alert(self):
        """Testuje znaleziony alert (10s)."""
        if not hasattr(self, 'wizard_found_alert'):
            messagebox.showinfo("Brak alertu", "Najpierw znajdź alert.")
            return
        cid, data, is_ext = self.wizard_found_alert
        self.quick_test_alert(cid, data, is_ext, period=1.0, duration=10.0)

    def wizard_start_hunt_deactivator(self):
        """Krok 4: Uruchamia polowanie na dezaktywator."""
        if not hasattr(self, 'wizard_found_alert'):
            messagebox.showinfo("Brak alertu", "Najpierw znajdź alert.")
            return
        if not self.can or not self.can.connected:
            messagebox.showerror("Błąd", "Połącz się z CAN przed polowaniem.")
            return

        alert_id, _, _ = self.wizard_found_alert
        self.hunt_alert_id.set(f"{alert_id:08X}")
        self.hunt_period.set(1.0)
        self.hunt_tolerance.set(0.2)
        self.hunt_start_index.set(0)

        self.binary_frames = self.wizard_loaded_frames.copy()
        self.binary_mode.set('hunt_deactivator')
        self.binary_start_btn.config(state='normal')

        self._start_hunting()
        self._wizard_awaiting_deact_result = True
        self.log("[Kreator] Rozpoczęto polowanie na dezaktywator.")

    def wizard_on_deactivator_found(self, candidates):
        """Wywoływane po znalezieniu dezaktywatora (pierwsza ramka z kandydatów)."""
        if candidates:
            cid, data, is_ext, ts = candidates[0]
            self.wizard_deact_result_label.config(
                text=f"Znaleziono: ID=0x{cid:08X}, dane={data.hex().upper()}, {'EXT' if is_ext else 'STD'}"
            )
            self.wizard_found_deactivator = (cid, data, is_ext)
            self.log(f"[Kreator] Znaleziono dezaktywator: ID=0x{cid:08X}")
        else:
            self.wizard_deact_result_label.config(text="Nie znaleziono dezaktywatora.")
            self.log("[Kreator] Nie znaleziono dezaktywatora.")

    def wizard_test_deactivator(self):
        """Testuje znaleziony dezaktywator (10s)."""
        if not hasattr(self, 'wizard_found_deactivator'):
            messagebox.showinfo("Brak dezaktywatora", "Najpierw znajdź dezaktywator.")
            return
        cid, data, is_ext = self.wizard_found_deactivator
        self.quick_test_alert(cid, data, is_ext, period=1.0, duration=10.0)
