#!/usr/bin/env python3
import asyncio
import websockets
import json
import time

async def handler(websocket, path):
    print(f"Nowe połączenie z {websocket.remote_address}")
    try:
        async for message in websocket:
            print(f"Otrzymano: {message}")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Połączenie zamknięte: {e}")
    finally:
        print("Handler zakończony")

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("Serwer działa na ws://0.0.0.0:8765")
        await asyncio.Future()  # działa w nieskończoność

if __name__ == "__main__":
    asyncio.run(main())
