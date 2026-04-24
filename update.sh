#!/bin/bash
# fix_E_optional.sh – naprawia brak importu Optional w ecu_emulator.py
# Uruchom w katalogu can_simulator/

set -e

echo "=== Naprawa ecu_emulator.py (brak Optional) ==="

if [ -f controllers/ecu_emulator.py ]; then
    # Sprawdź, czy już jest import Optional
    if grep -q 'from typing import Optional' controllers/ecu_emulator.py; then
        echo "Import Optional już istnieje."
    else
        # Dodajemy import na początku pliku (przed class)
        sed -i '1i from typing import Optional' controllers/ecu_emulator.py
        echo "Dodano 'from typing import Optional'."
    fi
else
    echo "Plik controllers/ecu_emulator.py nie istnieje – przerywam."
    exit 1
fi

# Sprawdzenie składni
echo ""
python3 -m py_compile controllers/ecu_emulator.py && echo "ecu_emulator.py – składnia OK" || echo "BŁĄD składni"

echo ""
echo "=== Możesz teraz uruchomić ./run.sh ==="
