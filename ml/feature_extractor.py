import numpy as np
import logging
from collections import Counter

logger = logging.getLogger("ML.FeatureExtractor")

# Lista "interesujących" identyfikatorów – dla starego modelu
INTERESTING_IDS = [
    0x0C00008F, 0x1CFF66F0, 0x0C000005, 0x14200032,
    0x0C00004C, 0x14044D4C, 0x10314D4C, 0x10B14D4C
]

# Maksymalna długość sekwencji dla modelu LSTM
MAX_SEQ_LEN = 100


# ============================
# STARY MODEL (regresja logistyczna)
# ============================
def extract_features(frames):
    """
    Zamienia listę ramek na wektor cech statystycznych.
    Używane przez model regresji logistycznej.
    """
    if not frames:
        return np.zeros(len(INTERESTING_IDS) + 3)

    n = len(frames)
    ids = [f[0] for f in frames]
    data_lengths = [len(f[1]) for f in frames]
    is_ext = [1 if f[2] else 0 for f in frames]

    id_counts = Counter(ids)
    id_features = [id_counts.get(iid, 0) / n for iid in INTERESTING_IDS]

    avg_len = np.mean(data_lengths) if data_lengths else 0
    ext_ratio = np.mean(is_ext) if is_ext else 0
    unique_ids = len(set(ids)) / max(1, n)

    features = np.array(id_features + [avg_len, ext_ratio, unique_ids])
    return features


# ============================
# NOWY MODEL (LSTM)
# ============================
def frame_to_vector(frame):
    """
    Zamienia pojedynczą ramkę na wektor cech dla modelu LSTM.
    """
    can_id, data, is_ext, _ = frame
    norm_id = can_id / 0x1FFFFFFF
    data_len = len(data) / 8.0
    ext_flag = 1.0 if is_ext else 0.0
    return np.array([norm_id, data_len, ext_flag], dtype=np.float32)


def extract_sequential_features(frames):
    """
    Tworzy sekwencję wektorów cech o stałej długości MAX_SEQ_LEN.
    Używane przez model LSTM.
    """
    if not frames:
        return np.zeros((MAX_SEQ_LEN, 3), dtype=np.float32)

    seq = np.array([frame_to_vector(f) for f in frames], dtype=np.float32)
    n = len(seq)

    if n >= MAX_SEQ_LEN:
        indices = np.linspace(0, n - 1, MAX_SEQ_LEN, dtype=int)
        return seq[indices]
    else:
        padded = np.zeros((MAX_SEQ_LEN, 3), dtype=np.float32)
        padded[-n:] = seq
        return padded
