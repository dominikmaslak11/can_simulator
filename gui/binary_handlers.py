import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
from datetime import datetime
from threads import BinarySearchThread
from sequence_analyzer import SequenceAnalyzer


class BinaryHandlers:
    def start_binary_search(self):
        if not self.binary_frames:
            messagebox.showerror("Błąd", "Najpierw wczytaj plik")
            return
        if not self.can.connected:
            messagebox.showerror("Błąd", "Połącz się z CAN")
            return

        mode = self.binary_mode.get()
        if mode == 'hunt_deactivator':
            self._start_hunting()
            return
        elif mode == 'rl_hunt':
            self._start_rl_hunting()
            return

        self.binary_start_btn.config(state='disabled')
        self.binary_yes_btn.config(state='normal')
        self.binary_no_btn.config(state='normal')
        self.binary_stop_btn.config(state='normal')
        self.binary_undo_btn.config(state='normal')

        num_parts = self.binary_parts.get() if mode == 'manual_parts' else 2
        self.binary_answer = None
        self.binary_answer_event = threading.Event()

        def ask_callback(prompt="Czy zjawisko wystąpiło?", input_type='yesno', choices=None, default=None):
            self.binary_answer_event.clear()
            self.log(f"[Binary] {prompt}")
            if input_type == 'yesno':
                self.binary_answer_event.wait()
                return self.binary_answer
            elif input_type == 'choice':
                choice = simpledialog.askinteger("Wybór", prompt, minvalue=1, maxvalue=len(choices))
                self.binary_answer_event.set()
                return choice - 1 if choice is not None else None
            elif input_type == 'integer':
                val = simpledialog.askinteger("Liczba części", prompt, initialvalue=default)
                self.binary_answer_event.set()
                return val
            else:
                self.binary_answer_event.wait()
                return self.binary_answer

        self.binary_thread = BinarySearchThread(
            self.can, self.log, ask_callback, self._binary_done, self._update_binary_progress
        )
        self.binary_thread.setup(self.binary_frames, self.binary_interval.get(), mode, num_parts)
        self.binary_thread.start()
        self._update_binary_progress()

    def _start_hunting(self):
        try:
            alert_id = int(self.hunt_alert_id.get().strip(), 16)
        except ValueError:
            messagebox.showerror("Błąd", "Nieprawidłowy format ID alertu")
            return

        period = self.hunt_period.get()
        tolerance = self.hunt_tolerance.get()
        interval = self.binary_interval.get()
        start_idx = self.hunt_start_index.get()

        self.binary_start_btn.config(state='disabled')
        self.binary_stop_btn.config(state='normal')
        self.binary_yes_btn.config(state='disabled')
        self.binary_no_btn.config(state='disabled')
        self.binary_undo_btn.config(state='disabled')

        self.binary_thread = BinarySearchThread(
            self.can, self.log, None, self._hunting_done, self._update_hunting_status
        )
        self.binary_thread.setup_hunting(self.binary_frames, interval, alert_id, period, tolerance, start_idx)
        self.binary_thread.deactivation_callback = self._on_deactivation
        self.binary_thread.start()
        self.binary_progress.config(text="Tryb polowania aktywny...")
        self.log("[Polowanie] Rozpoczęto.")

    def _start_rl_hunting(self):
        try:
            alert_id = int(self.hunt_alert_id.get().strip(), 16)
        except ValueError:
            messagebox.showerror("Błąd", "Nieprawidłowy format ID alertu")
            return

        period = self.hunt_period.get()
        tolerance = self.hunt_tolerance.get()
        interval = self.binary_interval.get()
        start_idx = self.hunt_start_index.get()

        self.binary_start_btn.config(state='disabled')
        self.binary_stop_btn.config(state='normal')
        self.binary_yes_btn.config(state='disabled')
        self.binary_no_btn.config(state='disabled')
        self.binary_undo_btn.config(state='disabled')

        self.binary_thread = BinarySearchThread(
            self.can, self.log, None, self._hunting_done, self._update_hunting_status
        )
        self.binary_thread.setup_rl_hunting(self.binary_frames, interval, alert_id, period, tolerance, start_idx)
        self.binary_thread.deactivation_callback = self._on_deactivation
        self.binary_thread.start()
        self.binary_progress.config(text="Tryb RL-polowania aktywny...")
        self.log("[RL-Polowanie] Rozpoczęto.")

    def _on_deactivation(self, candidates):
        self.log(f"[Polowanie] Wykryto dezaktywację! Znaleziono {len(candidates)} kandydatów.")

        if hasattr(self, 'seq_analyzer'):
            self.seq_analyzer.add_candidates(candidates)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"candidates_{timestamp}.txt"
        with open(filename, 'w') as f:
            for cid, data, is_ext, ts in candidates:
                f.write(f"({ts:.6f}) can0 {cid:08X}#{data.hex().upper()}\n")
        self.log(f"Kandydaci zapisani do {filename}")

        win = tk.Toplevel(self.root)
        win.title("Kandydaci - ramki przed dezaktywacją")
        text = tk.scrolledtext.ScrolledText(win, width=100, height=20)
        text.pack(fill=tk.BOTH, expand=True)
        text.insert(tk.END, f"Znaleziono {len(candidates)} ramek:\n\n")
        for i, (cid, data, is_ext, ts) in enumerate(candidates):
            text.insert(tk.END, f"{i+1:4d}. ID=0x{cid:08X}  Data={data.hex().upper()}  {'EXT' if is_ext else 'STD'}  ts={ts:.6f}\n")
        text.config(state='disabled')

        btn_frame = ttk.Frame(win)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Przekaż do wyszukiwania binarnego",
                   command=lambda: self._load_candidates_to_binary(candidates)).pack(side=tk.LEFT, padx=5)
        if hasattr(self, 'seq_analyzer'):
            ttk.Button(btn_frame, text="Analizuj sekwencje",
                       command=lambda: self._show_sequence_analysis()).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="Znajdź wzorzec (LCS)",
                       command=lambda: self._show_lcs_pattern()).pack(side=tk.LEFT, padx=5)
        if candidates:
            first = candidates[0]
            ttk.Button(btn_frame, text="Użyj w symulacji",
                       command=lambda: self._use_in_simulation(first)).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="Testuj alert (10s)",
                       command=lambda: self._quick_test(first[0], first[1], first[2])).pack(side=tk.LEFT, padx=5)

        self.binary_progress.config(text=f"Dezaktywacja! {len(candidates)} kandydatów.")

    def _load_candidates_to_binary(self, candidates):
        if not candidates:
            messagebox.showinfo("Brak kandydatów", "Lista kandydatów jest pusta.")
            return
        self.binary_frames = [(cid, data, is_ext) for (cid, data, is_ext, ts) in candidates]
        self.binary_info.config(text=f"Wczytano {len(self.binary_frames)} kandydatów")
        self.binary_start_btn.config(state='normal')
        self.binary_mode.set('find_start')
        self._redraw_binary_progress()
        self.log(f"[Binary] Wczytano {len(self.binary_frames)} ramek z kandydatów.")
        self.notebook.select(self.tab_binary)
        messagebox.showinfo("Gotowe", f"Wczytano {len(self.binary_frames)} ramek.\nMożesz rozpocząć wyszukiwanie binarne.")

    def _show_sequence_analysis(self):
        if not hasattr(self, 'seq_analyzer'):
            messagebox.showinfo("Brak analizatora", "Analizator sekwencji nie jest dostępny.")
            return
        top_seqs = self.seq_analyzer.get_top_sequences(5)
        if not top_seqs:
            messagebox.showinfo("Brak sekwencji", "Nie znaleziono jeszcze żadnych sekwencji.")
            return

        win = tk.Toplevel(self.root)
        win.title("Najczęstsze sekwencje")
        text = tk.scrolledtext.ScrolledText(win, width=100, height=15)
        text.pack(fill=tk.BOTH, expand=True)
        text.insert(tk.END, "Najczęściej występujące sekwencje:\n\n")
        for i, (seq, count) in enumerate(top_seqs):
            text.insert(tk.END, f"Sekwencja {i+1} (wystąpień: {count}):\n")
            for j, (cid, data, is_ext) in enumerate(seq):
                text.insert(tk.END, f"  {j+1}. ID=0x{cid:08X} Data={data.hex().upper()} {'EXT' if is_ext else 'STD'}\n")
            text.insert(tk.END, "\n")

        btn_frame = ttk.Frame(win)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Zamknij", command=win.destroy).pack()

    def _show_lcs_pattern(self):
        if not hasattr(self, 'seq_analyzer'):
            messagebox.showinfo("Brak analizatora", "Analizator sekwencji nie jest dostępny.")
            return
        pattern = self.seq_analyzer.find_pattern_across_sessions(min_support=2)
        if not pattern:
            messagebox.showinfo("Brak wzorca", "Nie znaleziono wspólnego wzorca dla co najmniej 2 sesji.")
            return

        win = tk.Toplevel(self.root)
        win.title("Wzorzec LCS")
        text = tk.scrolledtext.ScrolledText(win, width=100, height=10)
        text.pack(fill=tk.BOTH, expand=True)
        text.insert(tk.END, "Wspólny wzorzec (LCS) dla wszystkich sesji:\n\n")
        for i, (cid, data, is_ext) in enumerate(pattern):
            text.insert(tk.END, f"{i+1:4d}. ID=0x{cid:08X} Data={data.hex().upper()} {'EXT' if is_ext else 'STD'}\n")
        text.config(state='disabled')

        btn_frame = ttk.Frame(win)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Przekaż do wyszukiwania binarnego",
                   command=lambda: self._load_pattern_to_binary(pattern)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Użyj wzorca w symulacji",
                   command=lambda: self._use_pattern_in_simulation(pattern)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Testuj wzorzec (10s)",
                   command=lambda: self._quick_test_pattern(pattern)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Zamknij", command=win.destroy).pack()

    def _load_pattern_to_binary(self, pattern):
        if not pattern:
            return
        self.binary_frames = pattern
        self.binary_info.config(text=f"Wczytano wzorzec ({len(pattern)} ramek)")
        self.binary_start_btn.config(state='normal')
        self.binary_mode.set('find_start')
        self._redraw_binary_progress()
        self.log(f"[Binary] Wczytano wzorzec LCS ({len(pattern)} ramek).")
        self.notebook.select(self.tab_binary)
        messagebox.showinfo("Gotowe", "Wzorzec został przekazany do wyszukiwania.")

    def _use_in_simulation(self, frame_tuple):
        cid, data, is_ext, _ = frame_tuple
        self._switch_to_simulation_tab(cid, data, is_ext)

    def _use_pattern_in_simulation(self, pattern):
        if pattern:
            cid, data, is_ext = pattern[0]
            self._switch_to_simulation_tab(cid, data, is_ext)

    def _switch_to_simulation_tab(self, can_id, data, is_extended):
        if hasattr(self, 'use_in_simulation'):
            self.use_in_simulation(can_id, data, is_extended)
        else:
            # fallback
            self.manual_id.set(f"{can_id:08X}")
            self.manual_data.set(data.hex().upper())
            self.manual_extended.set(is_extended)
            self.notebook.select(self.tab_manual)
            self.log(f"Przekazano ID=0x{can_id:08X} do symulacji.")

    def _quick_test(self, cid, data, is_ext, period=1.0):
        if hasattr(self, 'quick_test_alert'):
            self.quick_test_alert(cid, data, is_ext, period=period, duration=10.0)
        else:
            messagebox.showerror("Błąd", "Metoda quick_test_alert nie jest dostępna.")

    def _quick_test_pattern(self, pattern):
        if not pattern:
            return
        cid, data, is_ext = pattern[0]
        self._quick_test(cid, data, is_ext)

    def _show_result_with_simulation_button(self, cid, data, is_ext):
        win = tk.Toplevel(self.root)
        win.title("Wynik wyszukiwania")
        tk.Label(win, text=f"Znaleziono ramkę:\nID=0x{cid:08X}\nData={data.hex().upper()}\n{'EXT' if is_ext else 'STD'}",
                 font=('Arial', 12)).pack(padx=20, pady=20)
        btn_frame = ttk.Frame(win)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Użyj w symulacji",
                   command=lambda: [self._switch_to_simulation_tab(cid, data, is_ext), win.destroy()]).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Testuj alert (10s)",
                   command=lambda: [self._quick_test(cid, data, is_ext), win.destroy()]).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Zamknij", command=win.destroy).pack(side=tk.LEFT, padx=5)

    def binary_answer_yes(self):
        if self.binary_thread and self.binary_thread.is_alive():
            self.binary_answer = True
            self.binary_answer_event.set()
            self.log("[Binary] TAK")
            self._update_binary_progress()

    def binary_answer_no(self):
        if self.binary_thread and self.binary_thread.is_alive():
            self.binary_answer = False
            self.binary_answer_event.set()
            self.log("[Binary] NIE")
            self._update_binary_progress()

    def _update_binary_progress(self):
        if self.binary_thread:
            left = self.binary_thread.left
            right = self.binary_thread.right
            mid = self.binary_thread.mid
            total = len(self.binary_frames)
            self.binary_progress.config(text=f"Zakres: [{left} .. {right}]  środek: {mid}  (razem: {total})")
            self._redraw_binary_progress()

    def _redraw_binary_progress(self):
        if not hasattr(self, 'binary_canvas') or not self.binary_frames:
            return
        canvas = self.binary_canvas
        canvas.delete("all")
        total = len(self.binary_frames)
        if total == 0:
            return
        width = canvas.winfo_width()
        if width <= 10:
            width = 600

        if self.binary_thread and self.binary_thread.running:
            left = self.binary_thread.left
            right = self.binary_thread.right
            mid = self.binary_thread.mid
        else:
            left, right = 0, total - 1
            mid = (left + right) // 2

        def idx_to_x(idx):
            return int((idx / (total - 1)) * width) if total > 1 else 0

        x_left = idx_to_x(left)
        x_right = idx_to_x(right)
        x_mid = idx_to_x(mid)

        canvas.create_rectangle(0, 0, width, 30, fill='lightgray', outline='')
        canvas.create_rectangle(x_left, 0, x_right, 30, fill='lightgreen', outline='darkgreen')
        canvas.create_line(x_mid, 0, x_mid, 30, fill='red', width=2)
        canvas.create_text(x_left, 15, text=str(left), anchor='e', font=('Arial', 8))
        canvas.create_text(x_right, 15, text=str(right), anchor='w', font=('Arial', 8))
        canvas.create_text(x_mid, 0, text=str(mid), anchor='s', font=('Arial', 8, 'bold'), fill='red')

    def _binary_done(self):
        self.binary_start_btn.config(state='normal')
        for btn in [self.binary_yes_btn, self.binary_no_btn, self.binary_stop_btn, self.binary_undo_btn]:
            btn.config(state='disabled')
        self.binary_progress.config(text="Wyszukiwanie zakończone.")
        self._redraw_binary_progress()
        if self.binary_thread and hasattr(self.binary_thread, 'left') and self.binary_thread.left == self.binary_thread.right:
            idx = self.binary_thread.left
            if idx < len(self.binary_frames):
                cid, data, is_ext = self.binary_frames[idx]
                self._show_result_with_simulation_button(cid, data, is_ext)

    def stop_binary_search(self):
        if self.binary_thread:
            self.binary_thread.stop()
        self._binary_done()
        self.log("[Binary] Zatrzymano.")

    def _hunting_done(self):
        self.binary_start_btn.config(state='normal')
        self.binary_stop_btn.config(state='disabled')
        self.binary_progress.config(text="Polowanie zakończone.")

    def _update_hunting_status(self):
        pass
