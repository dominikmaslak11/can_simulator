"""Test integracyjny dla asocjacji J1939 (wymaga vcan0 i python-can)."""
import unittest
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import can
    HAS_CAN = True
except ImportError:
    HAS_CAN = False

if HAS_CAN:
    from can_interface import CanInterface
    from controllers.j1939_associative_controller import J1939AssociativeController
    from parsers_j1939 import parse_j1939_id


class DummyApp:
    """Minimalny obiekt aplikacji dla testów."""
    def __init__(self):
        self.can = CanInterface()
        self.can.connected = False

    def connect(self, interface='vcan0'):
        try:
            self.can.connect(interface)
            self.can.connected = True
        except Exception:
            self.can.connected = False

    def log(self, msg):
        pass  # w testach pomijamy logowanie


@unittest.skipUnless(HAS_CAN, "python-can nie jest dostępny")
class TestJ1939Associative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import subprocess
        result = subprocess.run(['ip', 'link', 'show', 'vcan0'],
                                capture_output=True, text=True)
        if result.returncode != 0:
            raise unittest.SkipTest("vcan0 nie istnieje.")

    def setUp(self):
        self.app = DummyApp()
        self.app.connect('vcan0')
        if not self.app.can.connected:
            self.skipTest("Nie można połączyć z vcan0")
        # Używamy specjalistycznego kontrolera J1939
        self.controller = J1939AssociativeController(self.app)
        self.controller.start()

    def tearDown(self):
        self.controller.stop()
        self.app.can.disconnect()

    def test_event_toggle_j1939(self):
        """Test podstawowego przełączania zdarzeń."""
        self.assertEqual(self.controller.get_iteration_count(), 0)
        self.controller.toggle_event()
        self.controller.toggle_event()
        self.assertEqual(self.controller.get_iteration_count(), 1)

    def test_candidates_pgn_enriched(self):
        """Sprawdza, czy kandydaci z J1939 mają pola pgn i source_address."""
        import can as can_lib
        bus = can_lib.interface.Bus(channel='vcan0', bustype='socketcan')

        # Wysyłamy kilka ramek J1939 (29-bit)
        for _ in range(3):
            msg = can_lib.Message(arbitration_id=0x18FEF100, data=[0x01, 0x02, 0x03, 0x04],
                                  is_extended_id=True)
            bus.send(msg)
            time.sleep(0.02)

        self.controller.toggle_event()
        time.sleep(0.1)
        self.controller.toggle_event()

        candidates = self.controller.get_candidates()
        self.assertGreater(len(candidates), 0, "Powinien być przynajmniej jeden kandydat")
        first = candidates[0]
        # Sprawdź obecność pól J1939
        self.assertIn("pgn", first, "Kandydat powinien mieć pole 'pgn'")
        self.assertIn("source_address", first, "Kandydat powinien mieć pole 'source_address'")
        # Sprawdź, czy PGN jest poprawny
        self.assertEqual(first["pgn"], 0xFEF1)

        bus.shutdown()

    def test_export_j1939_pattern(self):
        """Test eksportu wzorca J1939 do JSON."""
        import json, tempfile, os
        # Symulujemy kandydata
        self.controller.candidates = [{
            "id": 0x18FEF100,
            "byte": 1,
            "value": 0x02,
            "background": 0x00,
            "confidence": 95.0,
            "source": "j1939",
            "pgn": 0xFEF1,
            "pgn_name": "Cruise Control / Vehicle Speed Setup (CCVS1)",
            "source_address": 0x00
        }]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            filepath = tmp.name
        try:
            self.controller.export_pattern(filepath)
            with open(filepath, 'r') as f:
                data = json.load(f)
            self.assertEqual(data["format_version"], 2)
            self.assertEqual(data["pgn"], 0xFEF1)
            self.assertIn("Cruise Control", data["pgn_name"])
        finally:
            os.unlink(filepath)


if __name__ == '__main__':
    unittest.main()
