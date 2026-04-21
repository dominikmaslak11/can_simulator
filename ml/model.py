import os
import pickle
import logging
import numpy as np

logger = logging.getLogger("ML.Model")

# Próbujemy zaimportować XGBoost, jeśli nie ma – fallback do regresji logistycznej
try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False
    logger.warning("XGBoost nie jest dostępny – używam regresji logistycznej (fallback)")

# Niezależnie od XGBoost, scikit-learn jest potrzebny do skalowania i fallbacku
try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn nie jest dostępny – ML wyłączone")


class MLModel:
    def __init__(self, model_path="ml_model.pkl"):
        self.model_path = model_path
        self.pipeline = None          # Dla XGBoost: pipeline ze StandardScaler + XGBClassifier
        self.X = []                   # cechy przedziałów
        self.y = []                   # etykiety
        self.use_xgboost = XGB_AVAILABLE
        if SKLEARN_AVAILABLE:
            self.load()

    def _build_pipeline(self):
        """Tworzy pipeline z wybranym klasyfikatorem."""
        if self.use_xgboost:
            model = xgb.XGBClassifier(
                objective='binary:logistic',
                eval_metric='logloss',
                use_label_encoder=False,
                verbosity=0
            )
        else:
            model = LogisticRegression(class_weight='balanced', max_iter=1000)
        return make_pipeline(StandardScaler(), model)

    def predict_proba(self, features):
        """Zwraca prawdopodobieństwo, że przedział zawiera granicę."""
        if not SKLEARN_AVAILABLE or self.pipeline is None:
            return 0.5
        try:
            proba = self.pipeline.predict_proba([features])[0]
            return proba[1] if len(proba) > 1 else 0.5
        except Exception as e:
            logger.error(f"Błąd predykcji: {e}")
            return 0.5

    def add_sample(self, features, label):
        if SKLEARN_AVAILABLE:
            self.X.append(features)
            self.y.append(label)

    def add_verified_sample(self, features, label, weight=3.0):
        """Dodaje próbkę ze zwiększoną wagą (zweryfikowaną przez użytkownika)."""
        if not SKLEARN_AVAILABLE:
            return
        repeat = max(1, int(weight))
        for _ in range(repeat):
            self.X.append(features)
            self.y.append(label)
        logger.info(f"Dodano zweryfikowaną próbkę z wagą {weight} (label={label})")

    def train(self):
        if not SKLEARN_AVAILABLE or len(self.X) < 2:
            return
        try:
            X = np.array(self.X)
            y = np.array(self.y)
            self.pipeline = self._build_pipeline()
            self.pipeline.fit(X, y)
            self.save()
            model_type = "XGBoost" if self.use_xgboost else "regresja logistyczna"
            logger.info(f"Model wytrenowany ({model_type})")
        except Exception as e:
            logger.error(f"Błąd trenowania modelu: {e}")

    def save(self):
        try:
            with open(self.model_path, 'wb') as f:
                pickle.dump({
                    'pipeline': self.pipeline,
                    'X': self.X,
                    'y': self.y,
                    'use_xgboost': self.use_xgboost
                }, f)
        except Exception as e:
            logger.error(f"Błąd zapisu modelu: {e}")

    def load(self):
        if not SKLEARN_AVAILABLE:
            return
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    data = pickle.load(f)
                self.pipeline = data.get('pipeline')
                self.X = data.get('X', [])
                self.y = data.get('y', [])
                saved_use_xgb = data.get('use_xgboost', False)
                if saved_use_xgb and not XGB_AVAILABLE:
                    logger.warning("Zapisany model używa XGBoost, który nie jest dostępny. Model nie zostanie wczytany.")
                    self.pipeline = None
                else:
                    self.use_xgboost = saved_use_xgb
                logger.info(f"Wczytano model z {self.model_path}")
            except Exception as e:
                logger.error(f"Błąd wczytywania modelu: {e}")
                self.pipeline = None
        else:
            self.pipeline = None
