#!/bin/bash
# update_F9b.sh – Faza 9b: Algorytm wyszukiwania sekwencji w kontrolerze
# Uruchom w katalogu can_simulator/

set -e

echo "=== Wdrażanie Fazy 9b: Algorytm sekwencji ==="

if [ ! -f controllers/associative_controller.py ]; then
    echo "BŁĄD: controllers/associative_controller.py nie istnieje."
    exit 1
fi

python3 << 'PYEOF'
with open("controllers/associative_controller.py", "r") as f:
    content = f.read()

# 1. Dodajemy metodę find_sequences
if "def find_sequences" not in content:
    new_method = '''
    def find_sequences(self, main_candidate, tolerance_ms=200):
        """
        Szuka powtarzalnych sekwencji wokół głównej ramki (main_candidate).
        Zwraca listę słowników z kluczami:
        - main_id, main_byte
        - ids_order: lista ID w kolejności występowania
        - avg_delays: średnie odstępy między ramkami
        - confidence: procent okien, w których sekwencja wystąpiła
        """
        margin = tolerance_ms / 1000.0
        main_id = main_candidate["id"]
        main_byte = main_candidate["byte"]

        # Zbierz wszystkie wystąpienia głównej ramki w buforze
        main_events = [ts for ts, rec in self.buffer if rec["arb_id"] == main_id]

        if len(main_events) < 3:
            logger.info("Za mało wystąpień głównej ramki do analizy sekwencji.")
            return []

        # Dla każdego wystąpienia znajdź sąsiadujące ID w oknie czasowym
        neighbor_stats = {}  # {arb_id: {"before": count, "after": count, "delays": []}}
        window_before = 0.5  # sekund przed
        window_after = 0.5   # sekund po

        for main_ts in main_events:
            # Znajdź ramki w oknie wokół main_ts
            for ts, rec in self.buffer:
                if rec["arb_id"] == main_id:
                    continue
                if (main_ts - window_before) <= ts <= main_ts:
                    # Ramka przed
                    nid = rec["arb_id"]
                    if nid not in neighbor_stats:
                        neighbor_stats[nid] = {"before": 0, "after": 0, "delays": []}
                    neighbor_stats[nid]["before"] += 1
                    neighbor_stats[nid]["delays"].append(main_ts - ts)
                elif main_ts < ts <= (main_ts + window_after):
                    # Ramka po
                    nid = rec["arb_id"]
                    if nid not in neighbor_stats:
                        neighbor_stats[nid] = {"before": 0, "after": 0, "delays": []}
                    neighbor_stats[nid]["after"] += 1
                    neighbor_stats[nid]["delays"].append(ts - main_ts)

        # Filtruj – tylko ID występujące w >80% okien
        threshold_ratio = 0.8
        total_windows = len(main_events)
        frequent_neighbors = []
        for arb_id, stats in neighbor_stats.items():
            max_occurrence = max(stats["before"], stats["after"])
            if max_occurrence / total_windows >= threshold_ratio:
                avg_delay = sum(stats["delays"]) / len(stats["delays"]) if stats["delays"] else 0
                direction = "before" if stats["before"] > stats["after"] else "after"
                frequent_neighbors.append({
                    "id": arb_id,
                    "direction": direction,
                    "avg_delay": avg_delay,
                    "occurrence_ratio": max_occurrence / total_windows
                })

        if not frequent_neighbors:
            return []

        # Buduj sekwencję: sortuj według avg_delay i kierunku
        before_ids = [n for n in frequent_neighbors if n["direction"] == "before"]
        after_ids = [n for n in frequent_neighbors if n["direction"] == "after"]

        before_ids.sort(key=lambda x: x["avg_delay"], reverse=True)  # najbliższe przed
        after_ids.sort(key=lambda x: x["avg_delay"])                # najbliższe po

        ids_order = [n["id"] for n in before_ids] + [main_id] + [n["id"] for n in after_ids]

        # Oblicz uśrednioną pewność sekwencji
        avg_confidence = sum(n["occurrence_ratio"] for n in frequent_neighbors) / len(frequent_neighbors) * 100

        sequence = [{
            "main_id": main_id,
            "main_byte": main_byte,
            "ids_order": ids_order,
            "neighbors": frequent_neighbors,
            "confidence": round(avg_confidence, 1),
            "source": "sekwencja"
        }]
        logger.info(f"Znaleziono sekwencję: {' -> '.join(hex(i) for i in ids_order)}")
        return sequence
'''
    # Wstawiamy przed get_highlight_ids
    if "def get_highlight_ids" in content:
        content = content.replace("    def get_highlight_ids", new_method + "\n    def get_highlight_ids")
    else:
        content += "\n" + new_method
    print("Dodano metodę find_sequences.")
else:
    print("Metoda find_sequences już istnieje.")

# 2. Rozszerzamy get_highlight_ids, aby uwzględniał ID z sekwencji
if "def get_highlight_ids" in content and "sequence" not in content:
    old_highlight = '''    def get_highlight_ids(self, threshold=80.0):
        """Zwraca listę ID, których pewność przekroczyła threshold."""
        ids = []
        for c in self.candidates:
            if c["confidence"] >= threshold:
                ids.append(c["id"])
        return list(set(ids))'''
    new_highlight = '''    def get_highlight_ids(self, threshold=80.0):
        """Zwraca listę ID do podświetlenia, w tym ID z sekwencji."""
        ids = []
        for c in self.candidates:
            if c["confidence"] >= threshold:
                ids.append(c["id"])
                # Jeśli kandydat ma sekwencję, dodaj wszystkie jej ID
                if "ids_order" in c:
                    ids.extend(c["ids_order"])
        return list(set(ids))'''
    content = content.replace(old_highlight, new_highlight)
    print("Rozszerzono get_highlight_ids o ID z sekwencji.")
else:
    print("get_highlight_ids już zawiera obsługę sekwencji lub nie istnieje.")

with open("controllers/associative_controller.py", "w") as f:
    f.write(content)
print("Zapisano zmiany w associative_controller.py.")
PYEOF

python3 -m py_compile controllers/associative_controller.py && echo "  controller OK" || echo "  controller BŁĄD"

echo ""
echo "=== Faza 9b zakończona ==="
echo "Uruchom update_F9c.sh"
