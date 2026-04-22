import numpy as np
import logging
import os

logger = logging.getLogger("ML.Advanced")

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch nie jest dostępny – prognozowanie LSTM wyłączone.")


class SignalLSTM(nn.Module):
    def __init__(self, input_size=1, hidden_size=64, num_layers=2, output_size=1):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.fc(out[:, -1, :])
        return out


class SignalForecaster:
    def __init__(self, model_path="signal_forecaster.pth"):
        self.model_path = model_path
        self.model = None
        self.scaler = None
        self.seq_length = 20
        if TORCH_AVAILABLE:
            self.model = SignalLSTM()

    def _create_sequences(self, data, seq_length):
        X, y = [], []
        for i in range(len(data) - seq_length):
            X.append(data[i:i+seq_length])
            y.append(data[i+seq_length])
        return np.array(X), np.array(y)

    def train(self, signal_values, epochs=50):
        if not TORCH_AVAILABLE:
            logger.error("PyTorch niedostępny.")
            return False
        if len(signal_values) < self.seq_length + 10:
            logger.warning("Zbyt mało danych do trenowania.")
            return False

        from sklearn.preprocessing import MinMaxScaler
        self.scaler = MinMaxScaler()
        scaled = self.scaler.fit_transform(np.array(signal_values).reshape(-1, 1)).flatten()

        X, y = self._create_sequences(scaled, self.seq_length)
        X_tensor = torch.tensor(X, dtype=torch.float32).unsqueeze(-1)
        y_tensor = torch.tensor(y, dtype=torch.float32).unsqueeze(-1)

        self.model = SignalLSTM()
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        criterion = nn.MSELoss()

        self.model.train()
        for epoch in range(epochs):
            optimizer.zero_grad()
            outputs = self.model(X_tensor)
            loss = criterion(outputs, y_tensor)
            loss.backward()
            optimizer.step()
        self.model.eval()
        torch.save({
            'model_state': self.model.state_dict(),
            'scaler': self.scaler,
            'seq_length': self.seq_length
        }, self.model_path)
        logger.info("Model LSTM wytrenowany.")
        return True

    def forecast(self, signal_values, steps=50):
        if not TORCH_AVAILABLE or self.model is None:
            return []
        if self.scaler is None:
            return []
        scaled = self.scaler.transform(np.array(signal_values).reshape(-1, 1)).flatten()
        if len(scaled) < self.seq_length:
            return []

        self.model.eval()
        current_seq = scaled[-self.seq_length:].copy()
        predictions = []
        with torch.no_grad():
            for _ in range(steps):
                inp = torch.tensor(current_seq, dtype=torch.float32).unsqueeze(0).unsqueeze(-1)
                pred = self.model(inp).item()
                predictions.append(pred)
                current_seq = np.append(current_seq[1:], pred)
        return self.scaler.inverse_transform(np.array(predictions).reshape(-1, 1)).flatten().tolist()

    def load(self):
        if not TORCH_AVAILABLE or not os.path.exists(self.model_path):
            return False
        checkpoint = torch.load(self.model_path)
        self.seq_length = checkpoint.get('seq_length', 20)
        self.model = SignalLSTM()
        self.model.load_state_dict(checkpoint['model_state'])
        self.scaler = checkpoint['scaler']
        self.model.eval()
        return True
