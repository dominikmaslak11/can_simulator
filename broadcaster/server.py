"""
Serwer WebSocket do przesyłania ramek CAN w czasie rzeczywistym.

Używa biblioteki `websockets` (asyncio).
"""

import asyncio
import json
import logging
from typing import Set, Callable, Optional

import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)


class CANWebSocketServer:
    """
    Serwer WebSocket rozgłaszający ramki CAN do podłączonych klientów.

    Użycie:
        server = CANWebSocketServer(port=8765)
        await server.start()
        # ... później
        server.broadcast_frame(frame_data)
        # ...
        await server.stop()
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8765, token: Optional[str] = None):
        self.host = host
        self.port = port
        self.token = token  # opcjonalny token autoryzacyjny
        self._server = None
        self._clients: Set[WebSocketServerProtocol] = set()
        self._running = False
        self._loop = None

    async def _handler(self, websocket: WebSocketServerProtocol, path: str):
        """Obsługa pojedynczego klienta."""
        # Opcjonalna autoryzacja przez nagłówek lub pierwszy komunikat
        if self.token:
            # Prosta autoryzacja: oczekujemy pierwszego komunikatu jako token
            try:
                msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                if msg != self.token:
                    logger.warning(f"Nieprawidłowy token od {websocket.remote_address}")
                    await websocket.close(1008, "Invalid token")
                    return
            except asyncio.TimeoutError:
                await websocket.close(1008, "Token timeout")
                return

        logger.info(f"Nowy klient połączony: {websocket.remote_address}")
        self._clients.add(websocket)
        try:
            # Utrzymuj połączenie – oczekuj na zamknięcie
            await websocket.wait_closed()
        finally:
            self._clients.remove(websocket)
            logger.info(f"Klient rozłączony: {websocket.remote_address}")

    async def start(self):
        """Uruchamia serwer WebSocket."""
        if self._running:
            logger.warning("Serwer już działa")
            return
        logger.info(f"Uruchamianie serwera WebSocket na {self.host}:{self.port}")
        self._server = await websockets.serve(self._handler, self.host, self.port)
        self._running = True

    async def stop(self):
        """Zatrzymuje serwer i rozłącza wszystkich klientów."""
        if not self._running:
            return
        logger.info("Zatrzymywanie serwera WebSocket...")
        self._server.close()
        await self._server.wait_closed()
        # Rozłącz pozostałych klientów
        for client in list(self._clients):
            await client.close()
        self._clients.clear()
        self._running = False
        logger.info("Serwer zatrzymany")

    def broadcast_frame(self, frame: dict):
        """
        Rozsyła ramkę CAN (w formacie słownika) do wszystkich klientów.
        Metoda NIEBLOKUJĄCA – planuje wysyłkę w pętli asyncio.
        """
        if not self._running or not self._clients:
            return
        message = json.dumps(frame)
        # Używamy asyncio.create_task, aby nie czekać na wysyłkę
        for client in list(self._clients):
            try:
                asyncio.create_task(client.send(message))
            except Exception as e:
                logger.error(f"Błąd wysyłania do klienta: {e}")

    async def broadcast_frame_async(self, frame: dict):
        """Wersja asynchroniczna – przydatna wewnątrz pętli asyncio."""
        if not self._running or not self._clients:
            return
        message = json.dumps(frame)
        for client in list(self._clients):
            try:
                await client.send(message)
            except Exception as e:
                logger.error(f"Błąd wysyłania do klienta: {e}")

    @property
    def client_count(self) -> int:
        return len(self._clients)

    @property
    def is_running(self) -> bool:
        return self._running
