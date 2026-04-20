import os
import pickle
import logging
import numpy as np

logger = logging.getLogger("ML.Model")

try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger.warning("scikit-learn nie jest dostępny – ML wyłączone")

class MLModel:
    def __init__(self, model_path="ml_model.pkl"):
        self.model_path = model_path
        self.pipeline = None
        self.X = []   # cechy przedziałów
        self.y = []   # etykiety: 1 = granica w przedziale, 0 = brak
        if ML_AVAILABLE:
            self.load()

    def _build_pipeline(self):
        return make_pipeline(StandardScaler(), LogisticRegression(class_weight='balanced', max_iter=1000))

    def predict_proba(self, features):
        """Zwraca prawdopodobieństwo, że przedział zawiera granicę."""
        if not ML_AVAILABLE or self.pipeline is None or not hasattr(self.pipeline, 'predict_proba'):
            return 0.5  # domyślnie
        try:
            proba = self.pipeline.predict_proba([features])[0]
            return proba[1] if len(proba) > 1 else 0.5
        except Exception as e:
            logger.error(f"Błąd predykcji: {e}")
            return 0.5

    def add_sample(self, features, label):
        if ML_AVAILABLE:
            self.X.append(features)
            self.y.append(label)

    def train(self):
        if not ML_AVAILABLE or len(self.X) < 2:
            return
        try:
            X = np.array(self.X)
            y = np.array(self.y)
            self.pipeline = self._build_pipeline()
            self.pipeline.fit(X, y)
            self.save()
            logger.info("Model wytrenowany")
        except Exception as e:
            logger.error(f"Błąd trenowania modelu: {e}")

    def save(self):
        try:
            with open(self.model_path, 'wb') as f:
                pickle.dump({'pipeline': self.pipeline, 'X': self.X, 'y': self.y}, f)
        except Exception as e:
            logger.error(f"Błąd zapisu modelu: {e}")

    def load(self):
        if not ML_AVAILABLE:
            return
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    data = pickle.load(f)
                self.pipeline = data.get('pipeline')
                self.X = data.get('X', [])
                self.y = data.get('y', [])
                logger.info(f"Wczytano model z {self.model_path}")
            except Exception as e:
                logger.error(f"Błąd wczytywania modelu: {e}")
                self.pipeline = None
        else:
            self.pipeline = None
