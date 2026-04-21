import os
import logging
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

logger = logging.getLogger("ML.SequentialModel")

class LSTMModel(nn.Module):
    def __init__(self, input_dim=3, hidden_dim=64, num_layers=2, dropout=0.3):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers,
                            batch_first=True, bidirectional=True, dropout=dropout)
        self.fc = nn.Linear(hidden_dim * 2, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        # x: (batch, seq_len, input_dim)
        lstm_out, _ = self.lstm(x)
        # bierzemy ostatni krok czasowy
        last_out = lstm_out[:, -1, :]
        out = self.fc(last_out)
        return self.sigmoid(out)

class SequentialMLModel:
    def __init__(self, model_path="sequential_model.pth"):
        self.model_path = model_path
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._init_model()
        self.X = []   # lista sekwencji (np.array)
        self.y = []   # etykiety
        self.load()

    def _init_model(self):
        self.model = LSTMModel().to(self.device)
        self.optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        self.criterion = nn.BCELoss()

    def predict_proba(self, seq_features):
        """
        seq_features: np.array o kształcie (MAX_SEQ_LEN, 3)
        Zwraca prawdopodobieństwo (float).
        """
        if self.model is None:
            return 0.5
        self.model.eval()
        with torch.no_grad():
            x = torch.tensor(seq_features, dtype=torch.float32).unsqueeze(0).to(self.device)
            proba = self.model(x).item()
        return proba

    def add_sample(self, seq_features, label):
        self.X.append(seq_features)
        self.y.append(float(label))

    def train(self):
        if len(self.X) < 2:
            return
        logger.info("Rozpoczynanie trenowania modelu LSTM...")
        self.model.train()
        X_tensor = torch.tensor(np.array(self.X), dtype=torch.float32).to(self.device)
        y_tensor = torch.tensor(self.y, dtype=torch.float32).unsqueeze(1).to(self.device)

        dataset = torch.utils.data.TensorDataset(X_tensor, y_tensor)
        loader = torch.utils.data.DataLoader(dataset, batch_size=8, shuffle=True)

        epochs = 20
        for epoch in range(epochs):
            total_loss = 0.0
            for batch_x, batch_y in loader:
                self.optimizer.zero_grad()
                outputs = self.model(batch_x)
                loss = self.criterion(outputs, batch_y)
                loss.backward()
                self.optimizer.step()
                total_loss += loss.item()
            if (epoch+1) % 5 == 0:
                logger.debug(f"Epoch {epoch+1}/{epochs}, loss: {total_loss/len(loader):.4f}")

        self.save()
        logger.info("Model LSTM wytrenowany i zapisany.")

    def save(self):
        try:
            torch.save({
                'model_state': self.model.state_dict(),
                'optimizer_state': self.optimizer.state_dict(),
                'X': self.X,
                'y': self.y
            }, self.model_path)
        except Exception as e:
            logger.error(f"Błąd zapisu modelu: {e}")

    def load(self):
        if os.path.exists(self.model_path):
            try:
                checkpoint = torch.load(self.model_path, map_location=self.device)
                self.model.load_state_dict(checkpoint['model_state'])
                self.optimizer.load_state_dict(checkpoint['optimizer_state'])
                self.X = checkpoint.get('X', [])
                self.y = checkpoint.get('y', [])
                logger.info(f"Wczytano model LSTM z {self.model_path}")
            except Exception as e:
                logger.error(f"Błąd wczytywania modelu: {e}")
                self._init_model()
        else:
            logger.info("Brak zapisanego modelu LSTM – inicjalizacja nowego.")
