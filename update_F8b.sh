#!/bin/bash
# update_F8b.sh – Faza 8b: Rozbudowa kontrolera o korelację wartościową
# Uruchom w katalogu can_simulator/

set -e

echo "=== Wdrażanie Fazy 8b: Kontroler – korelacja wartościowa ==="

if [ ! -f controllers/associative_controller.py ]; then
    echo "BŁĄD: controllers/associative_controller.py nie istnieje."
    exit 1
fi

python3 << 'PYEOF'
with open("controllers/associative_controller.py", "r") as f:
    content = f.read()

# -------------------------------------------
# 1. Dodaj atrybuty value_* w __init__
# -------------------------------------------
if "self.value_history" not in content:
    old_init_end = "self.classifier = PassiveAggressiveClassifier(warm_start=True, random_state=42)"
    new_attrs = '''
        # Tryb wartościowy
        self.value_history = []          # lista zatwierdzonych wartości (float)
        self.value_timestamps = []       # odpowiadające im timestampy
        self.value_labels = []           # etykiety dla bufora (słownik timestamp->wartość)
'''
    content = content.replace(old_init_end, old_init_end + new_attrs)
    print("Dodano atrybuty trybu wartościowego.")
else:
    print("Atrybuty trybu wartościowego już istnieją.")

# -------------------------------------------
# 2. Dodaj metody commit_value, undo_last_value, get_value_history
# -------------------------------------------
if "def commit_value" not in content:
    new_methods = '''
    def commit_value(self, value: float):
        """Rejestruje wartość referencyjną z bieżącym timestampem."""
        now = time.time()
        self.value_history.append(value)
        self.value_timestamps.append(now)
        # Oznacz ramki w buforze w oknie tolerancji
        margin = self.tolerance_ms / 1000.0
        for ts, rec in self.buffer:
            if (now - margin) <= ts <= (now + margin):
                rec_id = id(rec)
                self.value_labels.append((ts, rec, value))
        logger.info(f"Zarejestrowano wartość {value} (historia: {len(self.value_history)})")

    def undo_last_value(self):
        """Usuwa ostatnią zatwierdzoną wartość."""
        if not self.value_history:
            return
        removed = self.value_history.pop()
        self.value_timestamps.pop()
        # Usuń odpowiadające etykiety
        cutoff = self.value_timestamps[-1] if self.value_timestamps else 0
        self.value_labels = [(ts, rec, v) for ts, rec, v in self.value_labels if ts <= cutoff]
        logger.info(f"Cofnięto wartość {removed}")

    def get_value_history(self):
        return list(self.value_history)
'''
    # Wstawiamy przed get_highlight_ids
    if "def get_highlight_ids" in content:
        content = content.replace("    def get_highlight_ids", new_methods + "\n    def get_highlight_ids")
    else:
        content += "\n" + new_methods
    print("Dodano metody commit_value, undo_last_value, get_value_history.")
else:
    print("Metody trybu wartościowego już istnieją.")

# -------------------------------------------
# 3. Dodaj metodę _analyze_value_correlation
# -------------------------------------------
if "def _analyze_value_correlation" not in content:
    corr_method = '''
    def _analyze_value_correlation(self):
        """Analizuje korelację między wartościami bajtów a wartością referencyjną."""
        if len(self.value_history) < 3:
            return []   # za mało danych

        candidates = []
        margin = self.tolerance_ms / 1000.0

        # Dla każdego unikalnego ID w buforze
        for arb_id in set(rec["arb_id"] for _, rec in self.buffer):
            # Zbierz próbki: dla każdej zarejestrowanej wartości znajdź średnią bajtu w oknie
            byte_samples = {i: [] for i in range(8)}
            ref_values = []

            for ref_ts, ref_val in zip(self.value_timestamps, self.value_history):
                frame_slice = [rec for ts, rec in self.buffer
                               if rec["arb_id"] == arb_id
                               and (ref_ts - margin) <= ts <= (ref_ts + margin)]
                if not frame_slice:
                    continue
                # Dla każdego bajtu weź średnią z okna
                avg_data = [0] * 8
                for rec in frame_slice:
                    for i, b in enumerate(rec["data"]):
                        avg_data[i] += b
                for i in range(8):
                    avg_data[i] /= len(frame_slice)
                for i in range(8):
                    byte_samples[i].append(avg_data[i])
                ref_values.append(ref_val)

            if len(ref_values) < 3:
                continue

            # Oblicz korelację Pearsona dla każdego bajtu
            for byte_idx in range(8):
                x = ref_values
                y = byte_samples[byte_idx]
                if len(set(y)) < 2:   # bajt się nie zmienia
                    continue
                r = self._pearson_correlation(x, y)
                if r is None:
                    continue
                abs_r = abs(r)
                if abs_r >= 0.8:   # próg korelacji
                    candidates.append({
                        "id": arb_id,
                        "byte": byte_idx,
                        "value": round(np.mean(y)),
                        "background": None,
                        "pos_count": len(x),
                        "neg_count": 0,
                        "confidence": round(abs_r * 100, 1),
                        "source": "wartosc" if not self.iteration_count else "wartosc"
                    })

        candidates.sort(key=lambda c: c["confidence"], reverse=True)
        return candidates

    @staticmethod
    def _pearson_correlation(x, y):
        """Oblicza współczynnik korelacji Pearsona."""
        n = len(x)
        if n < 3:
            return None
        import math
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        num = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        den_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
        den_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))
        if den_x == 0 or den_y == 0:
            return None
        return num / (den_x * den_y)
'''
    # Wstawiamy przed _analyze lub na końcu
    if "def _analyze(self):" in content:
        content = content.replace("    def _analyze(self):", corr_method + "\n    def _analyze(self):")
    else:
        content += "\n" + corr_method
    print("Dodano metodę _analyze_value_correlation i _pearson_correlation.")
else:
    print("Metody korelacji już istnieją.")

# -------------------------------------------
# 4. Modyfikuj _analyze, aby łączyła wyniki obu trybów
# -------------------------------------------
if "wartosciowi = self._analyze_value_correlation()" not in content:
    old_analyze_end = "candidates.sort(key=lambda x: x[\"confidence\"], reverse=True)"
    new_analyze = '''        # Dodaj wyniki z trybu wartościowego
        wartosciowi = self._analyze_value_correlation()
        candidates.extend(wartosciowi)

        candidates.sort(key=lambda x: x["confidence"], reverse=True)'''
    content = content.replace(old_analyze_end, new_analyze)
    print("Zaktualizowano _analyze o łączenie wyników obu trybów.")
else:
    print("_analyze już łączy wyniki obu trybów.")

# -------------------------------------------
# 5. Import math na górze pliku (jeśli brak)
# -------------------------------------------
if "import math" not in content:
    content = content.replace("import time\n", "import time\nimport math\n")
    print("Dodano import math.")

with open("controllers/associative_controller.py", "w") as f:
    f.write(content)

print("Zapisano zmiany w associative_controller.py.")
PYEOF

python3 -m py_compile controllers/associative_controller.py && echo "  associative_controller.py OK" || echo "  associative_controller.py BŁĄD"

echo ""
echo "=== Faza 8b zakończona ==="
echo "Uruchom: update_F8c.sh"
