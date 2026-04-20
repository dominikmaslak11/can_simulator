import logging
from can_interface import CanInterface

logger = logging.getLogger("DummyInterface")


class DummyInterface(CanInterface):
    """Interfejs offline – symuluje wysyłanie, zawsze zwraca sukces."""

    def connect(self):
        self.connected = True
        logger.info(f"Połączono (tryb offline) z {self.interface}")
        return True, f"Połączono (offline) z {self.interface}"

    def disconnect(self):
        self.connected = False
        logger.info("Rozłączono (offline)")

    def send_frame(self, can_id, data, is_extended=None):
        if not self.connected:
            return False, "Brak połączenia"
        # Symulacja – zawsze sukces
        logger.info(f"[OFFLINE] Wysłano ID=0x{can_id:08X}")
        return True, f"[OFFLINE] Wysłano ID=0x{can_id:08X}"
