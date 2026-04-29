#!/bin/bash
# update_F9a.sh – Faza 9a: GUI dla wyszukiwania sekwencji
# Uruchom w katalogu can_simulator/

set -e

echo "=== Wdrażanie Fazy 9a: GUI rozszerzone o sekwencje ==="

if [ ! -f gui/tabs/associative_tab.py ]; then
    echo "BŁĄD: gui/tabs/associative_tab.py nie istnieje."
    exit 1
fi

python3 << 'PYEOF'
with open("gui/tabs/associative_tab.py", "r") as f:
    content = f.read()

# 1. Dodajemy przycisk "Szukaj sekwencji" obok "Eksportuj wzorzec"
if "self.btn_sequence = ttk.Button" not in content:
    # Wstawiamy po btn_export
    old_export = 'self.btn_export.pack(side=tk.LEFT, padx=5)'
    if old_export in content:
        new_btn = old_export + '\n\n        self.btn_sequence = ttk.Button(ctrl_frame, text="Szukaj sekwencji",\n                                        command=self.search_sequence)\n        self.btn_sequence.pack(side=tk.LEFT, padx=5)'
        content = content.replace(old_export, new_btn)
        print("Dodano przycisk 'Szukaj sekwencji'.")
    else:
        print("Nie znaleziono btn_export.")
else:
    print("Przycisk sekwencji już istnieje.")

# 2. Rozszerzamy tabelę o kolumnę "Sekwencja"
if '"sequence"' not in content:
    # Kolumna będzie wyświetlać powiązane ID w tekście
    old_columns = 'columns = ("id", "byte", "value", "background", "confidence", "source")'
    new_columns = 'columns = ("id", "byte", "value", "background", "confidence", "source", "sequence")'
    content = content.replace(old_columns, new_columns)

    # Nagłówek kolumny
    old_heading = 'self.tree.heading("source", text="Źródło")'
    new_heading = 'self.tree.heading("source", text="Źródło")\n        self.tree.heading("sequence", text="Sekwencja")'
    content = content.replace(old_heading, new_heading)

    # Szerokość kolumny
    old_width = 'self.tree.column("source", width=100)'
    new_width = 'self.tree.column("source", width=100)\n        self.tree.column("sequence", width=150)'
    content = content.replace(old_width, new_width)
    print("Dodano kolumnę 'Sekwencja'.")
else:
    print("Kolumna 'Sekwencja' już istnieje.")

# 3. Metoda search_sequence
if "def search_sequence" not in content:
    new_method = '''
    def search_sequence(self):
        """Uruchamia wyszukiwanie sekwencji na podstawie najlepszego kandydata."""
        if not self.controller or not self.controller.running:
            messagebox.showwarning("Uwaga", "Najpierw rozpocznij uczenie.")
            return
        best = self.controller.get_best_candidate()
        if not best:
            messagebox.showinfo("Brak", "Nie znaleziono jeszcze głównego kandydata do sekwencji.")
            return
        sequences = self.controller.find_sequences(best, tolerance_ms=self.tolerance_var.get())
        if sequences:
            self._update_candidates_table_with_sequences(sequences)
            self.app.log(f"[Assoc] Znaleziono {len(sequences)} sekwencję(e).")
        else:
            self.app.log("[Assoc] Nie znaleziono żadnej powtarzalnej sekwencji.")

    def _update_candidates_table_with_sequences(self, sequences):
        """Wypełnia tabelę sekwencjami (zastępuje bieżącą zawartość)."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        for seq in sequences:
            main_id = seq.get("main_id", "")
            main_byte = seq.get("main_byte", "")
            seq_str = " -> ".join(seq.get("ids_order", []))
            self.tree.insert("", "end", values=(
                f"0x{main_id:X}" if isinstance(main_id, int) else str(main_id),
                main_byte,
                "sekw.",
                "-",
                f"{seq.get('confidence', 0):.1f}",
                "sekwencja",
                seq_str
            ))
'''
    if "def _refresh_loop" in content:
        content = content.replace("    def _refresh_loop", new_method + "\n    def _refresh_loop")
    else:
        content += "\n" + new_method
    print("Dodano metodę search_sequence.")
else:
    print("Metoda search_sequence już istnieje.")

with open("gui/tabs/associative_tab.py", "w") as f:
    f.write(content)
print("Zapisano zmiany w associative_tab.py.")
PYEOF

python3 -m py_compile gui/tabs/associative_tab.py && echo "  associative_tab.py OK" || echo "  associative_tab.py BŁĄD"

echo ""
echo "=== Faza 9a zakończona ==="
echo "Uruchom update_F9b.sh"
