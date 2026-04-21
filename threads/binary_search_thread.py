import time
import threading
import json
import os
import logging
import numpy as np
from datetime import datetime

# Importy ML – próbujemy sekwencyjnego, w razie braku przełączamy na stary
try:
    from ml.feature_extractor import extract_sequential_features
    from ml.sequential_model import SequentialMLModel
    SEQUENTIAL_AVAILABLE = True
except ImportError:
    SEQUENTIAL_AVAILABLE = False

# Stary model zawsze dostępny jako fallback
from ml.feature_extractor import extract_features
from ml.model import MLModel

from session_manager import SessionManager

logger = logging.getLogger("BinarySearchThread")


class BinarySearchThread(threading.Thread):
    def __init__(self, can_if, log_callback, ask_callback, done_callback, state_update_callback=None):
        super().__init__(daemon=True)
        self.can = can_if
        self.log_cb = log_callback
        self.ask = ask_callback
        self.done = done_callback
        self.state_update = state_update_callback
        self.running = False
        self.frames = []
        self.interval = 0.5
        self.use_timestamps = False
        self.left = 0
        self.right = 0
        self.mid = 0
        self.mode = 'find_start'
        self.num_parts = 2
        self.history_file = "binary_search_history.json"
        self.history = []
        self.waiting_for_answer = threading.Event()

        # Wybór modelu: preferujemy sekwencyjny, jeśli dostępny
        if SEQUENTIAL_AVAILABLE:
            try:
                self.ml_model = SequentialMLModel()
                self.use_sequential = True
                logger.info("Używam modelu sekwencyjnego (LSTM)")
            except Exception as e:
                logger.warning(f"Nie można załadować modelu LSTM: {e}. Używam regresji logistycznej.")
                self.ml_model = MLModel()
                self.use_sequential = False
        else:
            self.ml_model = MLModel()
            self.use_sequential = False
            logger.info("Używam modelu regresji logistycznej (scikit-learn)")

        self.last_played_features = None

    def log(self, msg):
        logger.info(msg)
        if self.log_cb:
            self.log_cb(msg)

    def setup(self, frames, interval, mode='find_start', num_parts=2, left=None, right=None, use_timestamps=False):
        self.frames = frames
        self.interval = interval
        self.mode = mode
        self.num_parts = num_parts
        self.use_timestamps = use_timestamps
        self.left = left if left is not None else 0
        self.right = right if right is not None else len(frames) - 1
        self.running = True
        self._save_state("start")

    def _save_state(self, action="step"):
        state = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "mode": self.mode,
            "left": self.left,
            "right": self.right,
            "mid": self.mid,
            "total_frames": len(self.frames),
            "num_parts": self.num_parts if self.mode == 'manual_parts' else None
        }
        self.history.append(state)
        self._write_history()
        if self.state_update:
            self.state_update()

    def _write_history(self):
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            self.log(f"Błąd zapisu historii: {e}")

    def undo(self):
        if len(self.history) > 1:
            self.history.pop()
            prev = self.history[-1]
            self.left = prev['left']
            self.right = prev['right']
            self.mode = prev['mode']
            self.num_parts = prev.get('num_parts', 2)
            self._write_history()
            self.log(f"Cofnięto do: left={self.left}, right={self.right}")
            return True
        return False

    def run(self):
        if self.mode in ('find_start', 'find_end'):
            self._run_binary()
        elif self.mode == 'manual_parts':
            self._run_manual_parts()
        self.running = False
        self.done()
        self.log("Wyszukiwanie zakończone.")

    def _smart_split_point(self):
        """
        Analizuje zakres [left, right] i zwraca sugerowany indeks podziału (mid).
        Uwzględnia gęstość ramek, zmienność danych oraz predykcję modelu ML.
        """
        total = self.right - self.left + 1
        if total < 10:
            return (self.left + self.right) // 2

        # Pobieramy cechy z modelu ML (jeśli dostępny)
        if self.ml_model is not None and hasattr(self.ml_model, 'predict_proba'):
            try:
                feats = self._extract_features_for_range(self.left, self.right)
                if feats is not None:
                    prob = self.ml_model.predict_proba(feats)
                    # Jeśli model jest pewny, że granica jest blisko, zawężamy przeszukiwanie
                    if prob > 0.7:
                        # Przeszukujemy węższy zakres wokół środka
                        offset = int(total * 0.15)
                        return min(self.right, max(self.left, (self.left + self.right) // 2 + np.random.randint(-offset, offset)))
            except Exception:
                pass

        # Analiza gęstości ramek (odstępy czasowe)
        if self.use_timestamps:
            timestamps = [self.frames[i][3] for i in range(self.left, self.right + 1) if self.frames[i][3] is not None]
            if len(timestamps) > 2:
                diffs = np.diff(timestamps)
                avg_diff = np.mean(diffs)
                # Szukamy miejsc, gdzie odstęp jest znacznie większy niż średnia – naturalna granica
                for i in range(1, len(diffs)):
                    if diffs[i] > 2.0 * avg_diff:
                        candidate = self.left + i
                        if self.left < candidate < self.right:
                            return candidate

        # Analiza zmienności danych – szukamy "skoku" w zawartości ramek
        data_variability = []
        for i in range(self.left, self.right):
            curr_data = self.frames[i][1]
            next_data = self.frames[i+1][1]
            # Prosta miara: liczba różnych bajtów
            diff = sum(a != b for a, b in zip(curr_data, next_data))
            data_variability.append(diff)
        if data_variability:
            max_idx = np.argmax(data_variability) + self.left
            if self.left < max_idx < self.right:
                return max_idx

        # Domyślnie: podział na pół
        return (self.left + self.right) // 2

    def _run_binary(self):
        while self.running and self.left <= self.right:
            # Użyj inteligentnego podziału zamiast sztywnego //2
            self.mid = self._smart_split_point()
            if self.mode == 'find_start':
                start, end = self.left, self.mid - 1
            else:
                start, end = self.mid, self.right

            if start > end:
                self._save_state("empty_range")
                break

            self.log(f"=== Odtwarzanie zakresu [{start} .. {end}] (mid={self.mid}) ===")
            self._play_range(start, end)
            if not self.running:
                break

            self.waiting_for_answer.clear()
            response = self.ask()
            self.waiting_for_answer.set()
            if response is None:
                break

            if self.last_played_features is not None:
                self.ml_model.add_sample(self.last_played_features, 1 if response else 0)

            if self.mode == 'find_start':
                if response:
                    self.right = self.mid - 1
                else:
                    self.left = self.mid
            else:
                if response:
                    self.left = self.mid + 1
                else:
                    self.right = self.mid

            self._save_state("after_answer")

            if self.left == self.right:
                cid, data, is_ext, _ = self.frames[self.left]
                self.log(f">>> Znaleziono ramkę: ID=0x{cid:08X} Data={data.hex().upper()} (indeks {self.left}) <<<")
                self.ml_model.train()
                break

    def _run_manual_parts(self):
        while self.running and self.left <= self.right:
            total = self.right - self.left + 1
            part_size = max(1, total // self.num_parts)
            parts = []
            for i in range(self.num_parts):
                s = self.left + i * part_size
                e = self.right if i == self.num_parts - 1 else s + part_size - 1
                parts.append((s, e))

            part_probs = []
            for s, e in parts:
                feats = self._extract_features_for_range(s, e)
                prob = self.ml_model.predict_proba(feats) if feats is not None else 0.5
                part_probs.append((s, e, prob))

            parts_sorted = sorted(part_probs, key=lambda x: x[2], reverse=(self.mode == 'find_start'))

            part_results = []
            for s, e, prob in parts_sorted:
                if not self.running:
                    break
                self.log(f"=== Odtwarzanie części [{s}..{e}] (p={prob:.3f}) ===")
                self._play_range(s, e)
                if not self.running:
                    break
                self.waiting_for_answer.clear()
                resp = self.ask(f"Czy zjawisko w [{s}-{e}]?")
                self.waiting_for_answer.set()
                if resp is None:
                    return
                part_results.append((s, e, resp))
                feats = self._extract_features_for_range(s, e)
                if feats is not None:
                    self.ml_model.add_sample(feats, 1 if resp else 0)

            target = [p for p in part_results if p[2] == (self.mode == 'find_start')]
            if not target:
                break
            if len(target) == 1:
                self.left, self.right = target[0][0], target[0][1]
            else:
                choices = [f"[{p[0]}-{p[1]}]" for p in target]
                choice = self.ask("Wybierz część:", input_type='choice', choices=choices)
                if choice is None:
                    break
                self.left, self.right = target[choice][0], target[choice][1]

            self.log(f"Nowy zakres: [{self.left} .. {self.right}]")
            self._save_state("after_manual_choice")
            if self.left == self.right:
                cid, data, is_ext, _ = self.frames[self.left]
                self.log(f">>> Znaleziono ramkę: ID=0x{cid:08X} Data={data.hex().upper()} (indeks {self.left}) <<<")
                self.ml_model.train()
                break

            change = self.ask("Zmienić liczbę części?", input_type='yesno')
            if change:
                new = self.ask("Nowa liczba części:", input_type='integer', default=self.num_parts)
                if new:
                    self.num_parts = new

    def _extract_features_for_range(self, start, end):
        """Wybiera odpowiednią ekstrakcję cech w zależności od używanego modelu."""
        if start > end:
            return None
        frames_slice = self.frames[start:end + 1]
        if self.use_sequential:
            return extract_sequential_features(frames_slice)
        else:
            return extract_features(frames_slice)

    def _play_range(self, start, end):
        # Ekstrakcja cech dla całego odtwarzanego przedziału
        if start <= end:
            self.last_played_features = self._extract_features_for_range(start, end)
        else:
            self.last_played_features = None

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

            success, msg = self.can.send_frame(cid, data, is_ext)
            self.log(msg)

    def stop(self):
        self.running = False
        self.waiting_for_answer.set()

    # ---------- Eksport sesji ----------
    def export_session(self, settings, source_file, result=None):
        return SessionManager.export_session(
            self, 'binary', settings, source_file, len(self.frames), result
        )
