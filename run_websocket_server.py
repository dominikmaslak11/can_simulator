#!/usr/bin/env python3
"""
Testowy skrypt uruchamiający serwer WebSocket CAN.

Uruchom w terminalu:
    python run_websocket_server.py

Następnie przetestuj połączenie np. przez:
    https://www.piesocket.com/websocket-tester
wpisując adres: ws://localhost:8765
(lub użyj własnego klienta websocket)
"""

import asyncio
import logging
import signal
import sys
import time

# Dodaj bieżący katalog do ścieżki, aby móc importować broadcaster
sys.path.insert(0, '.')

from broadcaster import CANWebSocketServer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

server = CANWebSocketServer(port=8765)

async def simulate_can_frames():
    """Symuluje ramki CAN co 1 sekundę (tylko do demonstracji)."""
    counter = 0
    while server.is_running:
        frame = {
            "id": "0x123",
            "data": [counter % 256, 0, 0, 0, 0, 0, 0, 0],
            "timestamp": time.time()
        }
        await server.broadcast_frame_async(frame)
        logging.info(f"Wysłano ramkę: {frame}")
        counter += 1
        await asyncio.sleep(1.0)

async def main():
    await server.start()
    logging.info("Serwer WebSocket działa. Naciśnij Ctrl+C, aby zatrzymać.")
    # Uruchom symulację ramek (w tle)
    task = asyncio.create_task(simulate_can_frames())
    try:
        # Czekaj na przerwanie
        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGINT, stop_event.set)
        loop.add_signal_handler(signal.SIGTERM, stop_event.set)
        await stop_event.wait()
    finally:
        task.cancel()
        await server.stop()
        logging.info("Serwer zatrzymany.")

if __name__ == "__main__":
    asyncio.run(main())
