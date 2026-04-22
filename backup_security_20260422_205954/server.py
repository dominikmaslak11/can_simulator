"""
Serwer WebSocket do przesyłania ramek CAN w czasie rzeczywistym.
Obsługuje opcjonalny token autoryzacyjny.
"""

import asyncio
import json
import logging
from typing import Set, Optional
import ssl

import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)


class CANWebSocketServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8765, token: Optional[str] = None, ssl_context: Optional[ssl.SSLContext] = None):
        self.host = host
        self.port = port
        self.token = token
        self.ssl_context = ssl_context
        self._server = None
        self._clients: Set[WebSocketServerProtocol] = set()
        
        self.can_interface = None  # do ustawienia z zewnątrz (przez GUI)

        self._running = False

    async def _handler(self, websocket: WebSocketServerProtocol):
        logger.info(f"Nowy klient: {websocket.remote_address}")
        if self.token:
            try:
                msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                if msg != self.token:
                    logger.warning(f"Nieprawidłowy token od {websocket.remote_address}")
                    await websocket.close(1008, "Invalid token")
                    return
                logger.info(f"Token zaakceptowany od {websocket.remote_address}")
            except asyncio.TimeoutError:
                logger.warning(f"Timeout tokena od {websocket.remote_address}")
                await websocket.close(1008, "Token timeout")
                return

        self._clients.add(websocket)
        logger.info(f"Klient dodany, łącznie: {len(self._clients)}")

        # Uruchom pętlę odbierania wiadomości od klienta
        try:
            async for message in websocket:
                await self._handle_incoming_frame(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Połączenie zamknięte przez klienta {websocket.remote_address}")
        finally:
            self._clients.remove(websocket)
            logger.info(f"Klient rozłączony, pozostało: {len(self._clients)}")
    async def start(self):
        if self._running:
            return
        logger.info(f"Uruchamianie serwera WebSocket na {self.host}:{self.port} (SSL: {self.ssl_context is not None})")
        self._server = await websockets.serve(
            self._handler, self.host, self.port, ssl=self.ssl_context
        )
        self._running = True

    async def stop(self):
        if not self._running:
            return
        logger.info("Zatrzymywanie serwera...")
        self._server.close()
        await self._server.wait_closed()
        for client in list(self._clients):
            await client.close()
        self._clients.clear()
        self._running = False
        logger.info("Serwer zatrzymany")

    def broadcast_frame(self, frame: dict):
        if not self._running or not self._clients:
            return
        message = json.dumps(frame)
        for client in list(self._clients):
            try:
                asyncio.create_task(client.send(message))
            except Exception as e:
                logger.error(f"Błąd wysyłania: {e}")

    async def broadcast_frame_async(self, frame: dict):
        if not self._running or not self._clients:
            return
        message = json.dumps(frame)
        for client in list(self._clients):
            try:
                await client.send(message)
            except Exception as e:
                logger.error(f"Błąd wysyłania async: {e}")

    @property
    def client_count(self) -> int:
        return len(self._clients)

    @property
    def is_running(self) -> bool:
        return self._running
