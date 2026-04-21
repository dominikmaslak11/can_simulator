import time
import threading
from datetime import datetime
from tkinter import messagebox, simpledialog
from session_manager import SessionManager


class WizardSearchThread(threading.Thread):
    def __init__(self, app, log_cb):
        super().__init__(daemon=True)
        self.app = app
        self.log_cb = log_cb
        self.running = False
        self.frames = []
        self.interval = 0.5
        self.use_timestamps = False
        self.target = None
        self.num_parts = 2
        self.left = 0
        self.right = 0
        self.history = []

    def log(self, msg):
        self.log_cb(msg)

    def setup(self, frames, interval, target, num_parts=2, use_timestamps=False):
        self.frames = frames
        self.interval = interval
        self.target = target
        self.num_parts = num_parts
        self.use_timestamps = use_timestamps
        self.left = 0
        self.right = len(frames) - 1
        self.running = True
        self._save_state("start")

    def _save_state(self, action="step"):
        state = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "left": self.left,
            "right": self.right,
            "total_frames": len(self.frames),
            "num_parts": self.num_parts
        }
        self.history.append(state)

    def run(self):
        while self.running and self.left <= self.right:
            total = self.right - self.left + 1
            part_size = max(1, total // self.num_parts)
            parts = []
            for i in range(self.num_parts):
                s = self.left + i * part_size
                e = self.right if i == self.num_parts - 1 else s + part_size - 1
                parts.append((s, e))

            found_part = None
            for idx, (s, e) in enumerate(parts):
                if not self.running:
                    return
                self.log(f"[Kreator] Odtwarzanie części {idx+1}/{len(parts)}: [{s} .. {e}]")
                self._play_range(s, e)
                if not self.running:
                    return

                self.app.wizard_answer_event.clear()
                self.app.wizard_answer_event.wait()
                answer = self.app.wizard_answer
                if answer is None:
                    self.log("[Kreator] Anulowano")
                    return

                if answer:
                    found_part = (s, e)
                    break

            if found_part is None:
                self.log("[Kreator] Nie znaleziono szukanej ramki/sekwencji w żadnej części.")
                break

            self.left, self.right = found_part
            self._save_state("after_part")
            self.app.wizard_ctrl._add_history(self.left, self.right)
            self.app._update_wizard_progress()
            self.log(f"[Kreator] Zawężono zakres do [{self.left} .. {self.right}]")

            if self.left == self.right:
                if self._matches(self.frames[self.left]):
                    self.log(f"[Kreator] Znaleziono szukaną ramkę na indeksie {self.left}")
                else:
                    self.log(f"[Kreator] Nie znaleziono dokładnego dopasowania. Zatrzymano na indeksie {self.left}")
                break

            self.app.wizard_answer_event.clear()
            change = self._ask("Czy chcesz zmienić liczbę części dla następnego kroku?", input_type='yesno')
            if change:
                new_parts = self._ask("Podaj nową liczbę części:", input_type='integer', default=self.num_parts)
                if new_parts and new_parts > 0:
                    self.num_parts = new_parts

        self.running = False
        self.app.root.after(0, self._done)
        self.log("[Kreator] Wyszukiwanie zakończone.")

    def _play_range(self, start, end):
        last_ts = None
        for i in range(start, end + 1):
            if not self.running:
                break
            cid, data, is_ext, ts = self.frames[i]
            if self.use_timestamps and ts is not None:
                if last_ts is not None and ts > last_ts:
                    time.sleep(ts - last_ts)
                last_ts = ts
            else:
                time.sleep(self.interval)
            self.app.can.send_frame(cid, data, is_ext)

    def _matches(self, frame):
        if isinstance(self.target, tuple):
            tid, tdata, tis_ext = self.target
            cid, data, is_ext, _ = frame
            if cid != tid or is_ext != tis_ext:
                return False
            if tdata is not None and data != tdata:
                return False
            return True
        else:
            seq = self.target
            idx = self.frames.index(frame)
            if idx + len(seq) > len(self.frames):
                return False
            for i, (sid, sdata, sis_ext) in enumerate(seq):
                cid, data, is_ext, _ = self.frames[idx + i]
                if cid != sid or is_ext != sis_ext:
                    return False
                if sdata and data != sdata:
                    return False
            return True

    def _ask(self, prompt, input_type='yesno', default=None):
        if input_type == 'yesno':
            return messagebox.askyesno("Pytanie", prompt)
        elif input_type == 'integer':
            return simpledialog.askinteger("Liczba", prompt, initialvalue=default)
        return None

    def _done(self):
        self.app.wizard_start_btn.config(state='normal')
        self.app.wizard_yes_btn.config(state='disabled')
        self.app.wizard_no_btn.config(state='disabled')
        self.app.wizard_stop_btn.config(state='disabled')
        self.app.wizard_undo_btn.config(state='disabled')
        if hasattr(self.app, 'wizard_export_btn'):
            self.app.wizard_export_btn.config(state='disabled')

    def stop(self):
        self.running = False
        self.app.wizard_answer_event.set()

    def export_session(self, settings, source_file, result=None):
        return SessionManager.export_session(
            self, 'wizard', settings, source_file, len(self.frames), result
        )
