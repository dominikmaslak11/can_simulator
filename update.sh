#!/bin/bash

# Skrypt naprawia błędy w advanced_ml_tab.py:
# 1. Zastępuje forecast_frame -> frame w konfiguracjach grid
# 2. Przenosi canvas do wiersza 5 w setup_forecast_tab
# 3. Konfiguruje odpowiednie wiersze/kolumny

set -e

TARGET_FILE="gui/tabs/advanced_ml_tab.py"

if [ ! -f "$TARGET_FILE" ]; then
    if [ -f "../$TARGET_FILE" ]; then
        TARGET_FILE="../$TARGET_FILE"
    elif [ -f "../../$TARGET_FILE" ]; then
        TARGET_FILE="../../$TARGET_FILE"
    else
        echo "BŁĄD: Nie znaleziono advanced_ml_tab.py"
        exit 1
    fi
fi

echo "Plik docelowy: $TARGET_FILE"

# Kopia zapasowa
BACKUP_FILE="${TARGET_FILE}.backup_$(date +%Y%m%d_%H%M%S)"
cp "$TARGET_FILE" "$BACKUP_FILE"
echo "Kopia zapasowa: $BACKUP_FILE"

# 1. Zamiana forecast_frame na frame w liniach grid_rowconfigure/grid_columnconfigure
#    (dotyczy wszystkich trzech funkcji)
sed -i 's/forecast_frame\.grid_rowconfigure/frame.grid_rowconfigure/g' "$TARGET_FILE"
sed -i 's/forecast_frame\.grid_columnconfigure/frame.grid_columnconfigure/g' "$TARGET_FILE"

# 2. W setup_forecast_tab:
#    a) Zmieniamy row z 1 na 5 dla canvas
#    b) Dodajemy konfigurację wiersza 5 z weight=1 (po canvas)
#    c) Ustawiamy weight=0 dla wcześniejszych wierszy, aby nie rozciągały się

# Tworzymy tymczasowy plik z poprawkami dla funkcji setup_forecast_tab
awk '
/setup_forecast_tab\(app, frame\):/ { in_func = 1 }
in_func && /canvas\.get_tk_widget\(\)\.grid\(row=1,/ {
    sub(/row=1/, "row=5")
    print $0
    # Po tej linii dodajemy konfiguracje
    print "    frame.grid_rowconfigure(5, weight=1)"
    print "    frame.grid_rowconfigure(0, weight=0)"
    print "    frame.grid_rowconfigure(1, weight=0)"
    print "    frame.grid_rowconfigure(2, weight=0)"
    print "    frame.grid_rowconfigure(3, weight=0)"
    print "    frame.grid_rowconfigure(4, weight=0)"
    next
}
in_func && /^def / { in_func = 0 }
{ print }
' "$TARGET_FILE" > "${TARGET_FILE}.tmp"

mv "${TARGET_FILE}.tmp" "$TARGET_FILE"

echo "Poprawki zastosowane pomyślnie."
echo ""
echo "Zmiany:"
echo "  - 'forecast_frame' zastąpione przez 'frame' w konfiguracjach grid"
echo "  - Canvas w setup_forecast_tab przeniesiony do wiersza 5"
echo "  - Dodano odpowiednie grid_rowconfigure"
echo ""
echo "Możesz teraz uruchomić program: sudo ./run.sh"
