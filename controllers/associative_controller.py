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
