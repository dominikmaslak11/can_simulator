import os
import logging
import numpy as np
import pickle

logger = logging.getLogger("ML.PatternDetector")

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch nie jest dostępny – autoenkoder nie będzie działał.")


class Autoencoder(nn.Module):
    def __init__(self, input_dim, encoding_dim=16):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, encoding_dim)
        )
        self.decoder = nn.Sequential(
            nn.Linear(encoding_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 64),
            nn.ReLU(),
            nn.Linear(64, input_dim),
            nn.Sigmoid()
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded


class PatternDetector:
    def __init__(self, model_path="pattern_detector.pth"):
        self.model_path = model_path
        self.model = None
        self.input_dim = 20  # liczba cech na okno (dostosowana w razie potrzeby)
        self.threshold = None
        if TORCH_AVAILABLE:
            self.model = Autoencoder(self.input_dim)
        self.scaler = None

    def _extract_sequence_features(self, frames, window_size=10):
        """Tworzy wektory cech dla kolejnych okien przesuwnych."""
        if len(frames) < window_size:
            return np.array([])
        features = []
        for i in range(len(frames) - window_size + 1):
            window = frames[i:i+window_size]
            ids = [f[0] for f in window]
            data_lens = [len(f[1]) for f in window]
            is_ext = [1 if f[2] else 0 for f in window]
            timestamps = [f[3] for f in window if f[3] is not None]
            feats = [
                len(set(ids)) / window_size,
                np.mean(ids) if ids else 0,
                np.std(ids) if len(ids) > 1 else 0,
                np.mean(data_lens),
                np.mean(is_ext),
            ]
            if len(timestamps) > 1:
                diffs = np.diff(sorted(timestamps))
                feats.extend([np.mean(diffs), np.std(diffs)])
            else:
                feats.extend([0, 0])
            # Padding/obcięcie do stałego wymiaru
            if len(feats) < self.input_dim:
                feats.extend([0] * (self.input_dim - len(feats)))
            else:
                feats = feats[:self.input_dim]
            features.append(feats)
        return np.array(features, dtype=np.float32)

    def train(self, normal_frames):
        if not TORCH_AVAILABLE:
            logger.error("PyTorch niedostępny – nie można trenować autoenkodera.")
            return False
        X = self._extract_sequence_features(normal_frames)
        if len(X) == 0:
            logger.warning("Zbyt mało danych do trenowania.")
            return False

        # Normalizacja
        from sklearn.preprocessing import StandardScaler
        self.scaler = StandardScaler()
        X = self.scaler.fit_transform(X)

        X_tensor = torch.tensor(X, dtype=torch.float32)
        dataset = torch.utils.data.TensorDataset(X_tensor)
        loader = torch.utils.data.DataLoader(dataset, batch_size=32, shuffle=True)

        self.model = Autoencoder(self.input_dim)
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        criterion = nn.MSELoss()

        self.model.train()
        for epoch in range(50):
            total_loss = 0.0
            for batch in loader:
                optimizer.zero_grad()
                x = batch[0]
                reconstructed = self.model(x)
                loss = criterion(reconstructed, x)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            if (epoch+1) % 10 == 0:
                logger.debug(f"Epoch {epoch+1}, loss: {total_loss/len(loader):.4f}")

        # Oblicz próg na podstawie błędów rekonstrukcji
        self.model.eval()
        with torch.no_grad():
            reconstructed = self.model(X_tensor)
            errors = torch.mean((X_tensor - reconstructed) ** 2, dim=1).numpy()
            self.threshold = np.percentile(errors, 95)  # 95 percentyl jako próg anomalii
            logger.info(f"Próg rekonstrukcji: {self.threshold:.4f}")

        self._save_model()
        logger.info("Autoenkoder wytrenowany.")
        return True

    def detect_anomalies(self, frames):
        if not TORCH_AVAILABLE or self.model is None or self.scaler is None:
            return [], []
        X = self._extract_sequence_features(frames)
        if len(X) == 0:
            return [], []
        X = self.scaler.transform(X)
        X_tensor = torch.tensor(X, dtype=torch.float32)
        self.model.eval()
        with torch.no_grad():
            reconstructed = self.model(X_tensor)
            errors = torch.mean((X_tensor - reconstructed) ** 2, dim=1).numpy()

        # Znajdź okna, w których błąd przekracza próg
        anomalous_windows = []
        window_size = 10
        for i, err in enumerate(errors):
            if err > self.threshold:
                start_idx = i
                end_idx = i + window_size - 1
                if start_idx < len(frames) and end_idx < len(frames):
                    anomalous_windows.append({
                        'start': start_idx,
                        'end': end_idx,
                        'error': float(err)
                    })
        return errors, anomalous_windows

    def _save_model(self):
        if self.model is None:
            return
        torch.save({
            'model_state': self.model.state_dict(),
            'input_dim': self.input_dim,
            'threshold': self.threshold,
            'scaler': self.scaler
        }, self.model_path)

    def load_model(self):
        if not TORCH_AVAILABLE or not os.path.exists(self.model_path):
            return False
        checkpoint = torch.load(self.model_path)
        self.input_dim = checkpoint['input_dim']
        self.model = Autoencoder(self.input_dim)
        self.model.load_state_dict(checkpoint['model_state'])
        self.threshold = checkpoint['threshold']
        self.scaler = checkpoint['scaler']
        self.model.eval()
        return True

    def get_anomalous_windows(self, frames, errors, threshold):
        """Zwraca listę okien (start_idx, end_idx, start_time, end_time) dla anomalii."""
        window_size = 10
        windows = []
        for i, err in enumerate(errors):
            if err > threshold:
                start_idx = i
                end_idx = min(i + window_size - 1, len(frames) - 1)
                if start_idx < len(frames) and end_idx < len(frames):
                    start_time = frames[start_idx][3] if frames[start_idx][3] is not None else 0
                    end_time = frames[end_idx][3] if frames[end_idx][3] is not None else 0
                    windows.append({
                        'start_idx': start_idx,
                        'end_idx': end_idx,
                        'start_time': start_time,
                        'end_time': end_time,
                        'error': float(err)
                    })
        return windows

    def diagnose_window(self, normal_frames, window_frames):
        """Porównuje okno anomalne z normalnym logiem i zwraca listę przyczyn."""
        causes = []
        # Statystyki z normalnego logu
        normal_ids = {}
        for f in normal_frames:
            cid = f[0]
            normal_ids.setdefault(cid, []).append(f)

        normal_stats = {}
        for cid, frames in normal_ids.items():
            if len(frames) < 2:
                continue
            timestamps = [f[3] for f in frames if f[3] is not None]
            if len(timestamps) < 2:
                continue
            diffs = np.diff(sorted(timestamps))
            normal_stats[cid] = {
                'count': len(frames),
                'avg_interval': np.mean(diffs),
                'std_interval': np.std(diffs)
            }

        # Statystyki okna
        window_ids = {}
        for f in window_frames:
            cid = f[0]
            window_ids.setdefault(cid, []).append(f)

        # 1. Brakujące ID
        missing = set(normal_stats.keys()) - set(window_ids.keys())
        if missing:
            causes.append(f"Brakujące ID: {', '.join(hex(c) for c in list(missing)[:3])}")

        # 2. Zmiana częstotliwości
        for cid, frames in window_ids.items():
            if cid not in normal_stats or len(frames) < 2:
                continue
            timestamps = [f[3] for f in frames if f[3] is not None]
            if len(timestamps) < 2:
                continue
            diffs = np.diff(sorted(timestamps))
            avg = np.mean(diffs)
            norm = normal_stats[cid]
            if abs(avg - norm['avg_interval']) > 2 * norm['std_interval']:
                causes.append(f"{hex(cid)}: zmiana częstotliwości ({avg:.3f}s vs {norm['avg_interval']:.3f}s)")

        # 3. Ogólna liczba ramek
        normal_total = sum(s['count'] for s in normal_stats.values())
        window_total = len(window_frames)
        if normal_total > 0:
            ratio = window_total / normal_total
            if ratio < 0.5:
                causes.append(f"Mało ramek: {window_total} (norma ~{normal_total})")
            elif ratio > 2.0:
                causes.append(f"Dużo ramek: {window_total} (norma ~{normal_total})")

        if not causes:
            causes.append("Odchylenie wzorca (autoenkoder)")
        return causes
