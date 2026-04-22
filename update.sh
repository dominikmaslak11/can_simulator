#!/bin/bash
# =============================================================================
# Etap 5: Ulepszenie Sniffera o dekodowanie DBC + dokumentacja użytkownika
# =============================================================================

set -e

BASE_DIR="$(pwd)"
SNIFFER_FILE="${BASE_DIR}/gui/tabs/sniffer_tab.py"
DBC_TAB_FILE="${BASE_DIR}/gui/tabs/dbc_manager_tab.py"
SESSION_MANAGER="${BASE_DIR}/session_manager.py"
USER_GUIDE="${BASE_DIR}/USER_GUIDE.md"
BACKUP_DIR="${BASE_DIR}/backup_dbc_sniffer_$(date +%Y%m%d_%H%M%S)"

echo "=== Ulepszanie Sniffera o dekodowanie DBC i tworzenie dokumentacji ==="

mkdir -p "$BACKUP_DIR"
cp "$SNIFFER_FILE" "$DBC_TAB_FILE" "$SESSION_MANAGER" "$BACKUP_DIR/" 2>/dev/null || true
echo "Kopie zapasowe w: $BACKUP_DIR"

# -----------------------------------------------------------------------------
# 1. Modyfikacja sniffer_tab.py – dodanie kolumny z dekodowaniem DBC
# -----------------------------------------------------------------------------
python3 - "$SNIFFER_FILE" <<'EOF'
import re
import sys

file_path = sys.argv[1]
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1.1 Zmiana definicji kolumn – dodajemy "decoded"
content = re.sub(
    r'columns = \("time", "id", "ext", "data", "dlc", "flags"\)',
    'columns = ("time", "id", "ext", "data", "decoded", "dlc", "flags")',
    content
)

# 1.2 Dodanie nagłówka i szerokości kolumny
if 'tree.heading("decoded"' not in content:
    content = re.sub(
        r'(tree\.heading\("data", text="Dane \(hex\)"\)\n)',
        r'\1        tree.heading("decoded", text="Zdekodowane (DBC)")\n',
        content
    )
    content = re.sub(
        r'(tree\.column\("data", width=\d+\)\n)',
        r'\1        tree.column("decoded", width=250)\n',
        content
    )

# 1.3 W pętli przetwarzającej ramki dodajemy dekodowanie
loop_pattern = r'(for addr, data, is_ext, ts in frames:\n)'
decode_block = '''        # Dekodowanie DBC
        decoded_str = ""
        if hasattr(app, 'dbc_manager') and app.dbc_manager.db:
            try:
                dec = app.dbc_manager.decode_frame(addr, bytes(data))
                if dec:
                    sigs = dec["signals"]
                    decoded_str = ", ".join(f"{k}={v:.2f}" for k, v in sigs.items())
            except:
                pass
'''
content = re.sub(loop_pattern, r'\1' + decode_block, content)

# 1.4 Modyfikacja tree.insert, aby dodać decoded_str
content = re.sub(
    r'(tree\.insert\("", tk\.END, values=\()([^)]+)(\))',
    r'\1\2 + (decoded_str,)\3',
    content
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("sniffer_tab.py zaktualizowany – dodano kolumnę z dekodowaniem DBC.")
EOF

# -----------------------------------------------------------------------------
# 2. Zapamiętywanie ostatnio wczytanego pliku DBC (session_manager.py)
# -----------------------------------------------------------------------------
if [ -f "$SESSION_MANAGER" ]; then
    python3 - "$SESSION_MANAGER" <<'EOF'
import re
import sys

file_path = sys.argv[1]
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Dodaj zapisywanie ścieżki DBC
save_pattern = r'(def save_session\(app\):.*?data = {.*?})'
if 'dbc_path' not in content:
    # Dodaj do słownika zapisywanych danych
    content = re.sub(
        r'("theme": app\.theme_var\.get\(\),)',
        r'\1\n        "dbc_path": getattr(app, "last_dbc_path", ""),',
        content
    )

# Dodaj odczytywanie ścieżki DBC przy wczytywaniu
load_pattern = r'(def load_session\(app\):.*?if "theme" in data:)'
if 'last_dbc_path' not in content:
    load_code = '''    # Wczytaj ścieżkę DBC jeśli istnieje
    if "dbc_path" in data and data["dbc_path"]:
        app.last_dbc_path = data["dbc_path"]
        # Automatycznie załaduj DBC jeśli manager istnieje
        if hasattr(app, 'dbc_manager'):
            app.dbc_manager.load_dbc(app.last_dbc_path)
'''
    content = re.sub(load_pattern, load_code + r'\n    \1', content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("session_manager.py zaktualizowany – zapamiętywanie ścieżki DBC.")
EOF
else
    echo "session_manager.py nie istnieje – pomijam zapamiętywanie DBC."
fi

# -----------------------------------------------------------------------------
# 3. Automatyczne wczytywanie ostatniego DBC przy starcie (dbc_manager_tab.py)
# -----------------------------------------------------------------------------
python3 - "$DBC_TAB_FILE" <<'EOF'
import re
import sys

file_path = sys.argv[1]
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Po utworzeniu zakładki, jeśli app.last_dbc_path istnieje, wczytaj DBC
if 'app.last_dbc_path' not in content:
    auto_load = '''
    # Automatyczne wczytanie ostatniego DBC
    if hasattr(app, 'last_dbc_path') and app.last_dbc_path:
        load_dbc(app.last_dbc_path)
        dbc_path_var.set(app.last_dbc_path)
'''
    # Wstawiamy na końcu setup_dbc_manager_tab
    content = re.sub(r'(\n    app\.dbc_signal_listbox = signal_listbox\n)', r'\1' + auto_load, content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("dbc_manager_tab.py zaktualizowany – autoładowanie ostatniego DBC.")
EOF

# -----------------------------------------------------------------------------
# 4. Utworzenie USER_GUIDE.md
# -----------------------------------------------------------------------------
cat > "$USER_GUIDE" << 'EOF'
# CAN Simulator – Instrukcja użytkownika

## Spis treści
1. [Wymagania](#wymagania)
2. [Instalacja](#instalacja)
3. [Uruchamianie](#uruchamianie)
4. [Zdalny monitoring (dla Wojtka)](#zdalny-monitoring-dla-wojtka)
5. [Używanie plików DBC](#używanie-plików-dbc)
6. [Mostek vCAN (WebSocket → wirtualny CAN)](#mostek-vcan-websocket--wirtualny-can)
7. [Rozwiązywanie problemów](#rozwiązywanie-problemów)

---

## Wymagania

- System Linux (z jądrem obsługującym `vcan`)
- Python 3.8+ (jeśli uruchamiasz bez Dockera)
- Docker (opcjonalnie, dla łatwego wdrożenia)

## Instalacja

### Sposób 1: Uruchomienie przez Docker (zalecane)
```bash
git clone https://github.com/TwojaNazwa/magistralaCAN.git
cd can_simulator
./run_docker.sh
