#!/bin/bash
# =============================================================================
# Etap 12: Powiadomienia Telegram dla zdalnego monitoringu
# =============================================================================

set -e

BASE_DIR="$(pwd)"
GUI_TAB_FILE="${BASE_DIR}/gui/tabs/remote_monitor_tab.py"
SERVER_FILE="${BASE_DIR}/broadcaster/server.py"
BACKUP_DIR="${BASE_DIR}/backup_telegram_$(date +%Y%m%d_%H%M%S)"

echo "=== Etap 12: Powiadomienia Telegram ==="

mkdir -p "$BACKUP_DIR"
cp "$GUI_TAB_FILE" "$SERVER_FILE" "$BACKUP_DIR/" 2>/dev/null || true
echo "Kopie zapasowe w: $BACKUP_DIR"

# -----------------------------------------------------------------------------
# 1. Aktualizacja GUI – dodanie pól Telegram
# -----------------------------------------------------------------------------
python3 - "$GUI_TAB_FILE" <<'EOF'
import re, sys
file_path = sys.argv[1]
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1.1 Dodajemy atrybuty w __init__
init_pattern = r'(def __init__\(self, parent, app\):.*?)(self\._create_widgets)'
telegram_attrs = '''
        self.telegram_token_var = tk.StringVar()
        self.telegram_chat_id_var = tk.StringVar()
        self.enable_telegram_var = tk.BooleanVar(value=False)
'''
content = re.sub(init_pattern, r'\1' + telegram_attrs + r'\n        \2', content, flags=re.DOTALL)

# 1.2 Dodajemy widgety w GUI (po checkboxie logowania)
telegram_widgets = '''
        ttk.Separator(frame, orient='horizontal').grid(row=10, column=0, columnspan=2, sticky='ew', pady=10)
        ttk.Label(frame, text="Powiadomienia Telegram:", font=('TkDefaultFont', 10, 'bold')).grid(row=11, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(frame, text="Włącz powiadomienia Telegram", variable=self.enable_telegram_var).grid(row=12, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        ttk.Label(frame, text="Bot Token:").grid(row=13, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(frame, textvariable=self.telegram_token_var, width=50).grid(row=13, column=1, padx=5)
        ttk.Label(frame, text="Chat ID:").grid(row=14, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(frame, textvariable=self.telegram_chat_id_var, width=30).grid(row=14, column=1, padx=5)
'''
content = re.sub(r'(ttk\.Checkbutton\(frame, text="Zapisuj zdalne operacje do pliku".*?\n)',
                r'\1' + telegram_widgets, content, flags=re.DOTALL)

# 1.3 W start_server przekazujemy ustawienia do serwera
start_pattern = r'(self\.server = CANWebSocketServer\(port=port, token=token, ssl_context=ssl_ctx\))'
replacement = '''        self.server = CANWebSocketServer(port=port, token=token, ssl_context=ssl_ctx)
        self.server.allowed_client_ids = allowed_ids
        self.server.log_to_file = self.log_to_file_var.get()
        self.server.can_interface = self.app.can
        self.server.incoming_filter_ids = incoming_filter
        # Telegram
        if self.enable_telegram_var.get():
            self.server.telegram_token = self.telegram_token_var.get().strip()
            self.server.telegram_chat_id = self.telegram_chat_id_var.get().strip()
        else:
            self.server.telegram_token = None
            self.server.telegram_chat_id = None
'''
content = re.sub(start_pattern, replacement, content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("remote_monitor_tab.py zaktualizowany – GUI Telegram.")
EOF

# -----------------------------------------------------------------------------
# 2. Aktualizacja server.py – dodanie funkcji wysyłania do Telegrama
# -----------------------------------------------------------------------------
python3 - "$SERVER_FILE" <<'EOF'
import re, sys
file_path = sys.argv[1]
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 2.1 Dodajemy import urllib
if 'import urllib.request' not in content:
    content = re.sub(r'(import ssl)', r'\1\nimport urllib.request\nimport urllib.parse', content)

# 2.2 Dodajemy atrybuty w __init__
init_pattern = r'(def __init__\(self.*?\):.*?)(self\._running = False)'
telegram_attrs = '''
        self.telegram_token = None
        self.telegram_chat_id = None
'''
content = re.sub(init_pattern, r'\1' + telegram_attrs + r'\n        \2', content, flags=re.DOTALL)

# 2.3 Dodajemy metodę _send_telegram
telegram_method = '''
    def _send_telegram(self, message):
        """Wysyła wiadomość do skonfigurowanego czatu Telegram."""
        if not self.telegram_token or not self.telegram_chat_id:
            return
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = urllib.parse.urlencode({
                "chat_id": self.telegram_chat_id,
                "text": f"🚗 CAN Simulator\\n{message}",
                "parse_mode": "HTML"
            }).encode("utf-8")
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.getcode() != 200:
                    logger.warning(f"Telegram odpowiedział kodem {resp.getcode()}")
        except Exception as e:
            logger.error(f"Błąd wysyłania do Telegram: {e}")
'''
if '_send_telegram' not in content:
    content = re.sub(r'(    async def stop\(self\):)', telegram_method + r'\n\n\1', content)

# 2.4 W _handler wysyłamy powiadomienie o połączeniu/rozłączeniu
handler_conn = r'(logger\.info\(f"Klient dodany.*?\)\))'
content = re.sub(handler_conn,
                r'\1\n        self._send_telegram(f"🟢 Klient połączony: {websocket.remote_address}")',
                content)

handler_disconn = r'(logger\.info\(f"Klient rozłączony.*?\)\))'
content = re.sub(handler_disconn,
                r'\1\n        self._send_telegram(f"🔴 Klient rozłączony: {websocket.remote_address}")',
                content)

# 2.5 W _handle_incoming_frame przy błędzie wysyłania na CAN
error_send = r'(logger\.error\(f"Błąd wysyłania na CAN: {msg}"\))'
content = re.sub(error_send,
                r'\1\n            self._send_telegram(f"❌ Błąd wysyłania na CAN: {msg}")',
                content)

# 2.6 W sniffer_tab.py (już zintegrowane) – przy walidacji DBC dodajemy powiadomienie
# Zrobimy to w osobnym kroku, aby nie komplikować.

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("server.py zaktualizowany – powiadomienia Telegram.")
EOF

# -----------------------------------------------------------------------------
# 3. Integracja z walidacją DBC (sniffer_tab.py) – opcjonalnie, ale warto
# -----------------------------------------------------------------------------
SNIFFER_FILE="${BASE_DIR}/gui/tabs/sniffer_tab.py"
if [ -f "$SNIFFER_FILE" ]; then
    python3 - "$SNIFFER_FILE" <<'EOF'
import re, sys
file_path = sys.argv[1]
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Szukamy miejsca, gdzie logowane jest ostrzeżenie o wartości poza zakresem DBC
pattern = r'(app\.log\(f"\[DBC\] Wartość poza zakresem: {sig_name} = {value:\.2f}.*?"\))'
if re.search(pattern, content):
    # Dodajemy wywołanie Telegram, jeśli serwer jest uruchomiony
    telegram_call = r'''
                        if hasattr(app, 'remote_monitor_tab') and app.remote_monitor_tab.server:
                            app.remote_monitor_tab.server._send_telegram(
                                f"⚠️ DBC: {sig_name} = {value:.2f} (zakres: {min_val}..{max_val})"
                            )'''
    content = re.sub(pattern, r'\1' + telegram_call, content)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("sniffer_tab.py zaktualizowany – alerty DBC do Telegram.")
else:
    print("UWAGA: Nie znaleziono bloku walidacji DBC w sniffer_tab.py – pomijam.")
EOF
fi

# -----------------------------------------------------------------------------
# 4. Dodanie referencji do RemoteMonitorTab w app.py (dla dostępu z sniffera)
# -----------------------------------------------------------------------------
APP_FILE="${BASE_DIR}/gui/app.py"
if [ -f "$APP_FILE" ]; then
    python3 - "$APP_FILE" <<'EOF'
import re, sys
file_path = sys.argv[1]
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# W setup_remote_monitor_tab zapisujemy referencję do obiektu
pattern = r'(def setup_remote_monitor_tab\(app, parent_frame\):\n.*?)(RemoteMonitorTab\(parent_frame, app\))'
replacement = r'\1    tab = \2\n    app.remote_monitor_tab = tab\n    return tab'
content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Dodajemy atrybut w __init__
init_pattern = r'(self\.theme_var = tk\.StringVar\(value="light"\)\n)'
content = re.sub(init_pattern, r'\1        self.remote_monitor_tab = None\n', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("app.py zaktualizowany – referencja do RemoteMonitorTab.")
EOF
fi

echo ""
echo "=== Etap 12 zakończony pomyślnie ==="
echo "Nowe funkcje:"
echo "  - Konfiguracja bota Telegram (Token i Chat ID) w GUI"
echo "  - Powiadomienia o połączeniu/rozłączeniu klienta"
echo "  - Alerty przy wartościach DBC poza zakresem"
echo "  - Alerty przy błędach wysyłania na CAN"
echo ""
echo "Aby skonfigurować Telegram:"
echo "  1. Utwórz bota przez @BotFather i skopiuj token."
echo "  2. Znajdź swój Chat ID (np. przez @userinfobot)."
echo "  3. Wpisz dane w zakładce 'Zdalny monitoring' i zaznacz 'Włącz powiadomienia Telegram'."
echo ""
echo "Uruchom aplikację: sudo ./run.sh"
echo "Wypchnij zmiany na GitHub:"
echo "  git add -A"
echo "  git commit -m 'Etap 12: Powiadomienia Telegram dla zdalnego monitoringu'"
echo "  git push"
