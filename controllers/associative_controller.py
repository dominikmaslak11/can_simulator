"""Kontroler interaktywnego uczenia asocjacyjnego – Faza 7."""
import time
import logging
import json
import numpy as np

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
        self.buffer = []
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
        # Tryb wartościowy
        self.value_history = []          # lista zatwierdzonych wartości (float)
        self.value_timestamps = []       # odpowiadające im timestampy
        self.value_labels = []           # etykiety dla bufora (słownik timestamp->wartość)


    def start(self):
        if self.running:
            return
        self.running = True
        self.listener_id = self.app.can.add_listener(self._on_message)
        logger.info("AssociativeController uruchomiony (Faza 7)")

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
            self._analyze()

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
        cutoff = now - self.max_age
        while self.buffer and self.buffer[0][0] < cutoff:
            self.buffer.pop(0)

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
        """Filtruje ID, które są cykliczne i mało zmienne."""
        timestamps = [ts for ts, rec in self.buffer if rec["arb_id"] == arb_id]
        if len(timestamps) < 3:
            return False
        diffs = np.diff(timestamps)
        mean_diff = np.mean(diffs)
        std_diff = np.std(diffs)
        # Jeśli odstępy są bardzo regularne (niska zmienność), to prawdopodobnie cykliczny szum
        if mean_diff > 0 and std_diff / mean_diff < 0.1:
            return True
        return False


    def _analyze_value_correlation(self):
        """Analizuje korelację między wartościami bajtów a wartością referencyjną."""
        if len(self.value_history) < 3:
            return []   # za mało danych

        candidates = []
        margin = self.tolerance_ms / 1000.0

        # Dla każdego unikalnego ID w buforze
        for arb_id in set(rec["arb_id"] for _, rec in self.buffer):
            # Zbierz próbki: dla każdej zarejestrowanej wartości znajdź średnią bajtu w oknie
            byte_samples = {i: [] for i in range(8)}
            ref_values = []

            for ref_ts, ref_val in zip(self.value_timestamps, self.value_history):
                frame_slice = [rec for ts, rec in self.buffer
                               if rec["arb_id"] == arb_id
                               and (ref_ts - margin) <= ts <= (ref_ts + margin)]
                if not frame_slice:
                    continue
                # Dla każdego bajtu weź średnią z okna
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

            # Oblicz korelację Pearsona dla każdego bajtu
            for byte_idx in range(8):
                x = ref_values
                y = byte_samples[byte_idx]
                if len(set(y)) < 2:   # bajt się nie zmienia
                    continue
                r = self._pearson_correlation(x, y)
                if r is None:
                    continue
                abs_r = abs(r)
                if abs_r >= 0.8:   # próg korelacji
                    candidates.append({
                        "id": arb_id,
                        "byte": byte_idx,
                        "value": round(np.mean(y)),
                        "background": None,
                        "pos_count": len(x),
                        "neg_count": 0,
                        "confidence": round(abs_r * 100, 1),
                        "source": "wartosc" if not self.iteration_count else "wartosc"
                    })

        candidates.sort(key=lambda c: c["confidence"], reverse=True)
        return candidates

    @staticmethod
    def _pearson_correlation(x, y):
        """Oblicza współczynnik korelacji Pearsona."""
        n = len(x)
        if n < 3:
            return None
        import math
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        num = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        den_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
        den_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))
        if den_x == 0 or den_y == 0:
            return None
        return num / (den_x * den_y)

    def _analyze(self):
        pos_frames = self.last_labeled["positive"]
        neg_frames = self.last_labeled["negative"]

        candidates = []
        for arb_id in set(f["arb_id"] for f in pos_frames):
            # Filtrujemy szum cykliczny
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

                # Dodatkowe kryterium: bajt w tle musi być stabilny (max 1 wartość)
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

        # Klasyfikator online (jeśli dostępny)
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

                # Dodaj wyniki z trybu wartościowego
        wartosciowi = self._analyze_value_correlation()
        candidates.extend(wartosciowi)

        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        self.candidates = candidates
        logger.info("Analiza zakończona (Faza 7): %d kandydatów", len(candidates))

    def get_candidates(self):
        return self.candidates

    def get_best_candidate(self):
        if self.candidates:
            return self.candidates[0]
        return None

    def export_pattern(self, filepath):
        """Zapisuje najlepszego kandydata do pliku JSON."""
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
            "description": "Wzorzec wygenerowany przez uczenie asocjacyjne"
        }
        with open(filepath, "w") as f:
            json.dump(pattern, f, indent=2)
        logger.info(f"Wzorzec zapisany do {filepath}")
        return pattern


    def commit_value(self, value: float):
        """Rejestruje wartość referencyjną z bieżącym timestampem."""
        now = time.time()
        self.value_history.append(value)
        self.value_timestamps.append(now)
        # Oznacz ramki w buforze w oknie tolerancji
        margin = self.tolerance_ms / 1000.0
        for ts, rec in self.buffer:
            if (now - margin) <= ts <= (now + margin):
                rec_id = id(rec)
                self.value_labels.append((ts, rec, value))
        logger.info(f"Zarejestrowano wartość {value} (historia: {len(self.value_history)})")

    def undo_last_value(self):
        """Usuwa ostatnią zatwierdzoną wartość."""
        if not self.value_history:
            return
        removed = self.value_history.pop()
        self.value_timestamps.pop()
        # Usuń odpowiadające etykiety
        cutoff = self.value_timestamps[-1] if self.value_timestamps else 0
        self.value_labels = [(ts, rec, v) for ts, rec, v in self.value_labels if ts <= cutoff]
        logger.info(f"Cofnięto wartość {removed}")

    def get_value_history(self):
        return list(self.value_history)


    def find_sequences(self, main_candidate, tolerance_ms=200):
        """
        Szuka powtarzalnych sekwencji wokół głównej ramki (main_candidate).
        Zwraca listę słowników z kluczami:
        - main_id, main_byte
        - ids_order: lista ID w kolejności występowania
        - avg_delays: średnie odstępy między ramkami
        - confidence: procent okien, w których sekwencja wystąpiła
        """
        margin = tolerance_ms / 1000.0
        main_id = main_candidate["id"]
        main_byte = main_candidate["byte"]

        # Zbierz wszystkie wystąpienia głównej ramki w buforze
        main_events = [ts for ts, rec in self.buffer if rec["arb_id"] == main_id]

        if len(main_events) < 3:
            logger.info("Za mało wystąpień głównej ramki do analizy sekwencji.")
            return []

        # Dla każdego wystąpienia znajdź sąsiadujące ID w oknie czasowym
        neighbor_stats = {}  # {arb_id: {"before": count, "after": count, "delays": []}}
        window_before = 0.5  # sekund przed
        window_after = 0.5   # sekund po

        for main_ts in main_events:
            # Znajdź ramki w oknie wokół main_ts
            for ts, rec in self.buffer:
                if rec["arb_id"] == main_id:
                    continue
                if (main_ts - window_before) <= ts <= main_ts:
                    # Ramka przed
                    nid = rec["arb_id"]
                    if nid not in neighbor_stats:
                        neighbor_stats[nid] = {"before": 0, "after": 0, "delays": []}
                    neighbor_stats[nid]["before"] += 1
                    neighbor_stats[nid]["delays"].append(main_ts - ts)
                elif main_ts < ts <= (main_ts + window_after):
                    # Ramka po
                    nid = rec["arb_id"]
                    if nid not in neighbor_stats:
                        neighbor_stats[nid] = {"before": 0, "after": 0, "delays": []}
                    neighbor_stats[nid]["after"] += 1
                    neighbor_stats[nid]["delays"].append(ts - main_ts)

        # Filtruj – tylko ID występujące w >80% okien
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

        # Buduj sekwencję: sortuj według avg_delay i kierunku
        before_ids = [n for n in frequent_neighbors if n["direction"] == "before"]
        after_ids = [n for n in frequent_neighbors if n["direction"] == "after"]

        before_ids.sort(key=lambda x: x["avg_delay"], reverse=True)  # najbliższe przed
        after_ids.sort(key=lambda x: x["avg_delay"])                # najbliższe po

        ids_order = [n["id"] for n in before_ids] + [main_id] + [n["id"] for n in after_ids]

        # Oblicz uśrednioną pewność sekwencji
        avg_confidence = sum(n["occurrence_ratio"] for n in frequent_neighbors) / len(frequent_neighbors) * 100

        sequence = [{
            "main_id": main_id,
            "main_byte": main_byte,
            "ids_order": ids_order,
            "neighbors": frequent_neighbors,
            "confidence": round(avg_confidence, 1),
            "source": "sekwencja"
        }]
        logger.info(f"Znaleziono sekwencję: {' -> '.join(hex(i) for i in ids_order)}")
        return sequence

    def get_highlight_ids(self, threshold=80.0):
        ids = []
        for c in self.candidates:
            if c["confidence"] >= threshold:
                ids.append(c["id"])
        return list(set(ids))

    def get_iteration_count(self):
        return self.iteration_count

    def get_buffer_snapshot(self, max_items=50):
        return [rec for _, rec in self.buffer[-max_items:]]
