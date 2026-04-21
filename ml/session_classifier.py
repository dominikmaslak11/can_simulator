import os
import logging
import numpy as np
from collections import deque

logger = logging.getLogger("ML.SessionClassifier")

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch nie jest dostępny – używam regresji logistycznej.")

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import IsolationForest

# Parametry okna czasowego
WINDOW_SECONDS = 5.0
STEP_SECONDS = 1.0


class LSTMClassifier(nn.Module):
    def __init__(self, input_dim, hidden_dim=32):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, batch_first=True, bidirectional=True)
        self.fc = nn.Linear(hidden_dim * 2, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        out, _ = self.lstm(x)
        out = out[:, -1, :]
        out = self.fc(out)
        return self.sigmoid(out)


class SessionClassifier:
    def __init__(self, model_path="session_classifier.pth"):
        self.model_path = model_path
        self.lstm_model = None
        self.fallback_model = None
        self.use_lstm = TORCH_AVAILABLE
        self.input_dim = 10
        self.window_sec = WINDOW_SECONDS
        self.step_sec = STEP_SECONDS
        self.isolation_forest = None   # model bez nadzoru

    def _extract_features_from_window(self, frames):
        if not frames:
            return np.zeros(self.input_dim)
        n = len(frames)
        ids = [f[0] for f in frames]
        data_lens = [len(f[1]) for f in frames]
        is_ext = [1 if f[2] else 0 for f in frames]
        timestamps = [f[3] for f in frames if f[3] is not None]

        feats = [
            n,
            np.mean(ids) if ids else 0,
            np.std(ids) if len(ids) > 1 else 0,
            len(set(ids)) / max(1, n),
            np.mean(data_lens) if data_lens else 0,
            np.mean(is_ext) if is_ext else 0,
        ]
        if len(timestamps) > 1:
            diffs = np.diff(sorted(timestamps))
            feats.extend([
                np.mean(diffs),
                np.std(diffs) if len(diffs) > 1 else 0,
                np.min(diffs),
                np.max(diffs)
            ])
        else:
            feats.extend([0, 0, 0, 0])
        return np.array(feats, dtype=np.float32)

    def _sliding_windows(self, frames):
        if not frames:
            return []
        windows = []
        timestamps = [f[3] for f in frames]
        t_min = timestamps[0]
        t_max = timestamps[-1]
        current_start = t_min
        while current_start < t_max:
            current_end = current_start + self.window_sec
            window_frames = [f for f in frames if current_start <= f[3] < current_end]
            windows.append(window_frames)
            current_start += self.step_sec
        return windows

    def prepare_training_data(self, normal_log_frames):
        windows = self._sliding_windows(normal_log_frames)
        X, y = [], []
        for win in windows:
            feats = self._extract_features_from_window(win)
            X.append(feats)
            y.append(0)
        return np.array(X), np.array(y)

    def train(self, normal_frames, anomaly_frames=None):
        X_norm, y_norm = self.prepare_training_data(normal_frames)
        if anomaly_frames:
            X_anom, y_anom = self.prepare_training_data(anomaly_frames)
            y_anom[:] = 1
            X = np.vstack([X_norm, X_anom])
            y = np.concatenate([y_norm, y_anom])
        else:
            X, y = X_norm, y_norm

        if len(X) < 2:
            logger.warning("Zbyt mało danych do trenowania.")
            return False

        if self.use_lstm:
            self._train_lstm(X, y)
        else:
            self._train_fallback(X, y)

        # Trenuj również Isolation Forest na normalnych danych
        if len(X_norm) > 0:
            self.isolation_forest = IsolationForest(contamination=0.05, random_state=42)
            self.isolation_forest.fit(X_norm)
            logger.info("Isolation Forest wytrenowany na normalnych danych.")
        return True

    def _train_lstm(self, X, y):
        X_tensor = torch.tensor(X, dtype=torch.float32).unsqueeze(1)
        y_tensor = torch.tensor(y, dtype=torch.float32).unsqueeze(1)

        self.lstm_model = LSTMClassifier(self.input_dim)
        optimizer = optim.Adam(self.lstm_model.parameters(), lr=0.001)
        criterion = nn.BCELoss()

        self.lstm_model.train()
        for epoch in range(30):
            optimizer.zero_grad()
            outputs = self.lstm_model(X_tensor)
            loss = criterion(outputs, y_tensor)
            loss.backward()
            optimizer.step()
        self.lstm_model.eval()
        self._save_model()

    def _train_fallback(self, X, y):
        self.fallback_model = make_pipeline(StandardScaler(), LogisticRegression())
        self.fallback_model.fit(X, y)

    def predict_proba(self, frames):
        windows = self._sliding_windows(frames)
        if not windows:
            return [], []
        X = np.array([self._extract_features_from_window(w) for w in windows])
        if self.use_lstm and self.lstm_model is not None:
            X_tensor = torch.tensor(X, dtype=torch.float32).unsqueeze(1)
            with torch.no_grad():
                probs = self.lstm_model(X_tensor).squeeze().numpy()
        elif self.fallback_model is not None:
            probs = self.fallback_model.predict_proba(X)[:, 1]
        else:
            probs = np.zeros(len(windows))

        times = []
        for w in windows:
            if w:
                t = np.mean([f[3] for f in w])
                times.append(t)
        return times, probs

    def detect_anomalies_unsupervised(self, frames):
        """Wykrywa anomalie za pomocą Isolation Forest (bez etykiet)."""
        windows = self._sliding_windows(frames)
        if not windows:
            return [], []
        X = np.array([self._extract_features_from_window(w) for w in windows])

        if self.isolation_forest is None:
            # Jeśli nie ma wytrenowanego modelu, trenuj na bieżących danych
            self.isolation_forest = IsolationForest(contamination=0.05, random_state=42)
            self.isolation_forest.fit(X)
            logger.info("Isolation Forest wytrenowany na bieżącym logu.")

        # -1 dla anomalii, 1 dla normalnych
        preds = self.isolation_forest.predict(X)
        # Konwertujemy na prawdopodobieństwo (0 = normalne, 1 = anomalia)
        scores = self.isolation_forest.decision_function(X)
        # Normalizacja do [0,1]
        probs = 1.0 - (scores - scores.min()) / (scores.max() - scores.min() + 1e-8)
        # Dla punktów sklasyfikowanych jako anomalie ustawiamy wyższe prawdopodobieństwo
        probs[preds == -1] = np.maximum(probs[preds == -1], 0.8)

        times = []
        for w in windows:
            if w:
                t = np.mean([f[3] for f in w])
                times.append(t)
        return times, probs

    def _save_model(self):
        if self.lstm_model:
            torch.save(self.lstm_model.state_dict(), self.model_path)

    def load_model(self):
        if os.path.exists(self.model_path) and self.use_lstm:
            self.lstm_model = LSTMClassifier(self.input_dim)
            self.lstm_model.load_state_dict(torch.load(self.model_path))
            self.lstm_model.eval()
            return True
        return False
