"""Test integracyjny uczenia asocjacyjnego z vcan0."""
import unittest
import time
import threading
import sys
import os

# Dodajemy katalog nadrzędny do ścieżki
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Symulujemy środowisko CAN
try:
    import can
    HAS_CAN = True
except ImportError:
    HAS_CAN = False

# Importujemy tylko jeśli mamy dostępne zależności
if HAS_CAN:
    from can_interface import CanInterface
    from controllers.associative_controller import AssociativeController


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


@unittest.skipUnless(HAS_CAN, "python-can nie jest dostępny")
class TestAssociativeIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Sprawdzamy, czy vcan0 istnieje
        import subprocess
        result = subprocess.run(['ip', 'link', 'show', 'vcan0'],
                                capture_output=True, text=True)
        if result.returncode != 0:
            raise unittest.SkipTest("vcan0 nie istnieje. Utwórz: sudo ip link add dev vcan0 type vcan && sudo ip link set up vcan0")

    def setUp(self):
        self.app = DummyApp()
        self.app.connect('vcan0')
        if not self.app.can.connected:
            self.skipTest("Nie można połączyć z vcan0")
        self.controller = AssociativeController(self.app)
        self.controller.start()

    def tearDown(self):
        self.controller.stop()
        self.app.can.disconnect()

    def test_event_toggle_counts_iteration(self):
        """Sprawdza, czy toggle_event zwiększa licznik iteracji."""
        self.assertEqual(self.controller.get_iteration_count(), 0)
        self.controller.toggle_event()  # start
        self.controller.toggle_event()  # stop -> 1 iteracja
        self.controller.toggle_event()  # start
        self.controller.toggle_event()  # stop -> 2 iteracje
        self.assertEqual(self.controller.get_iteration_count(), 2)

    def test_buffer_fills_with_messages(self):
        """Sprawdza, czy ramki wysłane na vcan0 trafiają do bufora."""
        import can as can_lib
        bus = can_lib.interface.Bus(channel='vcan0', bustype='socketcan')
        # Wysyłamy kilka ramek
        msg = can_lib.Message(arbitration_id=0x123, data=[0x01, 0x02, 0x03], is_extended_id=False)
        for _ in range(5):
            bus.send(msg)
        time.sleep(0.5)
        snapshot = self.controller.get_buffer_snapshot(max_items=100)
        self.assertGreater(len(snapshot), 0)
        # Sprawdź, czy nasz ID jest w buforze
        ids = [rec['arb_id'] for rec in snapshot]
        self.assertIn(0x123, ids)
        bus.shutdown()

    def test_labeling_after_event(self):
        """Sprawdza, czy po zakończeniu zdarzenia ramki są oznaczane."""
        self.controller.toggle_event()  # start
        time.sleep(0.1)
        self.controller.toggle_event()  # stop
        labeled = self.controller.last_labeled
        self.assertIn("positive", labeled)
        self.assertIn("negative", labeled)

    def test_candidates_generated(self):
        """Sprawdza, czy po kilku iteracjach pojawiają się kandydaci."""
        import can as can_lib
        bus = can_lib.interface.Bus(channel='vcan0', bustype='socketcan')
        event_msg = can_lib.Message(arbitration_id=0x555, data=[0x00, 0x01, 0x00], is_extended_id=False)
        noise_msg = can_lib.Message(arbitration_id=0x200, data=[0x11, 0x22, 0x33], is_extended_id=False)

        # Wysyłamy szum
        for _ in range(3):
            bus.send(noise_msg)
        time.sleep(0.1)

        # Iteracja 1
        self.controller.toggle_event()
        bus.send(event_msg)
        time.sleep(0.1)
        self.controller.toggle_event()

        # Iteracja 2
        self.controller.toggle_event()
        bus.send(event_msg)
        time.sleep(0.1)
        self.controller.toggle_event()

        candidates = self.controller.get_candidates()
        self.assertGreater(len(candidates), 0)
        # 0x555 powinien być wysoko w rankingu
        id_555_cands = [c for c in candidates if c['id'] == 0x555]
        self.assertTrue(len(id_555_cands) > 0)

        bus.shutdown()


if __name__ == '__main__':
    unittest.main()

    def test_value_correlation(self):
        """Test trybu wartościowego – korelacja liniowa."""
        import can as can_lib
        bus = can_lib.interface.Bus(channel='vcan0', bustype='socketcan')
        # Symulacja: temperatura rośnie, bajt 2 rośnie proporcjonalnie
        for temp in range(20, 30):
            byte_val = temp + 30   # bajt 2 = temp + 30
            msg = can_lib.Message(arbitration_id=0x300, data=[0x00, 0x00, byte_val, 0x00],
                                  is_extended_id=False)
            bus.send(msg)
            time.sleep(0.05)
            # Zatwierdź wartość referencyjną
            self.controller.commit_value(float(temp))
            time.sleep(0.05)

        # Wymuś analizę
        self.controller._analyze()
        candidates = self.controller.get_candidates()
        # Powinien być kandydat dla ID 0x300, bajt 2
        matching = [c for c in candidates if c['id'] == 0x300 and c['byte'] == 2]
        self.assertTrue(len(matching) > 0, "Nie znaleziono korelacji dla ID 0x300 bajt 2")
        bus.shutdown()

    def test_sequence_detection(self):
        """Test wykrywania sekwencji: ID_B -> ID_A -> ID_C."""
        import can as can_lib
        bus = can_lib.interface.Bus(channel='vcan0', bustype='socketcan')
        # Główna ramka 0x400, poprzedzająca 0x300, następująca 0x500
        for i in range(5):
            # Sekwencja przed
            bus.send(can_lib.Message(arbitration_id=0x300, data=[0x01], is_extended_id=False))
            time.sleep(0.01)
            # Główna
            bus.send(can_lib.Message(arbitration_id=0x400, data=[0x02], is_extended_id=False))
            time.sleep(0.01)
            # Sekwencja po
            bus.send(can_lib.Message(arbitration_id=0x500, data=[0x03], is_extended_id=False))
            time.sleep(0.05)

        # Wprowadź główny kandydat
        self.controller.candidates = [{"id": 0x400, "byte": 0, "confidence": 95, "source": "zdarzenie"}]
        seqs = self.controller.find_sequences(self.controller.candidates[0])
        self.assertTrue(len(seqs) > 0)
        self.assertIn(0x300, seqs[0]["ids_order"])
        self.assertIn(0x500, seqs[0]["ids_order"])
        bus.shutdown()

