#!/bin/bash
# fix_F13_final.sh – ostateczna naprawa sniffer_tab.py (wcięcie + checkbox J1939)
# Uruchom w katalogu can_simulator/

set -e

echo "=== Ostateczna naprawa sniffer_tab.py ==="

if [ ! -f gui/tabs/sniffer_tab.py ]; then
    echo "BŁĄD: gui/tabs/sniffer_tab.py nie istnieje."
    exit 1
fi

python3 << 'PYEOF'
with open("gui/tabs/sniffer_tab.py", "r") as f:
    content = f.read()

# 1. Naprawa wcięcia: z 8 spacji na 4
old_indent = "        app.sniffer_j1939_var = j1939_var"
new_indent = "    app.sniffer_j1939_var = j1939_var"
if old_indent in content:
    content = content.replace(old_indent, new_indent)
    print("Poprawiono wcięcie dla app.sniffer_j1939_var.")
elif "app.sniffer_j1939_var = j1939_var" in content:
    print("Linia app.sniffer_j1939_var ma poprawne wcięcie (lub niestandardowe).")
else:
    print("Nie znaleziono linii app.sniffer_j1939_var.")

# 2. Zastąp komentarz "# J1939 View checkbox dodany niżej" właściwym checkboxem
old_comment = "    # J1939 View checkbox dodany niżej"
new_checkbox = (
    '    ttk.Checkbutton(toolbar, text="J1939 View", variable=j1939_var,\n'
    '                    command=lambda: app.sniffer_ctrl.toggle_j1939_view()'
    ').pack(side=tk.LEFT, padx=5)'
)
if old_comment in content and "ttk.Checkbutton(toolbar, text=\"J1939 View\"" not in content:
    content = content.replace(old_comment, new_checkbox)
    print("Dodano checkbox J1939 View.")
elif "ttk.Checkbutton(toolbar, text=\"J1939 View\"" in content:
    print("Checkbox J1939 View już istnieje.")
else:
    print("UWAGA: nie znaleziono komentarza do zastąpienia.")

with open("gui/tabs/sniffer_tab.py", "w") as f:
    f.write(content)

print("Zapisano poprawiony sniffer_tab.py.")
PYEOF

# Sprawdzenie składni
python3 -m py_compile gui/tabs/sniffer_tab.py && echo "  sniffer_tab.py OK" || echo "  sniffer_tab.py BŁĄD"

echo ""
echo "=== Naprawa zakończona. Uruchom ./run.sh ==="
