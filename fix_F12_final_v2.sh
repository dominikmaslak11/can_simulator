#!/bin/bash
# fix_F12_final_v2.sh – ostateczna poprawka testu J1939 i dodanie checkboxa J1939 do Sniffera (v2)
# Uruchamiamy w katalogu can_simulator/

set -e

echo "=== Naprawa fazy 12 – testy + checkbox J1939 View ==="

# 1. Poprawienie testów J1939 -------------------------------------------------
if [ -f tests/test_j1939.py ]; then
    cat > tests/test_j1939.py << 'TESTEOF'
"""Testy parsera J1939."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from parsers_j1939 import parse_j1939_id


def test_parse_j1939_id():
    result = parse_j1939_id(0x18FEF100)
    assert result["priority"] == 6
    assert result["pgn"] == 0xFEF1
    assert result["source_address"] == 0x00


def test_parse_another():
    result = parse_j1939_id(0x0CF0040B)
    assert result["priority"] == 3
    assert result["pgn"] == 0xF004
    assert result["source_address"] == 0x0B
TESTEOF
    echo "Testy J1939 zaktualizowane."
else
    echo "tests/test_j1939.py nie istnieje – tworzę."
    mkdir -p tests
    cat > tests/test_j1939.py << 'TESTEOF'
"""Testy parsera J1939."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from parsers_j1939 import parse_j1939_id


def test_parse_j1939_id():
    result = parse_j1939_id(0x18FEF100)
    assert result["priority"] == 6
    assert result["pgn"] == 0xFEF1
    assert result["source_address"] == 0x00


def test_parse_another():
    result = parse_j1939_id(0x0CF0040B)
    assert result["priority"] == 3
    assert result["pgn"] == 0xF004
    assert result["source_address"] == 0x0B
TESTEOF
fi

# 2. Dodanie checkboxa J1939 View w Snifferze (modyfikacja sniffer_tab.py) ------
if [ -f gui/tabs/sniffer_tab.py ]; then
    python3 << 'PYEOF'
content = open("gui/tabs/sniffer_tab.py", "r").read()

# 2a. Dodaj zmienną sniffer_j1939_var, jeśli jej nie ma
if "sniffer_j1939_var" not in content:
    if "self.sniffer_filter_var = tk.BooleanVar(value=False)" in content:
        content = content.replace(
            "self.sniffer_filter_var = tk.BooleanVar(value=False)",
            "self.sniffer_filter_var = tk.BooleanVar(value=False)\n        self.sniffer_j1939_var = tk.BooleanVar(value=False)"
        )
        print("Dodano zmienną sniffer_j1939_var.")
    else:
        print("Nie znaleziono sniffer_filter_var. Zmienna pominięta.")

# 2b. Wstaw checkbox do GUI – szukamy fragmentu z sniffer_filter_check.pack
if "sniffer_filter_check" in content and "j1939_view_check" not in content:
    old = "self.sniffer_filter_check.pack(side=tk.LEFT, padx=5)"
    new = 'self.sniffer_filter_check.pack(side=tk.LEFT, padx=5)\n        self.j1939_view_check = ttk.Checkbutton(filter_frame, text="J1939 View", variable=self.sniffer_j1939_var)\n        self.j1939_view_check.pack(side=tk.LEFT, padx=5)'
    content = content.replace(old, new)
    print("Dodano checkbox J1939 View do GUI.")
else:
    print("Checkbox J1939 View już istnieje lub nie znaleziono miejsca.")

# 2c. Dodaj metodę toggle_j1939_view
if "def toggle_j1939_view" not in content:
    method = '''
    def toggle_j1939_view(self):
        """Przełącza widok kolumn J1939 w snifferze."""
        if self.sniffer_j1939_var.get():
            self.app.log("[Sniffer] Widok J1939 włączony")
        else:
            self.app.log("[Sniffer] Widok J1939 wyłączony")
'''
    # wstaw przed istniejącą metodą toggle_filter
    if "def toggle_filter" in content:
        content = content.replace("    def toggle_filter", method + "\n    def toggle_filter")
    else:
        content += "\n" + method
    print("Dodano metodę toggle_j1939_view.")

open("gui/tabs/sniffer_tab.py", "w").write(content)
print("Zapisano zmiany w sniffer_tab.py.")
PYEOF
else
    echo "gui/tabs/sniffer_tab.py nie istnieje"
fi

# 3. Uruchom testy ------------------------------------------------------------
echo ""
echo "=== Uruchamianie testów J1939 ==="
python3 -m pytest tests/test_j1939.py -v 2>&1 || echo "UWAGA: Testy mogą wymagać pytest"

echo ""
echo "=== Poprawki zakończone. Uruchom aplikację ./run.sh ==="
