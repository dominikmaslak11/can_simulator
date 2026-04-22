#!/bin/bash
# Test połączenia WebSocket z lokalnym serwerem CAN

set -e

PORT=8765
SERVER_PID=""

cleanup() {
    echo ""
    echo "Zatrzymywanie serwera..."
    if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill "$SERVER_PID"
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    echo "Koniec testu."
}

trap cleanup EXIT INT TERM

echo "=== Test WebSocket na porcie $PORT ==="

# Uruchom serwer w tle
echo "Uruchamianie serwera run_websocket_server.py ..."
python run_websocket_server.py > /tmp/ws_server.log 2>&1 &
SERVER_PID=$!

# Poczekaj na uruchomienie (sprawdzamy, czy port zaczyna nasłuchiwać)
echo "Czekam na uruchomienie serwera..."
for i in {1..10}; do
    if ss -tlnp 2>/dev/null | grep -q ":$PORT" || netstat -tlnp 2>/dev/null | grep -q ":$PORT"; then
        echo "Serwer nasłuchuje na porcie $PORT"
        break
    fi
    sleep 1
done

# Test 1: websocat (jeśli dostępny)
if command -v websocat &> /dev/null; then
    echo ""
    echo "Testowanie za pomocą websocat..."
    echo "Wysyłam zapytanie i oczekuję odpowiedzi (timeout 3s)"
    if timeout 3 websocat "ws://localhost:$PORT" <<< ""; then
        echo "✅ Połączenie udane! Serwer odpowiedział."
    else
        echo "❌ Błąd połączenia lub timeout."
    fi

# Test 2: prosty klient Python (jeśli nie ma websocat)
else
    echo ""
    echo "websocat nie jest zainstalowany. Używam wbudowanego klienta Python..."
    python - <<EOF
import asyncio
import websockets
import sys

async def test():
    uri = "ws://localhost:$PORT"
    print(f"Łączenie z {uri} ...")
    try:
        async with websockets.connect(uri, timeout=3) as websocket:
            print("Połączono. Oczekiwanie na pierwszą wiadomość...")
            message = await asyncio.wait_for(websocket.recv(), timeout=3)
            print(f"Odebrano: {message}")
            print("✅ Test zakończony sukcesem!")
    except Exception as e:
        print(f"❌ Błąd: {e}")
        sys.exit(1)

asyncio.run(test())
EOF
    if [ $? -eq 0 ]; then
        echo "✅ Połączenie udane!"
    else
        echo "❌ Test nie powiódł się."
    fi
fi

echo ""
echo "Logi serwera (ostatnie 10 linii):"
tail -10 /tmp/ws_server.log

echo ""
echo "Jeśli test się nie powiódł, sprawdź:"
echo "- Czy port $PORT nie jest zajęty (sudo lsof -i :$PORT)"
echo "- Czy firewall nie blokuje połączeń lokalnych (iptables -L)"
echo "- Czy w logach serwera widać próbę połączenia"
