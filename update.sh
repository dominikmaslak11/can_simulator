#!/bin/bash
# =============================================================================
# Etap 11: Autoryzacja ID i szczegółowe logowanie zdalnych operacji
# =============================================================================

set -e

BASE_DIR="$(pwd)"
SERVER_FILE="${BASE_DIR}/broadcaster/server.py"
GUI_TAB_FILE="${BASE_DIR}/gui/tabs/remote_monitor_tab.py"
BACKUP_DIR="${BASE_DIR}/backup_security_$(date +%Y%m%d_%H%M%S)"

echo "=== Etap 11: Autoryzacja ID i logowanie zdalnych operacji ==="

mkdir -p "$BACKUP_DIR"
cp "$SERVER_FILE" "$GUI_TAB_FILE" "$BACKUP_DIR/" 2>/dev/null || true
echo "Kopie zapasowe w: $BACKUP_DIR"

# -----------------------------------------------------------------------------
# 1. Aktualizacja server.py – autoryzacja ID i logowanie do pliku
# -----------------------------------------------------------------------------
python3 - "$SERVER_FILE" <<'EOF'
import re, sys
file_path = sys.argv[1]
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1.1 Dodajemy atrybuty w __init__
init_pattern = r'(def __init__\(self.*?\):.*?)(self\._running = False)'
attrs = '''
        self.allowed_client_ids = None   # lista dozwolonych ID dla klientów (None = wszystkie)
        self.log_to_file = False
        self.log_file_path = "remote_operations.log"
'''
content = re.sub(init_pattern, r'\1' + attrs + r'\n        \2', content, flags=re.DOTALL)

# 1.2 Modyfikujemy _handler – po tokenie oczekujemy JSON z dozwolonymi ID
handler_pattern = r'(async def _handler\(self, websocket: WebSocketServerProtocol\):.*?)(if self\.token:)'
new_auth = '''
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
                # Zapisujemy dozwolone ID dla tego klienta (do logowania)
                websocket.client_allowed_ids = client_ids
                logger.info(f"Klient {websocket.remote_address} autoryzowany z ID: {client_ids}")
            except (asyncio.TimeoutError, json.JSONDecodeError):
                logger.warning(f"Błąd autoryzacji ID od {websocket.remote_address}")
                await websocket.close(1008, "Invalid ID list")
                return
'''
content = re.sub(handler_pattern, r'\1' + new_auth + r'\n        \2', content, flags=re.DOTALL)

# 1.3 W _handle_incoming_frame dodajemy logowanie do pliku
handle_method = r'(async def _handle_incoming_frame\(self, websocket, message\):.*?)(?=\n    async def stop)'
if re.search(handle_method, content, flags=re.DOTALL):
    log_code = '''
            # Loguj do pliku jeśli włączone
            if self.log_to_file:
                self._log_to_file(f"RX from {websocket.remote_address}: {message}")
'''
    content = re.sub(r'(logger\.info\(f"Wysłano na CAN:.*?\))', r'\1' + log_code, content, flags=re.DOTALL)

# 1.4 Dodajemy metodę _log_to_file
log_method = '''
    def _log_to_file(self, msg):
        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().isoformat()} {msg}\\n")
        except Exception as e:
            logger.error(f"Błąd zapisu do pliku logu: {e}")
'''
if '_log_to_file' not in content:
    content = re.sub(r'(import logging)', r'\1\nfrom datetime import datetime', content)
    content = re.sub(r'(    async def stop\(self\):)', log_method + r'\n\n\1', content)

# 1.5 W broadcast_frame_async logujemy wysyłane ramki
broadcast_pattern = r'(async def broadcast_frame_async\(self, frame: dict\):.*?)(for client in list\(self\._clients\):)'
log_send = '''
        if self.log_to_file:
            self._log_to_file(f"TX to clients: {message}")
'''
content = re.sub(broadcast_pattern, r'\1' + log_send + r'\n            \2', content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("server.py zaktualizowany – autoryzacja ID i logowanie.")
EOF

# -----------------------------------------------------------------------------
# 2. Aktualizacja GUI – dodanie pola dozwolonych ID i checkboxa logowania
# -----------------------------------------------------------------------------
python3 - "$GUI_TAB_FILE" <<'EOF'
import re, sys
file_path = sys.argv[1]
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 2.1 Dodajemy atrybuty w __init__
init_pattern = r'(def __init__\(self, parent, app\):.*?)(self\._create_widgets)'
attrs = '''
        self.allowed_ids_var = tk.StringVar()
        self.log_to_file_var = tk.BooleanVar(value=False)
'''
content = re.sub(init_pattern, r'\1' + attrs + r'\n        \2', content, flags=re.DOTALL)

# 2.2 Dodajemy widgety w GUI
filter_widget = '''
        ttk.Label(frame, text="Dozwolone ID dla klientów:").grid(row=7, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(frame, textvariable=self.allowed_ids_var, width=40).grid(row=7, column=1, padx=5)
        ttk.Label(frame, text="(lista oddzielona przecinkami, puste = wszystkie)").grid(row=8, column=1, sticky=tk.W, padx=5)
        ttk.Checkbutton(frame, text="Zapisuj zdalne operacje do pliku", variable=self.log_to_file_var).grid(row=9, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
'''
content = re.sub(r'(self\.auto_reconnect_var = tk\.BooleanVar.*?\n)',
                r'\1' + filter_widget, content, flags=re.DOTALL)

# 2.3 W start_server przekazujemy ustawienia
start_pattern = r'(self\.server = CANWebSocketServer\(port=port, token=token, ssl_context=ssl_ctx\))'
replacement = '''        # Parsuj dozwolone ID
        allowed_str = self.allowed_ids_var.get().strip()
        allowed_ids = None
        if allowed_str:
            try:
                allowed_ids = [int(x.strip(), 16) if x.strip().startswith('0x') else int(x.strip())
                               for x in allowed_str.split(',') if x.strip()]
            except ValueError:
                messagebox.showerror("Błąd", "Nieprawidłowy format listy dozwolonych ID.")
                return
        self.server = CANWebSocketServer(port=port, token=token, ssl_context=ssl_ctx)
        self.server.allowed_client_ids = allowed_ids
        self.server.log_to_file = self.log_to_file_var.get()
        self.server.can_interface = self.app.can'''
content = re.sub(start_pattern, replacement, content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("remote_monitor_tab.py zaktualizowany – GUI dla autoryzacji ID.")
EOF

# -----------------------------------------------------------------------------
# 3. Aktualizacja bridge_client.py – wysyłanie listy dozwolonych ID
# -----------------------------------------------------------------------------
python3 - "${BASE_DIR}/bridge_client.py" <<'EOF'
import re, sys
file_path = sys.argv[1]
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# W _on_open wysyłamy token (już jest), a następnie listę dozwolonych ID
open_pattern = r'(def _on_open\(self, ws\):.*?)(if self\.token:.*?ws\.send\(self\.token\))'
if re.search(open_pattern, content, flags=re.DOTALL):
    send_ids = '''
        # Wyślij listę dozwolonych ID (jeśli ustawiono)
        if self.filter_ids is not None:
            allowed_msg = json.dumps({"allowed_ids": list(self.filter_ids)})
            ws.send(allowed_msg)
            logger.info(f"Wysłano listę dozwolonych ID: {self.filter_ids}")
'''
    content = re.sub(open_pattern, r'\1\2' + send_ids, content, flags=re.DOTALL)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("bridge_client.py zaktualizowany – wysyłanie listy ID.")
else:
    print("UWAGA: Nie znaleziono _on_open w bridge_client.py")
EOF

echo ""
echo "=== Etap 11 zakończony pomyślnie ==="
echo "Nowe funkcje bezpieczeństwa:"
echo "  - Klient musi przedstawić listę dozwolonych ID (zgodną z konfiguracją serwera)"
echo "  - Serwer loguje zdalne operacje (RX/TX) z adresem IP klienta"
echo "  - Opcjonalny zapis logów do pliku remote_operations.log"
echo ""
echo "Uruchom aplikację: sudo ./run.sh"
echo "Skonfiguruj w 'Zdalny monitoring':"
echo "  - 'Dozwolone ID dla klientów' (np. 0x123,0x456)"
echo "  - Zaznacz 'Zapisuj zdalne operacje do pliku'"
echo ""
echo "Wypchnij zmiany na GitHub:"
echo "  git add -A"
echo "  git commit -m 'Etap 11: Autoryzacja ID i szczegółowe logowanie zdalnych operacji'"
echo "  git push"
