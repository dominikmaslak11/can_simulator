from .base_controller import BaseController
from tkinter import messagebox
from parsers import load_frames_from_file
import numpy as np

class ErrorController(BaseController):
    def __init__(self, app):
        super().__init__(app)
        self.frames = []
        self.reference_intervals = {}

    def add_frame(self, cid, data, is_ext, delay):
        self.frames.append({'id': cid, 'data': data, 'ext': is_ext, 'delay': delay})

    def remove_frame(self, idx):
        if 0 <= idx < len(self.frames):
            del self.frames[idx]

    def update_frame(self, idx, cid, data, is_ext, delay):
        if 0 <= idx < len(self.frames):
            self.frames[idx] = {'id': cid, 'data': data, 'ext': is_ext, 'delay': delay}

    def clear_frames(self):
        self.frames.clear()

    def analyze_reference_file(self):
        """Wczytuje plik referencyjny i wyświetla średnie interwały."""
        path = self.app.error_ref_file.get()
        if not path:
            messagebox.showinfo("Brak pliku", "Wybierz plik referencyjny.")
            return
        try:
            frames = load_frames_from_file(path)
            intervals = self._compute_intervals(frames)
            self.reference_intervals = intervals
            self.log("[Error] Obliczono interwały referencyjne.")
            for cid, val in intervals.items():
                self.log(f"  ID 0x{cid:08X}: {val:.4f}s")
            messagebox.showinfo("Sukces", f"Obliczono interwały dla {len(intervals)} ID.")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się przeanalizować pliku: {e}")

    def _compute_intervals(self, frames):
        id_timestamps = {}
        for f in frames:
            cid = f[0]
            ts = f[3] if len(f) > 3 else None
            if ts is not None:
                id_timestamps.setdefault(cid, []).append(ts)
        intervals = {}
        for cid, stamps in id_timestamps.items():
            if len(stamps) > 1:
                diffs = np.diff(sorted(stamps))
                intervals[cid] = float(np.mean(diffs))
        return intervals

    def start_error(self):
        self.app._start_sim()

        # Jeśli użyto timestampów, wczytaj plik i zastąp opóźnienia
        if self.app.error_use_timestamps.get():
            path = self.app.error_ref_file.get()
            if not path:
                messagebox.showerror("Błąd", "Wybierz plik referencyjny.")
                return
            try:
                frames = load_frames_from_file(path)
                intervals = self._compute_intervals(frames)
                # Zastosuj opóźnienia dla każdej ramki w sekwencji
                for f in self.frames:
                    cid = f['id']
                    if cid in intervals:
                        f['delay'] = intervals[cid]
                self.log("[Error] Zastosowano oryginalne opóźnienia z pliku referencyjnego.")
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie udało się wczytać pliku: {e}")
                return

        interval = self.app.error_interval.get()
        self.app.sim_thread.setup_error_frames(interval, self.frames)
        self.app.sim_thread.mode = 'error'
        self.app.sim_thread.start()
        self.app._simulation_started()

    def set_from_artifact(self, can_id, data, is_ext):
        # Placeholder – można wykorzystać do ustawienia kodu błędu
        pass

    def _refresh_tree(self):
        """Odświeża widok tabeli w GUI."""
        if hasattr(self.app, 'error_tree'):
            tree = self.app.error_tree
            tree.delete(*tree.get_children())
            for f in self.frames:
                tree.insert("", tk.END, values=(
                    f"0x{f['id']:08X}", f['data'].hex().upper(),
                    "X" if f['ext'] else "", f"{f['delay']:.3f}"
                ))
