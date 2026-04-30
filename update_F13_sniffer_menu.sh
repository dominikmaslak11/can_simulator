#!/bin/bash
# update_F13_sniffer_menu.sh – Optymalizacja paska narzędziowego Sniffera (menu rozwijane)
# Uruchom w katalogu can_simulator/

set -e

echo "=== Faza 13: Menu rozwijane w Snifferze ==="

if [ ! -f gui/tabs/sniffer_tab.py ]; then
    echo "BŁĄD: gui/tabs/sniffer_tab.py nie istnieje."
    exit 1
fi

python3 << 'PYEOF'
from pathlib import Path

path = Path("gui/tabs/sniffer_tab.py")
content = path.read_text()

# 1. Sprawdź, czy już nie ma menu (zabezpieczenie przed ponownym uruchomieniem)
if "Menubutton(toolbar, text=\"Eksportuj\"" in content:
    print("Menu Eksportuj już istnieje – pomijam.")
else:
    # Usuń stare przyciski eksportu (linijki z ich tworzeniem i pakowaniem)
    lines = content.split('\n')
    new_lines = []
    skip_until_pack = False
    removed_exports = False
    removed_dbc = False

    for line in lines:
        # Usuwamy przyciski eksportu
        if "export_btn = ttk.Button(toolbar, text=\"Eksportuj (log)\", command=app.sniffer_ctrl.export_sniffer)" in line:
            skip_until_pack = True
            removed_exports = True
            continue
        if "export_csv_btn = ttk.Button(toolbar, text=\"Eksportuj do CSV\"" in line:
            skip_until_pack = True
            continue
        if "export_asc_btn = ttk.Button(toolbar, text=\"Eksportuj do ASC\"" in line:
            skip_until_pack = True
            continue
        if "export_parquet_btn = ttk.Button(toolbar, text=\"Eksportuj do Parquet\"" in line:
            skip_until_pack = True
            continue
        if "export_mdf4_btn = ttk.Button(toolbar, text=\"Eksportuj do MDF4\"" in line:
            skip_until_pack = True
            continue
        if skip_until_pack and ".pack(side=tk.LEFT, padx=" in line and ("export_btn" in line or "export_csv_btn" in line or "export_asc_btn" in line or "export_parquet_btn" in line or "export_mdf4_btn" in line):
            skip_until_pack = False
            continue

        # Usuwamy również przyciski DBC
        if "dbc_load_btn = ttk.Button(toolbar, text=\"Wczytaj DBC\"" in line:
            skip_until_pack = True
            removed_dbc = True
            continue
        if "dbc_edit_btn = ttk.Button(toolbar, text=\"Edytor DBC\"" in line:
            skip_until_pack = True
            continue
        if skip_until_pack and ".pack(side=tk.LEFT, padx=" in line and ("dbc_load_btn" in line or "dbc_edit_btn" in line):
            skip_until_pack = False
            continue

        new_lines.append(line)

    if removed_exports or removed_dbc:
        # Wstawiamy nowe menu w odpowiednie miejsce
        # Szukamy linii, gdzie kończy się toolbar (przed 'filter_var = tk.BooleanVar')
        insert_idx = None
        for i, line in enumerate(new_lines):
            if "filter_var = tk.BooleanVar(value=False)" in line:
                insert_idx = i
                break
        if insert_idx is None:
            # wstawimy na końcu toolbar – trudniej, więc szukamy 'dbc_status_label'
            for i, line in enumerate(new_lines):
                if "dbc_status_label = ttk.Label" in line:
                    insert_idx = i
                    break
        if insert_idx is not None:
            # Przygotuj blok kodu dla menu Eksportuj
            export_menu_block = '''
    # Menu Eksportuj
    export_menu_btn = ttk.Menubutton(toolbar, text="Eksportuj")
    export_menu = tk.Menu(export_menu_btn, tearoff=0)
    export_menu.add_command(label="Eksportuj (log)", command=app.sniffer_ctrl.export_sniffer)
    export_menu.add_command(label="Eksportuj do CSV", command=app.sniffer_ctrl.export_csv)
    export_menu.add_command(label="Eksportuj do ASC", command=app.sniffer_ctrl.export_asc)
    export_menu.add_command(label="Eksportuj do Parquet", command=app.sniffer_ctrl.export_parquet)
    export_menu.add_command(label="Eksportuj do MDF4", command=app.sniffer_ctrl.export_mdf4)
    export_menu_btn["menu"] = export_menu
    export_menu_btn.pack(side=tk.LEFT, padx=2)
'''
            dbc_menu_block = '''
    # Menu DBC
    dbc_menu_btn = ttk.Menubutton(toolbar, text="DBC")
    dbc_menu = tk.Menu(dbc_menu_btn, tearoff=0)
    dbc_menu.add_command(label="Wczytaj DBC", command=app.sniffer_ctrl.load_dbc_file)
    dbc_menu.add_command(label="Edytor DBC", command=app.sniffer_ctrl.open_dbc_editor)
    dbc_menu_btn["menu"] = dbc_menu
    dbc_menu_btn.pack(side=tk.LEFT, padx=2)
    dbc_status_label = ttk.Label(toolbar, text="Brak DBC")
    dbc_status_label.pack(side=tk.LEFT, padx=2)
'''
            # Wstawiamy bloki przed filter_var
            new_lines.insert(insert_idx, export_menu_block)
            if removed_dbc:
                # dbc_status_label był wcześniej usuwany? Nie usuwaliśmy go, więc może wystarczy dodać menu DBC przed nim
                # ale insert_idx może być za wcześnie. Poszukajmy linii 'dbc_status_label'
                for i, line in enumerate(new_lines):
                    if "dbc_status_label = ttk.Label" in line:
                        # wstaw przed tą linią
                        new_lines.insert(i, dbc_menu_block)
                        break
        else:
            print("Nie znaleziono odpowiedniego miejsca na wstawienie menu.")

        content = '\n'.join(new_lines)
        path.write_text(content)
        print("Zastąpiono przyciski eksportu i DBC rozwijanymi menu.")
    else:
        print("Nie znaleziono przycisków do zastąpienia.")

print("Zakończono modyfikację sniffer_tab.py")
PYEOF

# Sprawdzenie składni
python3 -m py_compile gui/tabs/sniffer_tab.py && echo "  sniffer_tab.py OK" || echo "  sniffer_tab.py BŁĄD"

echo ""
echo "=== Faza 13 wdrożona ==="
echo "W Snifferze przyciski Eksportu i DBC zostały zastąpione rozwijanymi menu."
