#!/usr/bin/env python3
"""
Mostek WebSocket -> wirtualny CAN (vcan0) z auto-reconnect i filtrowaniem ID.
"""

import json
import logging
import threading
import time
import subprocess
import sys
import argparse
from typing import List, Optional, Set

import websocket
try:
    import can
except ImportError:
    can = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("CAN-Bridge")


class VCanBridge:
    def __init__(self, url: str, token: Optional[str] = None,
                 filter_ids: Optional[List[int]] = None,
                 auto_reconnect: bool = True,
                 reconnect_delay: int = 5,
                 status_callback=None):
        self.url = url
        self.token = token
        self.filter_ids = set(filter_ids) if filter_ids else None
        self.auto_reconnect = auto_reconnect
        self.reconnect_delay = reconnect_delay
        self.status_callback = status_callback

        self.ws = None
        self.bus = None
        self.running = False
        self.reconnect_thread = None
        self._setup_vcan()

    def _setup_vcan(self):
        if can is None:
            raise RuntimeError("python-can not installed; bridge cannot run.")
        """Tworzy wirtualny interfejs vcan0, jeśli nie istnieje."""
        try:
            subprocess.run(['ip', 'link', 'show', 'vcan0'], check=True, capture_output=True)
            logger.info("vcan0 już istnieje.")
        except subprocess.CalledProcessError:
            logger.info("Tworzenie vcan0...")
            subprocess.run(['sudo', 'ip', 'link', 'add', 'dev', 'vcan0', 'type', 'vcan'], check=True)
            subprocess.run(['sudo', 'ip', 'link', 'set', 'vcan0', 'up'], check=True)
            logger.info("vcan0 utworzony i włączony.")
        self.bus = can.interface.Bus(channel='vcan0', interface='socketcan')

    def _should_forward(self, can_id: int) -> bool:
        """Sprawdza, czy ramka o danym ID powinna być przekazana."""
        if self.filter_ids is None:
            return True
        return can_id in self.filter_ids

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            can_id = int(data['id'], 16) if isinstance(data['id'], str) else data['id']

            if not self._should_forward(can_id):
                logger.debug(f"Pominięto ID 0x{can_id:X} (filtrowanie)")
                return

            payload = bytes(data['data'])
            is_extended = data.get('is_extended', False)
            msg = can.Message(arbitration_id=can_id, data=payload, is_extended_id=is_extended)
            self.bus.send(msg)
            if self.status_callback:
                self.status_callback(f"Wysłano: {msg}")
        except Exception as e:
            logger.error(f"Błąd ramki: {e}")

    def _on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")
        if self.status_callback:
            self.status_callback(f"Błąd: {error}")

    def _on_close(self, ws, code, msg):
        logger.info("WebSocket zamknięty.")
        if self.status_callback:
            self.status_callback("Rozłączono")
        if self.auto_reconnect and self.running:
            self._start_reconnect()

    def _on_open(self, ws):
        logger.info("Połączono z serwerem.")
        if self.token:
            ws.send(self.token)
        if self.status_callback:
            self.status_callback("Połączono")

    def _start_reconnect(self):
        if self.reconnect_thread and self.reconnect_thread.is_alive():
            return
        self.reconnect_thread = threading.Thread(target=self._reconnect_loop, daemon=True)
        self.reconnect_thread.start()

    def _reconnect_loop(self):
        while self.running:
            logger.info(f"Próba ponownego połączenia za {self.reconnect_delay} s...")
            time.sleep(self.reconnect_delay)
            if not self.running:
                break
            try:
                self.ws = websocket.WebSocketApp(
                    self.url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close
                )
                wst = threading.Thread(target=self.ws.run_forever, daemon=True)
                wst.start()
                break  # po udanym połączeniu wychodzimy z pętli
            except Exception as e:
                logger.error(f"Błąd reconnect: {e}")

    def start(self):
        self.running = True
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        wst = threading.Thread(target=self.ws.run_forever, daemon=True)
        wst.start()

    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()
        if self.bus:
            self.bus.shutdown()
        if self.status_callback:
            self.status_callback("Zatrzymano")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='ws://localhost:8765')
    parser.add_argument('--token')
    parser.add_argument('--filter-ids', help='Lista ID CAN oddzielonych przecinkami, np. 0x123,0x456')
    parser.add_argument('--no-auto-reconnect', action='store_true', help='Wyłącz automatyczne ponawianie')
    args = parser.parse_args()

    filter_ids = None
    if args.filter_ids:
        try:
            filter_ids = [int(x.strip(), 16) if x.strip().startswith('0x') else int(x.strip()) for x in args.filter_ids.split(',')]
        except ValueError:
            logger.error("Nieprawidłowy format listy ID. Użyj liczb dziesiętnych lub szesnastkowych z 0x.")
            sys.exit(1)

    bridge = VCanBridge(
        url=args.url,
        token=args.token,
        filter_ids=filter_ids,
        auto_reconnect=not args.no_auto_reconnect,
        status_callback=print
    )
    bridge.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bridge.stop()


if __name__ == "__main__":
    main()
