import time
import threading
import json
import os
import logging
import numpy as np
from datetime import datetime
from ml.feature_extractor import extract_features
from ml.model import MLModel
from cyclic_detector import CyclicDetector

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
        self.left = 0
        self.right = 0
        self.mid = 0
        self.mode = 'find_start'
        self.num_parts = 2
        self.history_file = "binary_search_history.json"
        self.history = []
        self.waiting_for_answer = threading.Event()
        self.ml_model = MLModel()
        self.last_played_features = None

        # Pola dla trybu polowania
        self.alert_id = None
        self.alert_period = 1.0
        self.alert_tolerance = 0.2
        self.detector = None
        self.hunt_paused = False
        self.deactivation_callback = None
        self.start_index = 0
        self.playback_thread = None
        self.listen_thread = None

        # Pola dla RL
        self.rl_agent = None
        self.rl_total_frames = 0
        self.rl_episode_frames_played = 0

    def log(self, msg):
        logger.info(msg)
        if self.log_cb:
            self.log_cb(msg)

    def setup(self, frames, interval, mode='find_start', num_parts=2, left=None, right=None):
        self.frames = frames
        self.interval = interval
        self.mode = mode
        self.num_parts = num_parts
        self.left = left if left is not None else 0
        self.right = right if right is not None else len(frames) - 1
        self.running = True
        self._save_state("start")

    def setup_hunting(self, frames, interval, alert_id, period=1.0, tolerance=0.2, start_index=0):
        self.frames = frames
        self.interval = interval
        self.mode = 'hunt_deactivator'
        self.alert_id = alert_id
        self.alert_period = period
        self.alert_tolerance = tolerance
        self.start_index = max(0, min(start_index, len(frames) - 1))
        self.left = self.start_index
        self.right = len(frames) - 1
        self.running = True
        self.detector = CyclicDetector(alert_id, period, tolerance)
        self.log(f"Tryb polowania: ID=0x{alert_id:08X}, okres={period}s, tolerancja={tolerance}, start_idx={self.start_index}")

    def setup_rl_hunting(self, frames, interval, alert_id, period=1.0, tolerance=0.2, start_index=0):
        self.frames = frames
        self.interval = interval
        self.mode = 'rl_hunt'
        self.alert_id = alert_id
        self.alert_period = period
        self.alert_tolerance = tolerance
        self.start_index = max(0, min(start_index, len(frames) - 1))
        self.left = self.start_index
        self.right = len(frames) - 1
        self.rl_total_frames = len(frames)
        self.running = True
        self.detector = CyclicDetector(alert_id, period, tolerance)
        if self.rl_agent is None:
            from rl_agent import RLAgent
            self.rl_agent = RLAgent()
        self.log(f"Tryb RL-polowania: ID=0x{alert_id:08X}, start_idx={self.start_index}")

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
        if self.mode == 'rl_hunt':
            self._run_rl_hunting()
        elif self.mode == 'hunt_deactivator':
            self._run_hunting()
        elif self.mode in ('find_start', 'find_end'):
            self._run_binary()
        elif self.mode == 'manual_parts':
            self._run_manual_parts()
        else:
            self.log("Nieznany tryb wyszukiwania")
        self.running = False
        self.done()
        self.log("Wyszukiwanie zakończone.")

    def _run_hunting(self):
        self.log("=== Rozpoczynanie polowania na dezaktywator ===")
        idx = self.start_index
        self.detector.reset()
        while self.running:
            if self.hunt_paused:
                time.sleep(0.1)
                continue

            if idx >= len(self.frames):
                idx = self.start_index
                self.detector.reset()
                self.log("--- Zapętlenie pliku ---")

            can_id, data, is_ext = self.frames[idx]
            success, msg = self.can.send_frame(can_id, data, is_ext)
            self.log(msg)

            now = time.time()
            deactivated = self.detector.feed_frame(can_id, data, is_ext, now)

            if deactivated:
                self.log("!!! Wykryto dezaktywację alertu !!!")
                candidates = self.detector.get_candidate_window(window_before=1.0)
                self.log(f"Znaleziono {len(candidates)} ramek w oknie przed dezaktywacją.")
                if self.deactivation_callback:
                    self.deactivation_callback(candidates)
                break

            idx += 1
            time.sleep(self.interval)

        self.log("Polowanie zakończone.")

    def _run_rl_hunting(self):
        self.log("=== Rozpoczynanie polowania z RL ===")
        idx = self.start_index
        self.detector.reset()
        self.rl_episode_frames_played = 0

        while self.running:
            if self.hunt_paused:
                time.sleep(0.1)
                continue

            if idx >= len(self.frames):
                idx = self.start_index
                self.detector.reset()
                self.log("--- Zapętlenie pliku ---")

            can_id, data, is_ext = self.frames[idx]
            success, msg = self.can.send_frame(can_id, data, is_ext)
            self.log(msg)
            self.rl_episode_frames_played += 1

            now = time.time()
            deactivated = self.detector.feed_frame(can_id, data, is_ext, now)

            if deactivated:
                self.log(f"!!! Dezaktywacja po {self.rl_episode_frames_played} ramkach !!!")
                candidates = self.detector.get_candidate_window(window_before=1.0)
                # Nagroda: im szybciej znaleziono, tym lepiej
                reward = 1.0 / max(1, self.rl_episode_frames_played)
                action = self.rl_agent.choose_action(self.start_index, self.rl_total_frames)
                new_start = max(0, min(self.rl_total_frames - 1, self.start_index + action))
                self.rl_agent.update(reward, new_start, self.rl_total_frames)
                self.rl_agent.save()
                self.log(f"RL: akcja={action}, nagroda={reward:.4f}, nowy start={new_start}")
                self.start_index = new_start
                if self.deactivation_callback:
                    self.deactivation_callback(candidates)
                break

            idx += 1
            time.sleep(self.interval)

        self.log("Polowanie RL zakończone.")

    def _run_binary(self):
        while self.running and self.left <= self.right:
            self.mid = (self.left + self.right) // 2
            if self.mode == 'find_start':
                start, end = self.left, self.mid - 1
            else:
                start, end = self.mid, self.right

            if start > end:
                self._save_state("empty_range")
                break

            self.log(f"=== Odtwarzanie zakresu [{start} .. {end}] ===")
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
                cid, data, is_ext = self.frames[self.left]
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

            part_probs = [(s, e, self.ml_model.predict_proba(extract_features(self.frames[s:e+1]))) for s, e in parts]
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
                feats = extract_features(self.frames[s:e+1])
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
                cid, data, is_ext = self.frames[self.left]
                self.log(f">>> Znaleziono ramkę: ID=0x{cid:08X} Data={data.hex().upper()} (indeks {self.left}) <<<")
                self.ml_model.train()
                break

            if self.ask("Zmienić liczbę części?", input_type='yesno'):
                new = self.ask("Nowa liczba części:", input_type='integer', default=self.num_parts)
                if new:
                    self.num_parts = new

    def _play_range(self, start, end):
        if start <= end:
            self.last_played_features = extract_features(self.frames[start:end+1])
        else:
            self.last_played_features = None
        for i in range(start, end + 1):
            if not self.running:
                break
            cid, data, is_ext = self.frames[i]
            success, msg = self.can.send_frame(cid, data, is_ext)
            self.log(msg)
            time.sleep(self.interval)

    def pause_hunting(self):
        self.hunt_paused = True

    def resume_hunting(self):
        self.hunt_paused = False

    def stop(self):
        self.running = False
        self.waiting_for_answer.set()
