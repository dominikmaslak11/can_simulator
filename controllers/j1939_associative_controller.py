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
