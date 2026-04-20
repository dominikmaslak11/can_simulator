import socket
import struct
import logging

logger = logging.getLogger("CANInterface")

AF_CAN = 29
PF_CAN = AF_CAN
CAN_RAW = 1

class CanInterface:
    def __init__(self, interface='can0'):
        self.interface = interface
        self.sock = None
        self.connected = False

    def connect(self):
        try:
            self.sock = socket.socket(PF_CAN, socket.SOCK_RAW, CAN_RAW)
            self.sock.bind((self.interface,))
            self.connected = True
            logger.info(f"Połączono z {self.interface}")
            return True, f"Połączono z {self.interface}"
        except Exception as e:
            self.connected = False
            logger.error(f"Błąd połączenia: {e}")
            return False, f"Błąd: {e}"

    def disconnect(self):
        if self.sock:
            self.sock.close()
            self.sock = None
        self.connected = False
        logger.info("Rozłączono")

    def send_frame(self, can_id, data, is_extended=None):
        if not self.connected or not self.sock:
            return False, "Brak połączenia"
        if is_extended is None:
            is_extended = (can_id > 0x7FF)
        flags = can_id | (0x80000000 if is_extended else 0)
        data = bytes(data)[:8].ljust(8, b'\x00')
        frame = struct.pack("<IB3s8s", flags, len(data), b'\x00'*3, data)
        try:
            self.sock.send(frame)
            return True, f"Wysłano ID=0x{can_id:08X}"
        except Exception as e:
            logger.error(f"Błąd wysyłania: {e}")
            return False, f"Błąd: {e}"
