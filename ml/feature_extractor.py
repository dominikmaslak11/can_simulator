import logging
import numpy as np
import math
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
    Zwraca wektor o długości len(INTERESTING_IDS) + 4:
        - znormalizowane częstości interesujących ID
        - średnia długość danych
        - udział ramek rozszerzonych
        - liczba unikalnych ID (znormalizowana)
        - entropia bajtów (Shannon)
    """
    if not frames:
        return np.zeros(len(INTERESTING_IDS) + 4)

    n = len(frames)
    ids = [f[0] for f in frames]
    data_lengths = [len(f[1]) for f in frames]
    is_ext = [1 if f[2] else 0 for f in frames]

    # 1. Histogram interesujących ID (znormalizowany)
    id_counts = Counter(ids)
    id_features = [id_counts.get(iid, 0) / n for iid in INTERESTING_IDS]

    # 2. Średnia długość danych
    avg_len = np.mean(data_lengths) if data_lengths else 0.0

    # 3. Udział ramek rozszerzonych
    ext_ratio = np.mean(is_ext) if is_ext else 0.0

    # 4. Liczba unikalnych ID (znormalizowana)
    unique_ids = len(set(ids)) / max(1, n)

    # 5. Entropia bajtów (Shannon)
    byte_counter = Counter()
    for f in frames:
        byte_counter.update(f[1])
    total_bytes = sum(byte_counter.values())
    entropy = 0.0
    if total_bytes > 0:
        for count in byte_counter.values():
            p = count / total_bytes
            entropy -= p * math.log2(p)

    features = np.array(id_features + [avg_len, ext_ratio, unique_ids, entropy])
    return features
