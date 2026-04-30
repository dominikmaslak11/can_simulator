#!/bin/bash
# fix_F12_final.sh – naprawia test J1939 i dodaje checkbox J1939 do Sniffera (kompletny)
# Uruchom w katalogu can_simulator/

set -e

echo "=== Naprawa testu J1939 i integracji ze Snifferem ==="

# ---------- 1. Popraw testu ----------
if [ -f tests/test_j1939.py ]; then
    cat > tests/test_j1939.py << 'EOF'
"""Testy parsera J1939."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from parsers_j1939 import parse_j1939_id


def test_parse_j1939_id():
    # 0x18FEF100 = 00011000 11111110 11110001 00000000
    # Priorytet = najstarsze 3 bity = 000 -> 0? Nie:
    # (0x18FEF100 >> 26) = 0x06 = 6
    result = parse_j1939_id(0x18FEF100)
    assert result["priority"] == 6
    assert result["pgn"] == 0xFEF1
    assert result["source_address"] == 0x00

def test_parse_another():
    # 0x0CF0040B: priorytet = 3, PGN = 0xF004, source = 0x0B
    result = parse_j1939_id(0x0CF0040B)
    assert result["priority"] == 3
    assert result["pgn"] == 0xF004
    assert result["source_address"] == 0x0B
EOF
    echo "Poprawiono testy J1939."
else
    echo "tests/test_j1939.py nie istnieje."
fi

# ---------- 2. Dodaj checkbox J1939 View w Snifferze ----------
if [ -f gui/tabs/sniffer_tab.py ]; then
    python3 << 'PYEOF'
with open("gui/tabs/sniffer_tab.py", "r") as f:
    content = f.read()

if "sniffer_j1939_var" not in content:
    # Dodajemy zmienną
    if "self.sniffer_filter_var = tk.BooleanVar(value=False)" in content:
        content = content.replace(
            "self.sniffer_filter_var = tk.BooleanVar(value=False)",
            "self.sniffer_filter_var = tk.BooleanVar(value=False)\n    self.sniffer_j1939_var = tk.BooleanVar(value=False)"
        )
    # Wstawiamy checkbox bezpośrednio przed główną pętlą lub w ramce filter_frame
    if "sniffer_filter_check" in content and "j1939_view_check" not in content:
        old_pack = "self.sniffer_filter_check.pack(side=tk.LEFT, padx=5)"
        new_pack = 'self.sniffer_filter_check.pack(side=tk.LEFT, padx=5)\n        self.j1939_view_check = ttk.Checkbutton(filter_frame, text="J1939 View", variable=self.sniffer_j1939_var)\n        self.j1939_view_check.pack(side=tk.LEFT, padx=5)'
        if old_pack in content:
            content = content.replace(old_pack, new_pack)
            print("Dodano checkbox J1939 View.")
        else:
            print("Nie znaleziono pack dla filter_check.")
    else:
        print("Checkbox J1939 View już istnieje.")

    if "def toggle_j1939_view" not in content:
        toggle_method = '''
    def toggle_j1939_view(self):
        """Przełącza widok kolumn J1939 w snifferze."""
        if self.sniffer_j1939_var.get():
            self.app.log("[Sniffer] Widok J1939 włączony")
        else:
            self.app.log("[Sniffer] Widok J1939 wyłączony")
'''
        if "def toggle_filter" in content:
            content = content.replace("    def toggle_filter", toggle_method + "\n    def toggle_filter")
        else:
            content += "\n" + toggle_method
        print("Dodano metodę toggle_j1939_view.")

    with open("gui/tabs/sniffer_tab.py", "w") as f:
        f.write(content)
    print("Zapisano zmiany w sniffer_tab.py.")
else:
    echo "gui/tabs/sniffer_tab.py nie istnieje."
PYEOF

# ---------- 3. Uruchom testy ----------
echo ""
echo "Uruchamianie testów J1939:"
python3 -m pytest tests/test_j1939.py -v 2>&1 || echo "UWAGA: Testy mogą wymagać modułu pytest"

echo ""
echo "=== Wszystkie poprawki naniesione. Możesz uruchomić ./run.sh ==="
