import logging
import numpy as np
from collections import Counter

logger = logging.getLogger("ML.FeatureExtractor")

# Lista interesujących identyfikatorów – można ją rozszerzać
INTERESTING_IDS = [
    0x0C00008F, 0x1CFF66F0, 0x0C000005, 0x14200032,
    0x0C00004C, 0x14044D4C, 0x10314D4C, 0x10B14D4C
]

def extract_features(frames):
    """
    Zamienia listę ramek (can_id, data, is_ext) na wektor cech.
    """
    if not frames:
        return np.zeros(len(INTERESTING_IDS) + 3)

    n = len(frames)
    ids = [f[0] for f in frames]
    data_lengths = [len(f[1]) for f in frames]
    is_ext = [1 if f[2] else 0 for f in frames]

    # Histogram interesujących ID
    id_counts = Counter(ids)
    id_features = [id_counts.get(iid, 0) / n for iid in INTERESTING_IDS]

    # Średnia długość danych
    avg_len = np.mean(data_lengths) if data_lengths else 0

    # Udział ramek rozszerzonych
    ext_ratio = np.mean(is_ext) if is_ext else 0

    # Liczba unikalnych ID
    unique_ids = len(set(ids)) / max(1, n)

    features = np.array(id_features + [avg_len, ext_ratio, unique_ids])
    return features
