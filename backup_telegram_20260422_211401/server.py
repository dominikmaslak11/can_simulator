"""
Serwer WebSocket do przesyłania ramek CAN w czasie rzeczywistym.
Obsługuje opcjonalny token autoryzacyjny.
"""

import asyncio
import json
import logging
from datetime import datetime
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

        self.allowed_client_ids = None   # lista dozwolonych ID dla klientów (None = wszystkie)
        self.incoming_filter_ids = None  # filtr ID dla ramek przychodzących
        self.log_to_file = False
        self.log_file_path = "remote_operations.log"

        self._running = False

    async def _handler(self, websocket: WebSocketServerProtocol):
        logger.info(f"Nowy klient: {websocket.remote_address}")

        # Odbierz token (jeśli wymagany)
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

        # Odbierz listę dozwolonych ID (wymagane, jeśli serwer ma ustawione allowed_client_ids)
        if self.allowed_client_ids is not None:
            try:
                msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(msg)
                client_ids = set(data.get("allowed_ids", []))
                if not client_ids.issubset(self.allowed_client_ids):
                    logger.warning(f"Klient {websocket.remote_address} próbował użyć niedozwolonych ID")
                    await websocket.close(1008, "Forbidden IDs")
                    return
                websocket.client_allowed_ids = client_ids
                logger.info(f"Klient {websocket.remote_address} autoryzowany z ID: {client_ids}")
            except (asyncio.TimeoutError, json.JSONDecodeError):
                logger.warning(f"Błąd autoryzacji ID od {websocket.remote_address}")
                await websocket.close(1008, "Invalid ID list")
                return

        self._clients.add(websocket)
        logger.info(f"Klient dodany, łącznie: {len(self._clients)}")

        try:
            async for message in websocket:
                await self._handle_incoming_frame(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Połączenie zamknięte przez klienta {websocket.remote_address}")
        finally:
            self._clients.remove(websocket)
            logger.info(f"Klient rozłączony, pozostało: {len(self._clients)}")

    async def _handle_incoming_frame(self, websocket, message):
        """Przetwarza ramkę otrzymaną od klienta i wysyła na CAN."""
        if not self.incoming_filter_ids:
            logger.debug("Brak filtru przychodzącego – ramka odrzucona.")
            return
        try:
            data = json.loads(message)
            can_id = int(data['id'], 16) if isinstance(data['id'], str) else data['id']
            if can_id not in self.incoming_filter_ids:
                logger.debug(f"ID 0x{can_id:X} nie przechodzi filtra przychodzącego.")
                return
            payload = bytes(data['data'])
            is_extended = data.get('is_extended', False)
            if self.can_interface and self.can_interface.connected:
                success, msg = self.can_interface.send_frame(can_id, payload, is_extended)
                if success:
                    logger.info(f"Wysłano na CAN: ID=0x{can_id:X}, data={payload.hex().upper()}")
                    if self.log_to_file:
                        self._log_to_file(f"RX from {websocket.remote_address}: {message}")
                else:
                    logger.error(f"Błąd wysyłania na CAN: {msg}")
            else:
                logger.warning("CAN niepodłączony – ramka odrzucona.")
        except Exception as e:
            logger.error(f"Błąd przetwarzania ramki od klienta: {e}")

    async def start(self):
        if self._running:
            return
        logger.info(f"Uruchamianie serwera WebSocket na {self.host}:{self.port} (SSL: {self.ssl_context is not None})")
        self._server = await websockets.serve(
            self._handler, self.host, self.port, ssl=self.ssl_context
        )
        self._running = True

    def _log_to_file(self, msg):
        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().isoformat()} {msg}\n")
        except Exception as e:
            logger.error(f"Błąd zapisu do pliku logu: {e}")

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

        if self.log_to_file:
            self._log_to_file(f"TX to clients: {message}")

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
