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
