#!/bin/bash
# update_F12a.sh – Faza 12a: Parser J1939 + baza PGN + kontroler
# Uruchom w katalogu can_simulator/

set -e

echo "=== Wdrażanie Fazy 12a: Parser J1939 i kontroler ==="

# ---------- 1. parsers_j1939.py ----------
if [ ! -f parsers_j1939.py ]; then
    cat > parsers_j1939.py << 'EOF'
"""Parser identyfikatorów J1939 (29-bit)."""

def parse_j1939_id(arb_id: int):
    """
    Rozbija 29-bitowy identyfikator J1939 na składowe:
    - priority (3 bity, najstarsze)
    - pgn (18 bitów)
    - source_address (8 bitów)
    Zwraca słownik.
    """
    priority = (arb_id >> 26) & 0x07
    pgn = (arb_id >> 8) & 0x3FFFF
    source_address = arb_id & 0xFF
    return {
        "priority": priority,
        "pgn": pgn,
        "source_address": source_address
    }
EOF
    echo "Utworzono parsers_j1939.py"
else
    echo "parsers_j1939.py już istnieje"
fi

# ---------- 2. j1939_pgn_definitions.json (wbudowana baza) ----------
if [ ! -f j1939_pgn_definitions.json ]; then
    cat > j1939_pgn_definitions.json << 'EOF'
{
  "61444": "Electronic Engine Controller 1 (EEC1)",
  "61445": "Electronic Engine Controller 2 (EEC2)",
  "61446": "Electronic Engine Controller 3 (EEC3)",
  "61447": "Electronic Engine Controller 4 (EEC4)",
  "61448": "Electronic Transmission Controller 1 (ETC1)",
  "61449": "Electronic Transmission Controller 2 (ETC2)",
  "61450": "Electronic Brake Controller 1 (EBC1)",
  "61451": "Electronic Brake Controller 2 (EBC2)",
  "65132": "Cruise Control / Vehicle Speed Setup (CCVS)",
  "65133": "Vehicle Speed",
  "65134": "Engine Pressure",
  "65135": "Fuel Economy",
  "65177": "Engine Temperature 1 (ET1)",
  "65217": "High Resolution Vehicle Distance",
  "65226": "Active Diagnostic Trouble Codes (DM1)",
  "65227": "Previously Active Diagnostic Trouble Codes (DM2)",
  "65228": "Diagnostic Data Clear/Reset for Active DTcs (DM3)",
  "65229": "Freeze Frame Parameters (DM4)",
  "65230": "Diagnostic Readiness (DM5)",
  "65231": "OBD Compliance (DM6)",
  "65260": "Vehicle Identification (VIN)",
  "65262": "Engine Hours",
  "65263": "Engine Starts",
  "65264": "Trip Fuel",
  "65265": "Total Fuel Used",
  "65266": "Trip Distance",
  "65267": "Total Vehicle Distance",
  "65268": "Cruise Control / Vehicle Speed Setup 2",
  "65269": "Engine Temperature 2 (ET2)",
  "65270": "Engine Temperature 3 (ET3)",
  "65271": "Engine Fluid Level / Pressure 1 (EFL/P1)",
  "65272": "Engine Fluid Level / Pressure 2 (EFL/P2)",
  "65276": "Vehicle Weight",
  "65278": "Retarder Configuration",
  "65279": "Retarder Fluid",
  "65280": "Retarder Request",
  "65281": "Aux Input Output 1",
  "65282": "Aux Input Output 2",
  "65283": "Aux Input Output 3",
  "65284": "Cab Interior Environment",
  "65285": "Dash Display",
  "65312": "Vehicle Power Takeoff (PTO)",
  "65313": "Power Takeoff Engine Control (PTODE)",
  "65314": "Time/Date",
  "65315": "Tire Pressure",
  "65316": "Trailer Weight",
  "65317": "Turbocharger",
  "65318": "Intake/Exhaust Conditions",
  "65319": "Exhaust Emissions",
  "0xF004": "Electronic Engine Controller 1 (EEC1)",
  "0xF005": "Electronic Engine Controller 2 (EEC2)",
  "0xF006": "Electronic Engine Controller 3 (EEC3)",
  "0xF007": "Electronic Engine Controller 4 (EEC4)",
  "0xF008": "Electronic Transmission Controller 1 (ETC1)",
  "0xF009": "Electronic Transmission Controller 2 (ETC2)",
  "0xF00A": "Electronic Brake Controller 1 (EBC1)",
  "0xF00B": "Electronic Brake Controller 2 (EBC2)",
  "0xFE6C": "Cruise Control / Vehicle Speed Setup (CCVS)",
  "0xFE6D": "Vehicle Speed"
}
EOF
    echo "Utworzono j1939_pgn_definitions.json"
else
    echo "j1939_pgn_definitions.json już istnieje"
fi

# ---------- 3. controllers/j1939_controller.py ----------
mkdir -p controllers

if [ ! -f controllers/j1939_controller.py ]; then
    cat > controllers/j1939_controller.py << 'EOF'
"""Kontroler dla zakładki J1939 Browser."""
import logging
import json
import os
from parsers_j1939 import parse_j1939_id

logger = logging.getLogger("J1939Controller")

class J1939Controller:
    def __init__(self, app):
        self.app = app
        self.running = False
        self.listener_id = None
        self.frames = []  # lista słowników podobnych do CAN record
        self.pgn_database = self._load_pgn_database()

    def _load_pgn_database(self):
        """Wczytuje bazę nazw PGN z pliku JSON."""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               "j1939_pgn_definitions.json")
        try:
            with open(db_path, "r") as f:
                data = json.load(f)
                # Uzupełniamy klucze o wersje hex i int
                result = {}
                for key, value in data.items():
                    try:
                        if key.startswith("0x"):
                            int_key = int(key, 16)
                        else:
                            int_key = int(key)
                        result[int_key] = value
                    except ValueError:
                        pass
                logger.info(f"Wczytano {len(result)} definicji PGN.")
                return result
        except FileNotFoundError:
            logger.warning("Baza PGN nie znaleziona.")
            return {}

    def start(self):
        if self.running:
            return
        self.running = True
        self.listener_id = self.app.can.add_listener(self._on_message)
        logger.info("J1939 Browser uruchomiony")

    def stop(self):
        self.running = False
        if self.listener_id is not None:
            self.app.can.remove_listener(self.listener_id)
            self.listener_id = None
        logger.info("J1939 Browser zatrzymany")

    def _on_message(self, msg):
        if not self.running:
            return
        # Interesują nas tylko ramki z rozszerzonym identyfikatorem (29-bit)
        if not msg.is_extended:
            return
        record = {
            "timestamp": msg.timestamp,
            "arb_id": msg.arbitration_id,
            "data": list(msg.data),
            "dlc": msg.dlc,
            "is_extended": True
        }
        self.frames.append(record)
        # Ograniczenie bufora
        if len(self.frames) > 1000:
            self.frames = self.frames[-1000:]

    def get_frames(self):
        """Zwraca ostatnie ramki J1939."""
        return list(self.frames)

    def get_pgn_name(self, pgn):
        """Zwraca nazwę PGN (jeśli znana)."""
        return self.pgn_database.get(pgn, None)

    def clear(self):
        self.frames = []
EOF
    echo "Utworzono controllers/j1939_controller.py"
else
    echo "j1939_controller.py już istnieje"
fi

# Sprawdzenie składni
python3 -m py_compile parsers_j1939.py && echo "  parsers_j1939.py OK" || echo "  parsers_j1939.py BŁĄD"
python3 -m py_compile controllers/j1939_controller.py && echo "  j1939_controller.py OK" || echo "  j1939_controller.py BŁĄD"

echo ""
echo "=== Faza 12a zakończona ==="
echo "Uruchom update_F12b.sh"
