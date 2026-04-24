from typing import Optional
"""Emulacja prostego ECU odpowiadającego na żądania OBD-II."""
import struct

from can_interface import CanInterface


class EcuEmulator:
    """Uproszczony emulator ECU nasłuchujący ID 0x7DF i odpowiadający na 0x7E8."""

    OBD_REQUEST_ID = 0x7DF
    OBD_RESPONSE_ID = 0x7E8

    # Wybrane PIDy i ich domyślne wartości 4-bajtowe (lub krótsze)
    PID_DEFAULTS = {
        0x00: 0xBE1F_B810,  # PID 0x00 -> wspierane PIDy 01-20
        0x0C: 0x0000_1000,  # RPM (przykład ~1024 obr/min)
        0x0D: 0x0000_0050,  # Prędkość (80 km/h)
        0x05: 0x0000_0050,  # Temperatura cieczy chłodzącej (80°C)
        0x0B: 0x0000_006D,  # Ciśnienie w kolektorze (109 kPa)
    }

    def __init__(self, interface: CanInterface):
        self._interface = interface
        self._running = False
        self._callback_id = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._callback_id = self._interface.add_listener(self._on_message)

    def stop(self):
        self._running = False
        if self._callback_id is not None:
            self._interface.remove_listener(self._callback_id)
            self._callback_id = None

    def _on_message(self, msg):
        if not self._running:
            return
        # Sprawdzamy czy to zapytanie diagnostyczne (standard OBD-II: 0x7DF, DLC = 8, bajt 0 = 0x02)
        if msg.arbitration_id == self.OBD_REQUEST_ID and msg.dlc >= 8:
            data = msg.data
            # format: bajt0: liczba bajtów (zwykle 0x02 dla PID request), bajt1: serwis (0x01 = show current data)
            if data[0] == 0x02 and data[1] == 0x01:
                pid = data[2]
                response_data = self._generate_response(pid)
                if response_data is not None:
                    response_msg = self._interface.create_message(
                        arbitration_id=self.OBD_RESPONSE_ID,
                        data=response_data
                    )
                    self._interface.send(response_msg)

    def _generate_response(self, pid: int) -> Optional[bytes]:
        """Tworzy ramkę odpowiedzi dla danego PID lub zwraca None (brak wsparcia)."""
        default_val = self.PID_DEFAULTS.get(pid)
        if default_val is None:
            return None
        # Obligatoryjna ramka: 0x04 (liczba bajtów), 0x41 (serwis+0x40), PID, reszta danych
        payload = struct.pack(">BBBI", 0x04, 0x41, pid, default_val)
        return payload
