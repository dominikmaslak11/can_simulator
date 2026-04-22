import socket
import struct
import logging
import threading
import time

logger = logging.getLogger("CANInterface")

AF_CAN = 29
PF_CAN = AF_CAN
CAN_RAW = 1

class CanInterface:
    def __init__(self, interface='can0'):
        self.interface = interface
        self.sock = None
        self.connected = False
        self._recv_thread = None
        self._recv_callback = None
        self._running = False

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


    def add_frame_callback(self, callback):
        """Dodaje funkcję callback, która będzie wywoływana dla każdej odebranej ramki.
        Callback powinien przyjmować jeden argument: słownik z polami 'id', 'data', 'is_extended', 'timestamp'.
        """
        if callback not in self.frame_callbacks:
            self.frame_callbacks.append(callback)


    def disconnect(self):
        self.stop_receiving()
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

    def start_receiving(self, callback):
        """Uruchamia wątek nasłuchujący ramki CAN."""
        if not self.connected:
            return False
        self._recv_callback = callback
        self._running = True
        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._recv_thread.start()
        logger.info("Nasłuchiwanie CAN uruchomione")
        return True

    def stop_receiving(self):
        self._running = False
        if self._recv_thread:
            self._recv_thread.join(timeout=0.5)
        logger.info("Nasłuchiwanie CAN zatrzymane")

    def _recv_loop(self):
        while self._running and self.connected:
            try:
                data = self.sock.recv(16)
                if data and self._recv_callback:
                    can_id, dlc, payload = self._parse_frame(data)
                    is_ext = bool(can_id & 0x80000000)
                    can_id &= 0x1FFFFFFF
                    timestamp = time.time()
                    self._recv_callback(timestamp, can_id, payload[:dlc], is_ext)
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Błąd odbioru: {e}")
                break

    def _parse_frame(self, data):
        flags, dlc, _, payload = struct.unpack("<IB3s8s", data)
        return flags, dlc, payload
