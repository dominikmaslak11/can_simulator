#!/usr/bin/env python3
import asyncio
import websockets
import json

async def test():
    uri = "ws://localhost:8765"
    print(f"Łączenie z {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Połączono! Oczekiwanie na dane...")
            async for message in websocket:
                data = json.loads(message)
                print(f"Odebrano: ID={data['id']}, data={data['data']}")
    except Exception as e:
        print(f"Błąd: {e}")

asyncio.run(test())
