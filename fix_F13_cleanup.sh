#!/bin/bash
# fix_F13_cleanup.sh – usuwa pozostałości po starych przyciskach w sniffer_tab.py
# Uruchom w katalogu can_simulator/

set -e

echo "=== Czyszczenie błędów w sniffer_tab.py ==="

if [ ! -f gui/tabs/sniffer_tab.py ]; then
    echo "BŁĄD: gui/tabs/sniffer_tab.py nie istnieje."
    exit 1
fi

python3 << 'PYEOF'
with open("gui/tabs/sniffer_tab.py", "r") as f:
    content = f.read()

# 1. Usuwamy błędne linie pakowania nieistniejących przycisków
lines_to_remove = [
    "export_parquet_btn.pack(side=tk.LEFT, padx=2)",
    "export_asc_btn.pack(side=tk.LEFT, padx=2)",
    "export_csv_btn.pack(side=tk.LEFT, padx=2)",
    "dbc_load_btn.pack(side=tk.LEFT, padx=5)",
]
for line in lines_to_remove:
    if line in content:
        content = content.replace(line + "\n", "")  # usuń całą linię
        print(f"Usunięto linię: {line}")

# 2. Usuwamy zduplikowaną definicję dbc_status_label
dup_label = '    dbc_status_label = ttk.Label(toolbar, text="Brak DBC")\n    dbc_status_label.pack(side=tk.LEFT, padx=2)\n'
count = content.count('dbc_status_label = ttk.Label(toolbar, text="Brak DBC")')
if count > 1:
    # Zostawiamy pierwsze wystąpienie, usuwamy drugie
    first_pos = content.find('dbc_status_label = ttk.Label(toolbar, text="Brak DBC")')
    second_pos = content.find('dbc_status_label = ttk.Label(toolbar, text="Brak DBC")', first_pos + 1)
    if second_pos != -1:
        # Znajdź koniec linii pakowania
        end_pack = content.find('.pack(side=tk.LEFT, padx=2)', second_pos)
        if end_pack != -1:
            end_line = content.find('\n', end_pack)
            content = content[:second_pos] + content[end_line+1:]
            print("Usunięto zduplikowaną dbc_status_label.")
else:
    print("Duplikat dbc_status_label nie znaleziony.")

# 3. Dodajemy przypisanie app.sniffer_j1939_var (jeśli go brakuje)
if "app.sniffer_j1939_var = j1939_var" not in content:
    # Szukamy komentarza "# j1939_var przypisane wyżej" i zastępujemy go właściwym przypisaniem
    old_comment = "    # j1939_var przypisane wyżej"
    new_assign = "    app.sniffer_j1939_var = j1939_var"
    if old_comment in content:
        content = content.replace(old_comment, new_assign)
        print("Dodano przypisanie app.sniffer_j1939_var.")
    else:
        # Wstawiamy w sekcji przypisań na końcu (przed sniffer_dbc_status)
        if "app.sniffer_dbc_status = dbc_status_label" in content:
            content = content.replace(
                "app.sniffer_dbc_status = dbc_status_label",
                "app.sniffer_j1939_var = j1939_var\n    app.sniffer_dbc_status = dbc_status_label"
            )
            print("Dodano przypisanie app.sniffer_j1939_var przed dbc_status_label.")
else:
    print("app.sniffer_j1939_var już przypisana.")

# 4. Usuwamy lokalną definicję toggle_j1939_view (jest niepotrzebna, mamy metodę w kontrolerze)
if "def toggle_j1939_view(self):" in content:
    # Znajdź początek i koniec tej funkcji
    func_start = content.find("def toggle_j1939_view(self):")
    # Szukamy kolejnej definicji funkcji lub końca pliku
    next_func = content.find("def ", func_start + 1)
    if next_func == -1:
        # Usuwamy do końca pliku
        content = content[:func_start].rstrip()
    else:
        content = content[:func_start] + content[next_func:]
    print("Usunięto lokalną definicję toggle_j1939_view.")

with open("gui/tabs/sniffer_tab.py", "w") as f:
    f.write(content)

print("Zapisano oczyszczony sniffer_tab.py.")
PYEOF

# Sprawdzenie składni
python3 -m py_compile gui/tabs/sniffer_tab.py && echo "  sniffer_tab.py OK" || echo "  sniffer_tab.py BŁĄD"

echo ""
echo "=== Czyszczenie zakończone. Uruchom ./run.sh ==="
