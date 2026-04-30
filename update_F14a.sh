#!/bin/bash
# update_F14a.sh – Faza 14a: Kontroler asocjacji J1939
# Uruchom w katalogu can_simulator/

set -e

echo "=== Wdrażanie Fazy 14a: J1939AssociativeController ==="

# ---------- 1. Nowy kontroler ----------
mkdir -p controllers

cat > controllers/j1939_associative_controller.py << 'CONTROLLER_EOF'
"""Kontroler asocjacji z obsługą J1939 – dziedziczy po AssociativeController."""
import logging
import numpy as np
from controllers.associative_controller import AssociativeController
from parsers_j1939 import parse_j1939_id

logger = logging.getLogger("J1939AssociativeController")


class J1939AssociativeController(AssociativeController):
    """
    Rozszerza AssociativeController o analizę specyficzną dla J1939:
    - zamiana surowego arb_id na PGN w wynikach,
    - dodawanie adresu źródłowego (source_address),
    - uzupełnianie nazw PGN z wbudowanej bazy.
    """

    def __init__(self, app):
        super().__init__(app)
        self._pgn_database = {}
        self._load_pgn_database()

    def _load_pgn_database(self):
        """Wczytuje bazę nazw PGN (współdzieloną z J1939Controller)."""
        import json, os
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               "j1939_pgn_definitions.json")
        try:
            with open(db_path, "r") as f:
                data = json.load(f)
                for key, value in data.items():
                    try:
                        if key.startswith("0x"):
                            int_key = int(key, 16)
                        else:
                            int_key = int(key)
                        self._pgn_database[int_key] = value
                    except ValueError:
                        pass
            logger.info(f"J1939AssociativeController: wczytano {len(self._pgn_database)} definicji PGN.")
        except FileNotFoundError:
            logger.warning("Baza PGN nie znaleziona – nazwy nie będą wyświetlane.")

    def _analyze(self):
        """Nadpisuje _analyze z klasy bazowej, dodając metadane J1939."""
        # Wywołujemy oryginalną analizę (zdarzenia + wartości)
        super()._analyze()
        # Wzbogacamy kandydatów o informacje J1939
        for cand in self.candidates:
            arb_id = cand["id"]
            parsed = parse_j1939_id(arb_id)
            cand["pgn"] = parsed["pgn"]
            cand["source_address"] = parsed["source_address"]
            cand["pgn_name"] = self._pgn_database.get(parsed["pgn"], "")
            # Zmieniamy źródło, aby GUI mogło rozróżnić
            if cand.get("source") in ("zdarzenie", None):
                cand["source"] = "j1939"

    def find_sequences(self, main_candidate, tolerance_ms=200):
        """Wyszukuje sekwencje, uwzględniając PGN."""
        sequences = super().find_sequences(main_candidate, tolerance_ms)
        for seq in sequences:
            # Dodajemy nazwy PGN do sekwencji
            named_ids = []
            for aid in seq.get("ids_order", []):
                parsed = parse_j1939_id(aid)
                name = self._pgn_database.get(parsed["pgn"], "")
                if name:
                    named_ids.append(f"{name} (0x{aid:X})")
                else:
                    named_ids.append(f"0x{aid:X}")
            seq["ids_order_named"] = named_ids
        return sequences

    def export_pattern(self, filepath):
        """Rozszerzony eksport z danymi J1939."""
        import json, time
        best = self.get_best_candidate()
        if not best:
            raise ValueError("Brak kandydatów do eksportu.")
        pattern = {
            "format_version": 2,
            "timestamp": time.time(),
            "id": best["id"],
            "pgn": best.get("pgn", None),
            "pgn_name": best.get("pgn_name", ""),
            "source_address": best.get("source_address", None),
            "byte_index": best.get("byte", None),
            "expected_value": best.get("value", None),
            "background_value": best.get("background", None),
            "confidence": best["confidence"],
            "source": best.get("source", "j1939"),
            "description": "Wzorzec J1939 wygenerowany przez uczenie asocjacyjne"
        }
        with open(filepath, "w") as f:
            json.dump(pattern, f, indent=2)
        logger.info(f"Wzorzec J1939 zapisany do {filepath}")
        return pattern
CONTROLLER_EOF
echo "Utworzono controllers/j1939_associative_controller.py"

# ---------- 2. Rozszerzenie bazy PGN o dodatkowe wpisy ----------
python3 << 'PYEOF'
import json

db_path = "j1939_pgn_definitions.json"
try:
    with open(db_path, "r") as f:
        data = json.load(f)
except FileNotFoundError:
    data = {}

# Dodajemy brakujące, często używane PGN-y
additions = {
    "0xFEF1": "Cruise Control / Vehicle Speed Setup (CCVS1)",
    "0xFEF2": "Cruise Control / Vehicle Speed Setup 2 (CCVS2)",
    "0xFEF5": "Electronic Engine Controller 5 (EEC5)",
    "0xFEF6": "Electronic Engine Controller 6 (EEC6)",
    "0xFEF7": "Electronic Engine Controller 7 (EEC7)",
    "0xFEF8": "Electronic Engine Controller 8 (EEC8)",
    "0xFECA": "Engine Temperature 1 (ET1)",
    "0xFECB": "Engine Temperature 2 (ET2)",
    "0xFECC": "Engine Fluid Level / Pressure 1",
    "0xFECD": "Engine Fluid Level / Pressure 2",
    "0xFEE3": "Vehicle Electrical Power 1",
    "0xFEE4": "Vehicle Electrical Power 2",
    "0xFEE5": "Vehicle Electrical Power 3",
    "0xFEE6": "Vehicle Electrical Power 4",
    "0xFEE7": "Vehicle Electrical Power 5",
    "0xFEE8": "Vehicle Electrical Power 6",
    "0xFEE9": "Vehicle Electrical Power 7",
    "0xFEEA": "Vehicle Electrical Power 8",
    "0xFEED": "Engine Hours, Revolutions",
    "0xFEEE": "Engine Starts",
    "0xFEEF": "Trip Fuel",
    "0xFEF0": "Total Fuel Used",
    "0xFEF1": "Trip Distance",
    "0xFEF2": "Total Vehicle Distance",
}
added_count = 0
for k, v in additions.items():
    if k not in data:
        data[k] = v
        added_count += 1

with open(db_path, "w") as f:
    json.dump(data, f, indent=2)

if added_count:
    print(f"Dodano {added_count} nowych wpisów do bazy PGN.")
else:
    print("Wszystkie PGN-y już były w bazie.")
PYEOF

# ---------- 3. Sprawdzenie składni ----------
echo ""
python3 -m py_compile controllers/j1939_associative_controller.py && echo "  j1939_associative_controller.py OK" || echo "  j1939_associative_controller.py BŁĄD"
python3 -m py_compile controllers/associative_controller.py && echo "  associative_controller.py OK" || echo "  associative_controller.py BŁĄD"

echo ""
echo "=== Faza 14a wdrożona ==="
echo "Nowy kontroler J1939AssociativeController gotowy."
echo "Uruchom update_F14b.sh aby dodać przełącznik CAN/J1939 w GUI."
