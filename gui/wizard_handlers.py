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
        """Krok 2: Odświeża listę najczęstszych ID."""
        if not hasattr(self, 'wizard_loaded_frames') or not self.wizard_loaded_frames:
            messagebox.showinfo("Brak danych", "Najpierw wczytaj plik.")
            return
        profiler = LogProfiler(self.wizard_loaded_frames)
        top_ids = profiler.get_top_ids(15)
        self.wizard_id_listbox.delete(0, tk.END)
        for cid, count in top_ids:
            ext_str = "EXT" if cid > 0x7FF else "STD"
            self.wizard_id_listbox.insert(tk.END, f"0x{cid:08X} ({ext_str}) – {count} razy")
        self.log("[Kreator] Odświeżono listę ID.")

    def wizard_skip_alert_selection(self):
        """Pomija wybór alertu – użytkownik sam wpisze ID później."""
        self.wizard_id_listbox.selection_clear(0, tk.END)
        self.log("[Kreator] Pominięto wybór alertu.")

    def wizard_start_find_alert(self):
        """Krok 3: Uruchamia wyszukiwanie binarne początku alertu."""
        if not hasattr(self, 'wizard_loaded_frames') or not self.wizard_loaded_frames:
            messagebox.showerror("Błąd", "Najpierw wczytaj plik.")
            return
        if not self.can or not self.can.connected:
            messagebox.showerror("Błąd", "Połącz się z CAN przed wyszukiwaniem.")
            return

        # Sprawdź, czy użytkownik wybrał ID z listy
        selection = self.wizard_id_listbox.curselection()
        if selection:
            line = self.wizard_id_listbox.get(selection[0])
            # Parsuj ID z napisu "0x0C00008F (EXT) – 123 razy"
            id_str = line.split()[0]
            alert_id = int(id_str, 16)
        else:
            # Jeśli nie wybrano, zapytaj o ręczne wpisanie
            from tkinter import simpledialog
            id_input = simpledialog.askstring("ID alertu", "Podaj identyfikator alertu (hex):")
            if not id_input:
                return
            try:
                alert_id = int(id_input.strip(), 16)
            except ValueError:
                messagebox.showerror("Błąd", "Nieprawidłowy format ID.")
                return

        # Przekaż ramki do głównego wyszukiwania binarnego
        self.binary_frames = self.wizard_loaded_frames.copy()
        self.binary_info.config(text=f"Wczytano {len(self.binary_frames)} ramek (z kreatora)")
        self.binary_start_btn.config(state='normal')
        self.binary_mode.set('find_start')
        self._redraw_binary_progress()

        # Uruchom wyszukiwanie
        self.start_binary_search()

        # Po zakończeniu wyszukiwania (callback _binary_done) wywołamy metodę, która zaktualizuje etykietę w kreatorze
        self._wizard_awaiting_alert_result = True
        self.log(f"[Kreator] Rozpoczęto wyszukiwanie alertu ID=0x{alert_id:08X}")

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

        # Ustaw parametry polowania na podstawie znalezionego alertu
        alert_id, _, _ = self.wizard_found_alert
        self.hunt_alert_id.set(f"{alert_id:08X}")
        self.hunt_period.set(1.0)      # domyślnie 1s – można by pobrać z detektora
        self.hunt_tolerance.set(0.2)
        self.hunt_start_index.set(0)

        self.binary_frames = self.wizard_loaded_frames.copy()
        self.binary_mode.set('hunt_deactivator')
        self.binary_start_btn.config(state='normal')

        self._start_hunting()   # wywołanie istniejącej metody z BinaryHandlers

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
