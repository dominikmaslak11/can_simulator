#!/bin/bash
# Ostateczna naprawa importu setup_anomaly_tab

APP_FILE="gui/app.py"
BACKUP="${APP_FILE}.backup_anomaly_import_final_$(date +%Y%m%d_%H%M%S)"

cp "$APP_FILE" "$BACKUP"
echo "Kopia zapasowa: $BACKUP"

python3 - "$APP_FILE" <<'EOF'
import re, sys
file_path = sys.argv[1]
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
import_added = False
for line in lines:
    new_lines.append(line)
    # Wstaw po imporcie advanced_ml_tab
    if 'from gui.tabs.advanced_ml_tab import setup_advanced_ml_tab' in line and not import_added:
        new_lines.append('from gui.tabs.anomaly_tab import setup_anomaly_tab\n')
        import_added = True

if not import_added:
    # Jeśli nie znaleziono advanced_ml_tab, dodaj na początku po importach z gui.tabs
    for i, line in enumerate(new_lines):
        if 'from gui.tabs' in line:
            new_lines.insert(i+1, 'from gui.tabs.anomaly_tab import setup_anomaly_tab\n')
            import_added = True
            break

if import_added:
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("Import setup_anomaly_tab został dodany.")
else:
    print("Nie znaleziono odpowiedniego miejsca. Dodaj ręcznie: from gui.tabs.anomaly_tab import setup_anomaly_tab")
EOF

echo "Gotowe. Uruchom: sudo ./run.sh"
