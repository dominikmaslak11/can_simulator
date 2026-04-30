#!/bin/bash
# fix_F11_final.sh – Ostateczna naprawa błędów składniowych i optymalizacyjnych (Faza 11)
# Uruchom w katalogu can_simulator/

set -e

echo "=== Ostateczna naprawa błędów (Faza 11) ==="

# ---------- 1. Poprawiony controllers/associative_controller.py ----------
cat > controllers/associative_controller.py << 'CONTROLLER_EOF'
"""Kontroler interaktywnego uczenia asocjacyjnego – Faza 11."""
import threading
import time
import math
from collections import deque
import logging
import json
import numpy as np
import csv

logger = logging.getLogger("AssociativeController")

try:
    from sklearn.linear_model import PassiveAggressiveClassifier
    from sklearn.preprocessing import LabelEncoder, StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class AssociativeController:
    def __init__(self, app):
        self.app = app
        self.running = False
        self.buffer = deque(maxlen=5000)
        self.buffer_index = {}
        self.max_age = 10.0
        self.tolerance_ms = 200
        self.event_active = False
        self.event_start_time = None
        self.iteration_count = 0
        self.listener_id = None
        self.last_labeled = {"positive": [], "negative": []}
        self.candidates = []

        # Klasyfikator
        self.classifier = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.classifier_ready = False

        if SKLEARN_AVAILABLE:
            self.classifier = PassiveAggressiveClassifier(warm_start=True, random_state=42)
        # Wątek analizy
        self.analysis_thread = None
        self.analysis_lock = threading.Lock()
        self.pending_analysis = False

        # Tryb wartościowy
        self.value_history = []
        self.value_timestamps = []
        self.value_labels = []

    def start(self):
        if self.running:
            return
        self.running = True
        self.listener_id = self.app.can.add_listener(self._on_message)
        logger.info("AssociativeController uruchomiony (Faza 11)")

    def stop(self):
        self.running = False
        if self.listener_id is not None:
            self.app.can.remove_listener(self.listener_id)
            self.listener_id = None
        logger.info("AssociativeController zatrzymany")

    def set_tolerance(self, ms):
        self.tolerance_ms = ms

    def toggle_event(self):
        now = time.time()
        if not self.event_active:
            self.event_active = True
            self.event_start_time = now
            logger.info(f"Zdarzenie ROZPOCZĘTE o {now:.3f}")
        else:
            self.event_active = False
            event_stop = now
            logger.info(f"Zdarzenie ZAKOŃCZONE o {event_stop:.3f}")
            self._label_frames(self.event_start_time, event_stop)
            self.iteration_count += 1
            self._run_analysis_in_thread()

    def _on_message(self, msg):
        if not self.running:
            return
        now = time.time()
        record = {
            "timestamp": now,
            "arb_id": msg.arbitration_id,
            "data": list(msg.data),
            "dlc": msg.dlc,
            "is_extended": msg.is_extended,
        }
        self.buffer.append((now, record))
        arb_id = record["arb_id"]
        if arb_id not in self.buffer_index:
            self.buffer_index[arb_id] = []
        self.buffer_index[arb_id].append(len(self.buffer) - 1)
        cutoff = now - self.max_age
        while self.buffer and self.buffer[0][0] < cutoff:
            old_ts, old_rec = self.buffer[0]
            old_id = old_rec["arb_id"]
            if old_id in self.buffer_index and self.buffer_index[old_id]:
                self.buffer_index[old_id].pop(0)
                if not self.buffer_index[old_id]:
                    del self.buffer_index[old_id]

    def _label_frames(self, start_time, end_time):
        margin = self.tolerance_ms / 1000.0
        pos = []
        neg = []
        for ts, rec in self.buffer:
            if (start_time - margin) <= ts <= (end_time + margin):
                pos.append(rec)
            else:
                neg.append(rec)
        self.last_labeled["positive"] = pos
        self.last_labeled["negative"] = neg
        self._update_classifier(pos, neg)

    def _update_classifier(self, pos, neg):
        if not SKLEARN_AVAILABLE or self.classifier is None:
            return
        if len(pos) == 0:
            return
        X = []
        y = []
        for rec in pos:
            X.append(self._extract_features(rec))
            y.append("positive")
        for rec in neg:
            X.append(self._extract_features(rec))
            y.append("negative")
        if len(X) < 2:
            return
        try:
            if not self.classifier_ready:
                self.scaler.fit(X)
                X_scaled = self.scaler.transform(X)
                self.label_encoder.fit(y)
                y_enc = self.label_encoder.transform(y)
                self.classifier.fit(X_scaled, y_enc)
                self.classifier_ready = True
            else:
                X_scaled = self.scaler.transform(X)
                y_enc = self.label_encoder.transform(y)
                self.classifier.partial_fit(X_scaled, y_enc)
        except Exception as e:
            logger.warning(f"Błąd trenowania klasyfikatora: {e}")

    def _extract_features(self, rec):
        features = [float(rec["arb_id"]), float(rec["is_extended"]), float(rec["dlc"])]
        data = rec["data"]
        for i in range(8):
            features.append(float(data[i]) if i < len(data) else 0.0)
        return features

    def _is_noisy_id(self, arb_id):
        if arb_id not in self.buffer_index:
            return False
        indices = self.buffer_index[arb_id]
        if len(indices) < 3:
            return False
        timestamps = [self.buffer[i][0] for i in indices if i < len(self.buffer)]
        diffs = np.diff(timestamps)
        mean_diff = np.mean(diffs)
        std_diff = np.std(diffs)
        if mean_diff > 0 and std_diff / mean_diff < 0.1:
            return True
        return False

    def _analyze_value_correlation(self):
        if len(self.value_history) < 3:
            return []
        candidates = []
        margin = self.tolerance_ms / 1000.0
        for arb_id in set(rec["arb_id"] for _, rec in self.buffer):
            byte_samples = {i: [] for i in range(8)}
            ref_values = []
            for ref_ts, ref_val in zip(self.value_timestamps, self.value_history):
                frame_slice = [rec for ts, rec in self.buffer
                               if rec["arb_id"] == arb_id
                               and (ref_ts - margin) <= ts <= (ref_ts + margin)]
                if not frame_slice:
                    continue
                avg_data = [0] * 8
                for rec in frame_slice:
                    for i, b in enumerate(rec["data"]):
                        avg_data[i] += b
                for i in range(8):
                    avg_data[i] /= len(frame_slice)
                for i in range(8):
                    byte_samples[i].append(avg_data[i])
                ref_values.append(ref_val)
            if len(ref_values) < 3:
                continue
            for byte_idx in range(8):
                x = ref_values
                y = byte_samples[byte_idx]
                if len(set(y)) < 2:
                    continue
                r = self._pearson_correlation(x, y)
                if r is None:
                    continue
                abs_r = abs(r)
                if abs_r >= 0.8:
                    candidates.append({
                        "id": arb_id,
                        "byte": byte_idx,
                        "value": round(np.mean(y)),
                        "background": None,
                        "pos_count": len(x),
                        "neg_count": 0,
                        "confidence": round(abs_r * 100, 1),
                        "source": "wartosc"
                    })
        candidates.sort(key=lambda c: c["confidence"], reverse=True)
        return candidates

    @staticmethod
    def _pearson_correlation(x, y):
        n = len(x)
        if n < 3:
            return None
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        num = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        den_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
        den_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))
        if den_x == 0 or den_y == 0:
            return None
        return num / (den_x * den_y)

    def _run_analysis_in_thread(self):
        if self.analysis_thread and self.analysis_thread.is_alive():
            self.pending_analysis = True
            return
        self.analysis_thread = threading.Thread(target=self._analysis_worker, daemon=True)
        self.analysis_thread.start()
        logger.debug("Uruchomiono wątek analizy.")

    def _analysis_worker(self):
        with self.analysis_lock:
            try:
                self._analyze()
                logger.debug("Analiza w tle zakończona.")
            except Exception as e:
                logger.error(f"Błąd analizy w wątku: {e}")
            finally:
                self.analysis_thread = None
                if self.pending_analysis:
                    self.pending_analysis = False
                    self._run_analysis_in_thread()

    def _analyze(self):
        pos_frames = self.last_labeled["positive"]
        neg_frames = self.last_labeled["negative"]
        candidates = []
        for arb_id in set(f["arb_id"] for f in pos_frames):
            if self._is_noisy_id(arb_id):
                logger.debug(f"Pominięto ID 0x{arb_id:X} (cykliczny szum)")
                continue
            pos_samples = [f["data"] for f in pos_frames if f["arb_id"] == arb_id]
            neg_samples = [f["data"] for f in neg_frames if f["arb_id"] == arb_id]
            if not pos_samples:
                continue
            dlc = max(len(s) for s in pos_samples)
            for byte_idx in range(dlc):
                pos_vals = [s[byte_idx] for s in pos_samples if len(s) > byte_idx]
                neg_vals = [s[byte_idx] for s in neg_samples if len(s) > byte_idx]
                if not pos_vals:
                    continue
                unique_pos = set(pos_vals)
                unique_neg = set(neg_vals) if neg_vals else set()
                if len(unique_neg) > 1:
                    continue
                background_val = next(iter(unique_neg)) if unique_neg else None
                for val in unique_pos:
                    if val != background_val:
                        confidence = 100.0
                        candidates.append({
                            "id": arb_id,
                            "byte": byte_idx,
                            "value": val,
                            "background": background_val,
                            "pos_count": pos_vals.count(val),
                            "neg_count": len(neg_vals),
                            "confidence": round(confidence, 1)
                        })
        if SKLEARN_AVAILABLE and self.classifier_ready:
            for cand in candidates:
                rec = {
                    "arb_id": cand["id"],
                    "is_extended": 0,
                    "dlc": max(8, cand["byte"]+1),
                    "data": [0]*8
                }
                rec["data"][cand["byte"]] = cand["value"]
                features = self._extract_features(rec)
                try:
                    X = self.scaler.transform([features])
                    proba = self.classifier.predict_proba(X)
                    pos_idx = list(self.classifier.classes_).index(
                        self.label_encoder.transform(["positive"])[0]
                    )
                    model_conf = proba[0][pos_idx] * 100.0
                    cand["confidence"] = round((cand["confidence"] + model_conf) / 2, 1)
                except Exception:
                    pass
        wartosciowi = self._analyze_value_correlation()
        candidates.extend(wartosciowi)
        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        self.candidates = candidates
        logger.info("Analiza zakończona (Faza 11): %d kandydatów", len(candidates))

    def get_candidates(self):
        return self.candidates

    def get_best_candidate(self):
        if self.candidates:
            return self.candidates[0]
        return None

    def get_highlight_ids(self, threshold=80.0):
        ids = []
        for c in self.candidates:
            if c["confidence"] >= threshold:
                ids.append(c["id"])
        return list(set(ids))

    def get_iteration_count(self):
        return self.iteration_count

    def get_buffer_snapshot(self, max_items=50):
        if not self.buffer:
            return []
        items = list(self.buffer)[-max_items:]
        return [rec for _, rec in items]

    def commit_value(self, value: float):
        now = time.time()
        self.value_history.append(value)
        self.value_timestamps.append(now)
        margin = self.tolerance_ms / 1000.0
        for ts, rec in self.buffer:
            if (now - margin) <= ts <= (now + margin):
                self.value_labels.append((ts, rec, value))
        logger.info(f"Zarejestrowano wartość {value} (historia: {len(self.value_history)})")

    def undo_last_value(self):
        if not self.value_history:
            return
        removed = self.value_history.pop()
        self.value_timestamps.pop()
        cutoff = self.value_timestamps[-1] if self.value_timestamps else 0
        self.value_labels = [(ts, rec, v) for ts, rec, v in self.value_labels if ts <= cutoff]
        logger.info(f"Cofnięto wartość {removed}")

    def get_value_history(self):
        return list(self.value_history)

    def find_sequences(self, main_candidate, tolerance_ms=200):
        main_id = main_candidate["id"]
        if main_id not in self.buffer_index:
            return []
        main_indices = self.buffer_index[main_id]
        main_events = [self.buffer[i][0] for i in main_indices if i < len(self.buffer)]
        if len(main_events) < 3:
            return []
        neighbor_stats = {}
        window_before = 0.5
        window_after = 0.5
        for main_ts in main_events:
            for ts, rec in self.buffer:
                if rec["arb_id"] == main_id:
                    continue
                if (main_ts - window_before) <= ts <= main_ts:
                    nid = rec["arb_id"]
                    if nid not in neighbor_stats:
                        neighbor_stats[nid] = {"before": 0, "after": 0, "delays": []}
                    neighbor_stats[nid]["before"] += 1
                    neighbor_stats[nid]["delays"].append(main_ts - ts)
                elif main_ts < ts <= (main_ts + window_after):
                    nid = rec["arb_id"]
                    if nid not in neighbor_stats:
                        neighbor_stats[nid] = {"before": 0, "after": 0, "delays": []}
                    neighbor_stats[nid]["after"] += 1
                    neighbor_stats[nid]["delays"].append(ts - main_ts)
        threshold_ratio = 0.8
        total_windows = len(main_events)
        frequent_neighbors = []
        for arb_id, stats in neighbor_stats.items():
            max_occurrence = max(stats["before"], stats["after"])
            if max_occurrence / total_windows >= threshold_ratio:
                avg_delay = sum(stats["delays"]) / len(stats["delays"]) if stats["delays"] else 0
                direction = "before" if stats["before"] > stats["after"] else "after"
                frequent_neighbors.append({
                    "id": arb_id,
                    "direction": direction,
                    "avg_delay": avg_delay,
                    "occurrence_ratio": max_occurrence / total_windows
                })
        if not frequent_neighbors:
            return []
        before_ids = [n for n in frequent_neighbors if n["direction"] == "before"]
        after_ids = [n for n in frequent_neighbors if n["direction"] == "after"]
        before_ids.sort(key=lambda x: x["avg_delay"], reverse=True)
        after_ids.sort(key=lambda x: x["avg_delay"])
        ids_order = [n["id"] for n in before_ids] + [main_id] + [n["id"] for n in after_ids]
        avg_confidence = sum(n["occurrence_ratio"] for n in frequent_neighbors) / len(frequent_neighbors) * 100
        sequence = [{
            "main_id": main_id,
            "ids_order": ids_order,
            "neighbors": frequent_neighbors,
            "confidence": round(avg_confidence, 1),
            "source": "sekwencja"
        }]
        logger.info(f"Znaleziono sekwencję: {' -> '.join(hex(i) for i in ids_order)}")
        return sequence

    def export_to_csv(self, filepath):
        if not self.candidates:
            raise ValueError("Brak kandydatów do eksportu.")
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["CAN_ID", "Byte", "Value", "Background", "Confidence", "Source", "Sequence"])
            for c in self.candidates:
                writer.writerow([
                    f"0x{c['id']:X}",
                    c.get("byte", ""),
                    f"0x{c['value']:02X}" if isinstance(c.get("value"), int) else c.get("value", ""),
                    f"0x{c['background']:02X}" if isinstance(c.get("background"), int) else c.get("background", ""),
                    c["confidence"],
                    c.get("source", ""),
                    c.get("ids_order", "")
                ])
        logger.info(f"Eksportowano CSV do {filepath}")

    def export_to_html(self, filepath):
        if not self.candidates:
            raise ValueError("Brak kandydatów do eksportu.")
        html = ["<html><head><meta charset='utf-8'><title>CAN Asocjacja</title></head><body>"]
        html.append("<h2>Wyniki uczenia asocjacyjnego</h2>")
        html.append("<table border='1'><tr><th>CAN ID</th><th>Bajt</th><th>Wartość</th><th>Tło</th><th>Pewność</th><th>Źródło</th><th>Sekwencja</th></tr>")
        for c in self.candidates:
            html.append("<tr>")
            html.append(f"<td>0x{c['id']:X}</td>")
            html.append(f"<td>{c.get('byte', '')}</td>")
            html.append(f"<td>0x{c['value']:02X}</td>" if isinstance(c.get("value"), int) else f"<td>{c.get('value', '')}</td>")
            html.append(f"<td>0x{c['background']:02X}</td>" if isinstance(c.get("background"), int) else f"<td>{c.get('background', '')}</td>")
            html.append(f"<td>{c['confidence']:.1f}%</td>")
            html.append(f"<td>{c.get('source', '')}</td>")
            html.append(f"<td>{c.get('ids_order', '')}</td>")
            html.append("</tr>")
        html.append("</table></body></html>")
        with open(filepath, "w") as f:
            f.write("\n".join(html))
        logger.info(f"Eksportowano HTML do {filepath}")

    def export_pattern(self, filepath):
        best = self.get_best_candidate()
        if not best:
            raise ValueError("Brak kandydatów do eksportu.")
        pattern = {
            "format_version": 1,
            "timestamp": time.time(),
            "id": best["id"],
            "byte_index": best["byte"],
            "expected_value": best["value"],
            "background_value": best["background"],
            "confidence": best["confidence"],
            "source": best.get("source", "zdarzenie"),
            "description": "Wzorzec wygenerowany przez uczenie asocjacyjne"
        }
        with open(filepath, "w") as f:
            json.dump(pattern, f, indent=2)
        logger.info(f"Wzorzec zapisany do {filepath}")
        return pattern
CONTROLLER_EOF
echo "controllers/associative_controller.py – poprawiony"

# ---------- 2. Poprawka gui/tabs/associative_tab.py (kolumna sekwencji) ----------
python3 << 'PYEOF'
with open("gui/tabs/associative_tab.py", "r") as f:
    content = f.read()

# Poprawiamy _update_candidates_table – dodajemy pustą sekwencję na końcu
old_insert = '''            self.tree.insert("", "end", values=(
                f"0x{c['id']:X}",
                c['byte'],
                f"0x{c['value']:02X}",
                bg,
                f"{c['confidence']:.1f}",
                src
            ))'''

new_insert = '''            seq_str = c.get("ids_order", "")
            if isinstance(seq_str, list):
                seq_str = " -> ".join(str(i) for i in seq_str)
            self.tree.insert("", "end", values=(
                f"0x{c['id']:X}",
                c['byte'],
                f"0x{c['value']:02X}",
                bg,
                f"{c['confidence']:.1f}",
                src,
                seq_str
            ))'''

if old_insert in content:
    content = content.replace(old_insert, new_insert)
    with open("gui/tabs/associative_tab.py", "w") as f:
        f.write(content)
    print("Poprawiono _update_candidates_table – dodano kolumnę 'Sekwencja'.")
else:
    print("Nie znaleziono starej wersji _update_candidates_table (może już poprawiona).")
PYEOF

# ---------- 3. Sprawdzenie składni ----------
echo ""
echo "Sprawdzanie składni:"
python3 -m py_compile controllers/associative_controller.py && echo "  controller OK" || echo "  controller BŁĄD"
python3 -m py_compile gui/tabs/associative_tab.py && echo "  tab OK" || echo "  tab BŁĄD"

echo ""
echo "=== Ostateczna naprawa zakończona ==="
echo "Możesz teraz uruchomić ./run.sh"
