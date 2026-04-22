#!/usr/bin/env python3
import asyncio
import websockets
import traceback

async def handler(websocket):   # <-- tylko jeden argument!
    print(f"Połączenie z {websocket.remote_address}")
    try:
        async for message in websocket:
            print(f"Odebrano: {message}")
    except Exception as e:
        print(f"BŁĄD W HANDLERZE: {e}")
        traceback.print_exc()
        raise

async def main():
    try:
        async with websockets.serve(handler, "0.0.0.0", 8765):
            print("Serwer nasłuchuje na ws://0.0.0.0:8765")
            await asyncio.Future()
    except Exception as e:
        print(f"BŁĄD SERWERA: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
