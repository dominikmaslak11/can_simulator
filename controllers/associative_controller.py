"""Kontroler interaktywnego uczenia asocjacyjnego – Faza 5."""
import time
import logging
import numpy as np

logger = logging.getLogger("AssociativeController")

# Opcjonalny import – jeśli nie ma sklearn, model będzie wyłączony
try:
    from sklearn.linear_model import PassiveAggressiveClassifier
    from sklearn.preprocessing import LabelEncoder, StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn nie jest dostępny. Klasyfikator online wyłączony.")


class AssociativeController:
    def __init__(self, app):
        self.app = app
        self.running = False
        self.buffer = []          # lista (timestamp, msg_dict)
        self.max_age = 10.0       # sekund
        self.tolerance_ms = 200   # ±200 ms
        self.event_active = False
        self.event_start_time = None
        self.iteration_count = 0
        self.listener_id = None
        self.last_labeled = {"positive": [], "negative": []}
        self.candidates = []      # lista wyników analizy bajtów

        # Klasyfikator online
        self.classifier = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.classifier_ready = False
        self.X_buffer = []   # przechowuje cechy ostatnich próbek (dla partial_fit)
        self.y_buffer = []

        if SKLEARN_AVAILABLE:
            self.classifier = PassiveAggressiveClassifier(warm_start=True, random_state=42)

    def start(self):
        if self.running:
            return
        self.running = True
        self.listener_id = self.app.can.add_listener(self._on_message)
        logger.info("AssociativeController uruchomiony (z klasyfikatorem online)")

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
            logger.info(f"Iteracja {self.iteration_count} zakończona")
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
        logger.info(f"Oznaczono: {len(pos)} pozytywnych, {len(neg)} negatywnych")
        self._update_classifier(pos, neg)

    def _update_classifier(self, pos, neg):
        """Przygotowuje dane i trenuje klasyfikator online."""
        if not SKLEARN_AVAILABLE or self.classifier is None:
            return
        if len(pos) == 0:
            return

        # Tworzymy zestaw cech: każda ramka jako wektor
        X = []
        y = []
        for rec in pos:
            features = self._extract_features(rec)
            X.append(features)
            y.append("positive")
        for rec in neg:
            features = self._extract_features(rec)
            X.append(features)
            y.append("negative")

        if len(X) < 2:
            return

        # Skalowanie i trenowanie
        try:
            if not self.classifier_ready:
                # Pierwsze dopasowanie – full fit
                self.scaler.fit(X)
                X_scaled = self.scaler.transform(X)
                self.label_encoder.fit(y)
                y_encoded = self.label_encoder.transform(y)
                self.classifier.fit(X_scaled, y_encoded)
                self.classifier_ready = True
            else:
                # Przyrostowe – partial_fit
                X_scaled = self.scaler.transform(X)
                y_encoded = self.label_encoder.transform(y)
                self.classifier.partial_fit(X_scaled, y_encoded)
            logger.info("Klasyfikator zaktualizowany.")
        except Exception as e:
            logger.warning(f"Błąd trenowania klasyfikatora: {e}")

    def _extract_features(self, rec):
        """Zamienia rekord na wektor liczbowy."""
        # Cechy: ID (zakodowane jako float), bajty 0..7 (z dopełnieniem)
        features = [float(rec["arb_id"]), float(rec["is_extended"]), float(rec["dlc"])]
        data = rec["data"]
        for i in range(8):
            features.append(float(data[i]) if i < len(data) else 0.0)
        return features

    def _analyze(self):
        """Uruchamia analizę bajt po bajcie oraz dodaje wyniki klasyfikatora."""
        pos_frames = self.last_labeled["positive"]
        neg_frames = self.last_labeled["negative"]

        candidates = []
        # Analiza per bajt (jak wcześniej)
        for arb_id in set(f["arb_id"] for f in pos_frames):
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

                if len(unique_neg) <= 1:
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

        # Dodatkowo: jeśli klasyfikator działa, przypisujemy mu pewność dla ID
        if SKLEARN_AVAILABLE and self.classifier_ready:
            for cand in candidates:
                # Tworzymy syntetyczną ramkę z wartością bajtu
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
                    positive_idx = list(self.classifier.classes_).index(
                        self.label_encoder.transform(["positive"])[0]
                    )
                    model_confidence = proba[0][positive_idx] * 100.0
                    # Modyfikujemy pewność – średnia ważona z heurystyki i modelu
                    cand["confidence"] = round((cand["confidence"] + model_confidence) / 2, 1)
                except Exception:
                    pass

        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        self.candidates = candidates
        logger.info("Analiza zakończona, znaleziono %d kandydatów (z modelem)", len(candidates))

    def get_candidates(self):
        return self.candidates

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
