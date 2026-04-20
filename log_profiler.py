import numpy as np
from collections import Counter


class LogProfiler:
    """Analizuje listę ramek CAN i generuje statystyki."""

    def __init__(self, frames):
        """
        :param frames: lista ramek w formacie (can_id, data, is_extended)
        """
        self.frames = frames
        self.total = len(frames)

    def get_summary(self):
        """Podstawowe informacje o logu."""
        return {
            "total_frames": self.total,
            "unique_ids": len(set(f[0] for f in self.frames)),
            "extended_ratio": sum(1 for f in self.frames if f[2]) / max(1, self.total),
        }

    def get_top_ids(self, top_n=15):
        """Zwraca listę najczęściej występujących identyfikatorów."""
        counter = Counter(f[0] for f in self.frames)
        return counter.most_common(top_n)

    def get_data_length_stats(self):
        """Statystyki długości danych (DLC)."""
        lengths = [len(f[1]) for f in self.frames]
        if not lengths:
            return {"min": 0, "max": 0, "avg": 0.0, "std": 0.0}
        return {
            "min": min(lengths),
            "max": max(lengths),
            "avg": float(np.mean(lengths)),
            "std": float(np.std(lengths)),
        }

    def generate_report(self):
        """Tworzy tekstowy raport do wyświetlenia."""
        summary = self.get_summary()
        top_ids = self.get_top_ids(15)
        data_stats = self.get_data_length_stats()

        lines = []
        lines.append("=== PROFIL LOGU CAN ===")
        lines.append("")
        lines.append(f"Liczba ramek: {summary['total_frames']}")
        lines.append(f"Unikalne identyfikatory: {summary['unique_ids']}")
        lines.append(f"Udział ramek rozszerzonych: {summary['extended_ratio']:.1%}")
        lines.append("")
        lines.append("Najczęstsze identyfikatory:")
        for i, (cid, count) in enumerate(top_ids, 1):
            ext_str = "EXT" if cid > 0x7FF else "STD"
            pct = count / summary['total_frames'] * 100
            lines.append(f"  {i:2d}. 0x{cid:08X} ({ext_str}) – {count:6d} razy ({pct:5.1f}%)")
        lines.append("")
        lines.append("Długości danych (DLC):")
        lines.append(f"  Minimalna: {data_stats['min']}")
        lines.append(f"  Maksymalna: {data_stats['max']}")
        lines.append(f"  Średnia:   {data_stats['avg']:.2f}")
        lines.append(f"  Odchylenie: {data_stats['std']:.2f}")

        return "\n".join(lines)
