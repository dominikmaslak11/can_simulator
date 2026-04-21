import time
import threading
import logging
from collections import deque

logger = logging.getLogger("SnifferThread")

class SnifferThread(threading.Thread):
    def __init__(self, can_if, callback):
        super().__init__(daemon=True)
        self.can = can_if
        self.callback = callback
        self.running = False
        self.paused = False
        self.filter_ids = set()       # puste = brak filtrowania
        self.filter_active = False    # czy filtrowanie włączone

    def set_filter(self, ids, active):
        self.filter_ids = set(ids)
        self.filter_active = active

    def run(self):
        self.running = True
        logger.info("SnifferThread uruchomiony")
        while self.running:
            if not self.paused:
                # W rzeczywistej implementacji użyjemy socket.recv, tu uproszczenie
                # Ramki będą dostarczane przez CanInterface, która wymaga rozszerzenia.
                # Na potrzeby przykładu symulujemy ramki.
                # W finalnej wersji CanInterface będzie mieć metodę recv_frame.
                time.sleep(0.1)
            else:
                time.sleep(0.1)
        logger.info("SnifferThread zatrzymany")

    def stop(self):
        self.running = False

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False
