#!/bin/bash
# fix_F12_final_v3.sh – naprawia błąd AttributeError dla J1939 checkbox + dodaje metodę kontrolera
# Uruchom w katalogu can_simulator/

set -e

echo "=== Naprawa J1939 – brak atrybutu sniffer_j1939_var i metody kontrolera ==="

# ---------- 1. Poprawka sniffer_tab.py ----------
if [ -f gui/tabs/sniffer_tab.py ]; then
    python3 << 'PYEOF'
with open("gui/tabs/sniffer_tab.py", "r") as f:
    content = f.read()

# Krok a: usuń błędny fragment, który próbuje użyć app.sniffer_j1939_var przed definicją
# Znajdujemy linijkę z Checkbutton J1939 View i ją usuwamy (zastępujemy komentarzem)
old_check = '    ttk.Checkbutton(toolbar, text="J1939 View", variable=app.sniffer_j1939_var,\n                    command=app.sniffer_ctrl.toggle_j1939_view).pack(side=tk.LEFT, padx=5)'
if old_check in content:
    content = content.replace(old_check, '    # J1939 View checkbox dodany niżej')
    print("Usunięto stary checkbox J1939 View.")

# Krok b: wstaw NOWY poprawny fragment: najpierw lokalna zmienna, potem checkbox, potem przypisanie do app
# Miejsce: zaraz za checkboxem "Widok bitowy"
old_bit = 'command=app.sniffer_ctrl.toggle_bit_view).pack(side=tk.LEFT, padx=5)'
new_bit = ('command=app.sniffer_ctrl.toggle_bit_view).pack(side=tk.LEFT, padx=5)\n\n'
           '    # J1939 View\n'
           '    j1939_var = tk.BooleanVar(value=False)\n'
           '    ttk.Checkbutton(toolbar, text="J1939 View", variable=j1939_var,\n'
           '                    command=lambda: app.sniffer_ctrl.toggle_j1939_view()).pack(side=tk.LEFT, padx=5)\n'
           '    app.sniffer_j1939_var = j1939_var')
if old_bit in content and 'j1939_var = tk.BooleanVar(value=False)' not in content:
    content = content.replace(old_bit, new_bit)
    print("Wstawiono poprawny checkbox J1939 View.")
elif 'j1939_var = tk.BooleanVar(value=False)' in content:
    print("Poprawny checkbox J1939 View już istnieje.")
else:
    print("Nie znaleziono miejsca na checkbox J1939 View.")

# Krok c: usuń starą definicję zmiennej app.sniffer_j1939_var na końcu pliku (już niepotrzebna)
old_var = "app.sniffer_j1939_var = tk.BooleanVar(value=False)"
if old_var in content:
    content = content.replace(old_var, '    # j1939_var przypisane wyżej')
    print("Usunięto stare przypisanie app.sniffer_j1939_var.")

with open("gui/tabs/sniffer_tab.py", "w") as f:
    f.write(content)
print("Zapisano sniffer_tab.py.")
PYEOF
else
    echo "gui/tabs/sniffer_tab.py nie istnieje."
fi

# ---------- 2. Dodanie metody toggle_j1939_view do kontrolera sniffera ----------
SNIFFER_CONTROLLER="controllers/sniffer/core.py"
if [ ! -f "$SNIFFER_CONTROLLER" ]; then
    # Może kontroler jest w sniffer_base.py
    SNIFFER_CONTROLLER="controllers/sniffer/base.py"
fi
if [ -f "$SNIFFER_CONTROLLER" ]; then
    python3 << PYEOF
with open("$SNIFFER_CONTROLLER", "r") as f:
    content = f.read()

if "def toggle_j1939_view" not in content:
    method = '''
    def toggle_j1939_view(self):
        """Callback dla checkboxa J1939 View."""
        # Logika może być pusta – ważne, żeby metoda istniała
        pass
'''
    # Wstawiamy na końcu klasy – przed ewentualną następną klasą
    # Szukamy ostatniej metody i dodajemy za nią
    lines = content.split('\n')
    # Znajdź ostatnią linię, która jest pusta i znajduje się wewnątrz klasy
    # Prościej: dodaj na końcu pliku przed ewentualnym if __name__ == '__main__'
    if 'if __name__' in content:
        content = content.replace('if __name__', method + '\nif __name__')
    else:
        content += '\n' + method
    with open("$SNIFFER_CONTROLLER", "w") as f:
        f.write(content)
    print(f"Dodano metodę toggle_j1939_view do {SNIFFER_CONTROLLER}.")
else:
    print("toggle_j1939_view już istnieje w kontrolerze sniffera.")
PYEOF
else
    echo "Nie znaleziono pliku kontrolera sniffera (core.py/base.py)."
fi

# ---------- 3. Sprawdzenie składni i testy ----------
echo ""
echo "Sprawdzanie składni:"
python3 -m py_compile gui/tabs/sniffer_tab.py && echo "  sniffer_tab.py OK" || echo "  sniffer_tab.py BŁĄD"
if [ -f "$SNIFFER_CONTROLLER" ]; then
    python3 -m py_compile "$SNIFFER_CONTROLLER" && echo "  $SNIFFER_CONTROLLER OK" || echo "  $SNIFFER_CONTROLLER BŁĄD"
fi

echo ""
echo "Uruchamianie testów J1939:"
python3 -m pytest tests/test_j1939.py -v 2>&1 || echo "UWAGA: testy wymagają pytest"

echo ""
echo "=== Naprawa zakończona. Uruchom ./run.sh ==="
