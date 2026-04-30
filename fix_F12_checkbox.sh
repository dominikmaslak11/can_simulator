#!/bin/bash
# fix_F12_checkbox.sh – dodaje checkbox J1939 View do sniffera (precyzyjnie)
# Uruchom w katalogu can_simulator/

set -e

echo "=== Dodaję checkbox J1939 View do Sniffera ==="

if [ ! -f gui/tabs/sniffer_tab.py ]; then
    echo "BŁĄD: gui/tabs/sniffer_tab.py nie istnieje"
    exit 1
fi

python3 << 'PYEOF'
with open("gui/tabs/sniffer_tab.py", "r") as f:
    content = f.read()

changed = False

# ---------- 1. Dodaj zmienną sniffer_j1939_var ----------
# Szukamy linii: app.sniffer_bit_view_var = bit_view_var
# Po niej wstawiamy nową zmienną
old_line = "app.sniffer_bit_view_var = bit_view_var"
new_line = "app.sniffer_bit_view_var = bit_view_var\n    app.sniffer_j1939_var = tk.BooleanVar(value=False)"
if old_line in content and "app.sniffer_j1939_var" not in content:
    content = content.replace(old_line, new_line)
    print("1) Dodano zmienną app.sniffer_j1939_var.")
    changed = True
elif "app.sniffer_j1939_var" in content:
    print("1) Zmienna app.sniffer_j1939_var już istnieje.")
else:
    print("1) Nie znaleziono linii referencyjnej.")

# ---------- 2. Dodaj checkbox w toolbar ----------
# Szukamy linii z checkbuttonem "Widok bitowy" i wstawiamy po nim nowy checkbox
old_check = 'command=app.sniffer_ctrl.toggle_bit_view).pack(side=tk.LEFT, padx=5)'
new_check = ('command=app.sniffer_ctrl.toggle_bit_view).pack(side=tk.LEFT, padx=5)\n\n'
             '    j1939_var = tk.BooleanVar(value=False)\n'
             '    ttk.Checkbutton(toolbar, text="J1939 View", variable=app.sniffer_j1939_var,\n'
             '                    command=app.sniffer_ctrl.toggle_j1939_view).pack(side=tk.LEFT, padx=5)')
if old_check in content and 'text="J1939 View"' not in content:
    content = content.replace(old_check, new_check)
    print("2) Dodano checkbox J1939 View.")
    changed = True
elif 'text="J1939 View"' in content:
    print("2) Checkbox J1939 View już istnieje.")
else:
    # Awaryjnie: jeśli nie znaleziono, spróbuj wstawić za "Wczytaj DBC"
    old_dbc = "dbc_load_btn.pack(side=tk.LEFT, padx=5)"
    new_dbc = ('dbc_load_btn.pack(side=tk.LEFT, padx=5)\n'
               '    j1939_var = tk.BooleanVar(value=False)\n'
               '    ttk.Checkbutton(toolbar, text="J1939 View", variable=app.sniffer_j1939_var,\n'
               '                    command=app.sniffer_ctrl.toggle_j1939_view).pack(side=tk.LEFT, padx=5)')
    if old_dbc in content and 'text="J1939 View"' not in content:
        content = content.replace(old_dbc, new_dbc)
        print("2) Dodano checkbox J1939 View (awaryjnie za Wczytaj DBC).")
        changed = True
    else:
        print("2) Nie znaleziono miejsca na checkbox J1939 View.")

if changed:
    with open("gui/tabs/sniffer_tab.py", "w") as f:
        f.write(content)
    print("Zapisano zmiany.")
else:
    print("Nic nie zmieniono – checkbox może już być na miejscu.")
PYEOF

echo ""
echo "Sprawdzanie składni:"
python3 -m py_compile gui/tabs/sniffer_tab.py && echo "  sniffer_tab.py OK" || echo "  sniffer_tab.py BŁĄD"

echo ""
echo "=== Gotowe. Uruchom ./run.sh, checkbox J1939 View będzie w Snifferze. ==="
