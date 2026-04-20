import logging
from abc import ABC, abstractmethod

logger = logging.getLogger("CANInterface")


class CanInterface(ABC):
    """Abstrakcyjna klasa bazowa dla interfejsów CAN."""

    def __init__(self, interface='can0'):
        self.interface = interface
        self.connected = False

    @abstractmethod
    def connect(self):
        """Nawiązuje połączenie z interfejsem."""
        pass

    @abstractmethod
    def disconnect(self):
        """Zamyka połączenie."""
        pass

    @abstractmethod
    def send_frame(self, can_id, data, is_extended=None):
        """Wysyła ramkę CAN."""
        pass
