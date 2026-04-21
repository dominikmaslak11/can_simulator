import logging
from collections import defaultdict
from sequence_matcher import find_common_pattern

logger = logging.getLogger("SequenceAnalyzer")


class SequenceAnalyzer:
    def __init__(self, time_window=0.5, tolerance_bytes=None):
        self.time_window = time_window
        self.tolerance_bytes = tolerance_bytes  # np. [0, 2] – ignoruj bajty 0 i 2
        self.sequences = []
        self.sequence_hashes = defaultdict(int)

    def add_candidates(self, candidates):
        if not candidates:
            return
        sorted_cands = sorted(candidates, key=lambda x: x[3])
        seq = []
        last_ts = None
        for cand in sorted_cands:
            cid, data, is_ext, ts = cand
            if last_ts is None or (ts - last_ts) <= self.time_window:
                seq.append(cand)
            else:
                if seq:
                    self._add_sequence(seq)
                seq = [cand]
            last_ts = ts
        if seq:
            self._add_sequence(seq)

    def _add_sequence(self, seq):
        self.sequences.append(seq)
        hash_key = tuple((cid, data.hex(), is_ext) for cid, data, is_ext, _ in seq)
        self.sequence_hashes[hash_key] += 1

    def get_top_sequences(self, top_n=5):
        sorted_seqs = sorted(self.sequence_hashes.items(), key=lambda x: x[1], reverse=True)
        result = []
        for hash_key, count in sorted_seqs[:top_n]:
            seq = [(cid, bytes.fromhex(data_hex), is_ext) for cid, data_hex, is_ext in hash_key]
            result.append((seq, count))
        return result

    def find_pattern_across_sessions(self, min_support=2):
        """
        Znajduje wzorzec występujący w co najmniej `min_support` różnych sesjach.
        """
        if len(self.sequences) < min_support:
            return []
        # Konwersja do listy list (bez timestampów)
        all_seqs = [[(cid, data, is_ext) for cid, data, is_ext, _ in seq] for seq in self.sequences]
        pattern = find_common_pattern(all_seqs, tolerance_bytes=self.tolerance_bytes)
        return pattern

    def clear(self):
        self.sequences.clear()
        self.sequence_hashes.clear()
