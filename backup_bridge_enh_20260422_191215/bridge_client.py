#!/usr/bin/env python3
"""
Mostek WebSocket -> wirtualny CAN (vcan0)

Użycie:
    sudo python bridge_client.py [--url wss://adres:port] [--token TOKEN]

Domyślnie łączy się z ws://localhost:8765.
"""

import asyncio
import json
import sys
import argparse
import logging
import signal
import threading
import time

import websocket
import can

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("CAN-Bridge")

class VCanBridge:
    def __init__(self, url, token=None):
        self.url = url
        self.token = token
        self.ws = None
        self.bus = None
        self.running = False
        self._setup_vcan()

    def _setup_vcan(self):
        """Tworzy wirtualny interfejs vcan0, jeśli nie istnieje."""
        import subprocess
        try:
            # Sprawdź, czy vcan0 już istnieje
            subprocess.run(['ip', 'link', 'show', 'vcan0'], check=True, capture_output=True)
            logger.info("vcan0 już istnieje.")
        except subprocess.CalledProcessError:
            logger.info("Tworzenie vcan0...")
            subprocess.run(['sudo', 'ip', 'link', 'add', 'dev', 'vcan0', 'type', 'vcan'], check=True)
            subprocess.run(['sudo', 'ip', 'link', 'set', 'vcan0', 'up'], check=True)
            logger.info("vcan0 utworzony i włączony.")

        # Inicjalizacja magistrali python-can
        self.bus = can.interface.Bus(channel='vcan0', interface='socketcan')

    def _on_message(self, ws, message):
        """Odbiera ramkę JSON z WebSocket i wysyła do vcan0."""
        try:
            data = json.loads(message)
            can_id = int(data['id'], 16) if isinstance(data['id'], str) else data['id']
            payload = bytes(data['data'])
            is_extended = data.get('is_extended', False)

            msg = can.Message(
                arbitration_id=can_id,
                data=payload,
                is_extended_id=is_extended
            )
            self.bus.send(msg)
            logger.debug(f"Wysłano do vcan0: {msg}")
        except Exception as e:
            logger.error(f"Błąd przetwarzania ramki: {e}")

    def _on_error(self, ws, error):
        logger.error(f"Błąd WebSocket: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        logger.info("Połączenie WebSocket zamknięte.")
        self.running = False

    def _on_open(self, ws):
        logger.info("Połączono z serwerem WebSocket.")
        if self.token:
            ws.send(self.token)
            logger.info("Token wysłany.")

    def start(self):
        self.running = True
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        # Uruchom wątek WebSocket
        wst = threading.Thread(target=self.ws.run_forever)
        wst.daemon = True
        wst.start()

        logger.info(f"Mostek uruchomiony. Nasłuch na {self.url} i przekazywanie do vcan0.")
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()
        if self.bus:
            self.bus.shutdown()
        logger.info("Mostek zatrzymany.")

def main():
    parser = argparse.ArgumentParser(description='Mostek WebSocket -> vcan0')
    parser.add_argument('--url', default='ws://localhost:8765', help='Adres WebSocket serwera')
    parser.add_argument('--token', help='Opcjonalny token autoryzacyjny')
    args = parser.parse_args()

    bridge = VCanBridge(args.url, args.token)
    bridge.start()

if __name__ == "__main__":
    main()
