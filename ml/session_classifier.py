import os
import logging
import numpy as np
from collections import Counter, defaultdict

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

try:
    import cantools
    CANTTOOLS_AVAILABLE = True
except ImportError:
    CANTTOOLS_AVAILABLE = False

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
        self.isolation_forest = None
        self.normal_statistics = {}
        self.dbc_db = None
        self.signal_stats = {}

    def set_dbc(self, dbc_db):
        self.dbc_db = dbc_db

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

    def _compute_normal_statistics(self, normal_frames):
        id_frames = {}
        for f in normal_frames:
            cid = f[0]
            id_frames.setdefault(cid, []).append(f)

        for cid, frames in id_frames.items():
            if len(frames) < 2:
                continue
            timestamps = [f[3] for f in frames if f[3] is not None]
            if len(timestamps) < 2:
                continue
            diffs = np.diff(sorted(timestamps))
            self.normal_statistics[cid] = {
                'avg_interval': np.mean(diffs),
                'std_interval': np.std(diffs),
                'count': len(frames)
            }

        if self.dbc_db is not None:
            signal_values = defaultdict(list)
            for f in normal_frames:
                cid, data, _, ts = f
                try:
                    msg = self.dbc_db.get_message_by_frame_id(cid)
                    decoded = msg.decode(data)
                    for sig_name, val in decoded.items():
                        signal_values[sig_name].append(val)
                except:
                    continue
            for sig_name, vals in signal_values.items():
                if len(vals) > 1:
                    self.signal_stats[sig_name] = {
                        'min': np.min(vals),
                        'max': np.max(vals),
                        'mean': np.mean(vals),
                        'std': np.std(vals)
                    }

    def prepare_training_data(self, normal_log_frames):
        windows = self._sliding_windows(normal_log_frames)
        X, y = [], []
        for win in windows:
            feats = self._extract_features_from_window(win)
            X.append(feats)
            y.append(0)
        return np.array(X), np.array(y)

    def train(self, normal_frames, anomaly_frames=None):
        self._compute_normal_statistics(normal_frames)
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
            return [], [], []
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
        return times, probs, windows

    def detect_anomalies_unsupervised(self, frames):
        windows = self._sliding_windows(frames)
        if not windows:
            return [], [], []
        X = np.array([self._extract_features_from_window(w) for w in windows])

        if self.isolation_forest is None:
            self.isolation_forest = IsolationForest(contamination=0.05, random_state=42)
            self.isolation_forest.fit(X)
            logger.info("Isolation Forest wytrenowany na bieżącym logu.")

        preds = self.isolation_forest.predict(X)
        scores = self.isolation_forest.decision_function(X)
        probs = 1.0 - (scores - scores.min()) / (scores.max() - scores.min() + 1e-8)
        probs[preds == -1] = np.maximum(probs[preds == -1], 0.8)

        times = []
        for w in windows:
            if w:
                t = np.mean([f[3] for f in w])
                times.append(t)
        return times, probs, windows

    def _analyze_signals_in_window(self, window_frames):
        if self.dbc_db is None or not CANTTOOLS_AVAILABLE:
            return [], {}

        signal_issues = []
        details = {}
        window_signal_values = defaultdict(list)

        for f in window_frames:
            cid, data, _, _ = f
            try:
                msg = self.dbc_db.get_message_by_frame_id(cid)
                decoded = msg.decode(data)
                for sig_name, val in decoded.items():
                    window_signal_values[sig_name].append(val)
            except:
                continue

        for sig_name, vals in window_signal_values.items():
            if len(vals) == 0:
                continue
            avg_val = np.mean(vals)
            min_val = np.min(vals)
            max_val = np.max(vals)

            try:
                for msg in self.dbc_db.messages:
                    for sig in msg.signals:
                        if sig.name == sig_name:
                            dbc_min = sig.minimum
                            dbc_max = sig.maximum
                            if dbc_min is not None and min_val < dbc_min:
                                signal_issues.append(f"{sig_name}: poniżej min ({min_val:.2f} < {dbc_min:.2f})")
                            if dbc_max is not None and max_val > dbc_max:
                                signal_issues.append(f"{sig_name}: powyżej max ({max_val:.2f} > {dbc_max:.2f})")
                            break
            except:
                pass

            if sig_name in self.signal_stats:
                stats = self.signal_stats[sig_name]
                if abs(avg_val - stats['mean']) > 3 * stats['std']:
                    signal_issues.append(f"{sig_name}: odbiega od normy ({avg_val:.2f} vs {stats['mean']:.2f}±{3*stats['std']:.2f})")

            details[sig_name] = {
                'min': float(min_val),
                'max': float(max_val),
                'avg': float(avg_val),
                'count': len(vals)
            }

        return signal_issues, details

    def generate_report(self, frames, times, probs, windows, threshold=0.5):
        report = []
        for i, (t, p, w) in enumerate(zip(times, probs, windows)):
            if p < threshold or not w:
                continue

            start_time = min(f[3] for f in w if f[3] is not None)
            end_time = max(f[3] for f in w if f[3] is not None)

            causes = []
            details = {}

            ids_in_window = set(f[0] for f in w)
            if self.normal_statistics:
                missing_ids = set(self.normal_statistics.keys()) - ids_in_window
                if missing_ids:
                    causes.append(f"Brakujące ID: {', '.join(hex(c) for c in list(missing_ids)[:3])}")
                    suggested_intervals = {}
                    for mid in missing_ids:
                        if mid in self.normal_statistics:
                            suggested_intervals[mid] = self.normal_statistics[mid]['avg_interval']
                    details['suggested_intervals'] = suggested_intervals

            if self.normal_statistics:
                id_timestamps = {}
                for f in w:
                    cid = f[0]
                    id_timestamps.setdefault(cid, []).append(f[3])
                freq_issues = []
                for cid, stamps in id_timestamps.items():
                    if cid not in self.normal_statistics or len(stamps) < 2:
                        continue
                    diffs = np.diff(sorted(stamps))
                    avg = np.mean(diffs)
                    norm = self.normal_statistics[cid]
                    if abs(avg - norm['avg_interval']) > 2 * norm['std_interval']:
                        freq_issues.append(f"{hex(cid)}: {avg:.3f}s (norma: {norm['avg_interval']:.3f}s)")
                if freq_issues:
                    causes.append(f"Zmiana częstotliwości: {'; '.join(freq_issues[:2])}")
                    details['frequency'] = freq_issues

            signal_issues, signal_details = self._analyze_signals_in_window(w)
            if signal_issues:
                causes.extend(signal_issues[:3])
                details['signals'] = signal_details

            if self.normal_statistics:
                normal_total = sum(s['count'] for s in self.normal_statistics.values())
                window_total = len(w)
                if normal_total > 0:
                    ratio = window_total / normal_total
                    if ratio < 0.5:
                        causes.append(f"Mało ramek: {window_total} (norma ~{normal_total})")
                    elif ratio > 2.0:
                        causes.append(f"Dużo ramek: {window_total} (norma ~{normal_total})")

            cause_str = '; '.join(causes) if causes else "Odchylenie statystyczne (Isolation Forest)"

            report.append({
                'index': i,
                'start_time': start_time,
                'end_time': end_time,
                'probability': float(p),
                'cause': cause_str,
                'details': details
            })

        return report

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
