#!/bin/bash
# update_F8a.sh – Faza 8a: Rozbudowa GUI o tryb wartościowy
# Uruchom w katalogu can_simulator/

set -e

echo "=== Wdrażanie Fazy 8a: GUI trybu wartościowego ==="

if [ ! -f gui/tabs/associative_tab.py ]; then
    echo "BŁĄD: gui/tabs/associative_tab.py nie istnieje. Uruchom najpierw poprzednie fazy."
    exit 1
fi

python3 << 'PYEOF'
import re

with open("gui/tabs/associative_tab.py", "r") as f:
    content = f.read()

# -------------------------------------------
# 1. NOWA SEKCJA W create_widgets:
#    Dodajemy ramkę dla trybu wartościowego
# -------------------------------------------
if "tryb_wartosci" not in content:
    value_section = '''
        # --- Tryb wartościowy ---
        value_frame = ttk.LabelFrame(frame, text="Tryb wartościowy (np. temperatura)", padding=5)
        value_frame.pack(fill=tk.X, pady=10)

        val_entry_frame = ttk.Frame(value_frame)
        val_entry_frame.pack(fill=tk.X, pady=2)
        ttk.Label(val_entry_frame, text="Wartość referencyjna:").pack(side=tk.LEFT)
        self.value_var = tk.StringVar()
        self.value_entry = ttk.Entry(val_entry_frame, textvariable=self.value_var, width=10)
        self.value_entry.pack(side=tk.LEFT, padx=5)
        self.value_entry.bind("<Return>", self.commit_value)
        self.btn_commit_value = ttk.Button(val_entry_frame, text="Zatwierdź",
                                           command=self.commit_value)
        self.btn_commit_value.pack(side=tk.LEFT, padx=5)

        # Historia wartości
        hist_frame = ttk.Frame(value_frame)
        hist_frame.pack(fill=tk.X, pady=2)
        ttk.Label(hist_frame, text="Historia:").pack(side=tk.LEFT)
        self.history_var = tk.StringVar(value="(pusta)")
        ttk.Label(hist_frame, textvariable=self.history_var, foreground="gray").pack(side=tk.LEFT, padx=5)
        self.btn_undo_value = ttk.Button(hist_frame, text="Cofnij ostatnią",
                                         command=self.undo_last_value)
        self.btn_undo_value.pack(side=tk.RIGHT, padx=5)

        # Nazwa zmiennej
        name_frame = ttk.Frame(value_frame)
        name_frame.pack(fill=tk.X, pady=2)
        ttk.Label(name_frame, text="Nazwa zmiennej:").pack(side=tk.LEFT)
        self.variable_name_var = tk.StringVar(value="")
        ttk.Entry(name_frame, textvariable=self.variable_name_var, width=20).pack(side=tk.LEFT, padx=5)

        # Typ zależności
        type_frame = ttk.Frame(value_frame)
        type_frame.pack(fill=tk.X, pady=2)
        ttk.Label(type_frame, text="Typ zależności:").pack(side=tk.LEFT)
        self.correlation_type_var = tk.StringVar(value="linear")
        ttk.Radiobutton(type_frame, text="Liniowa", variable=self.correlation_type_var,
                        value="linear").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(type_frame, text="Dowolna zmiana", variable=self.correlation_type_var,
                        value="any_change").pack(side=tk.LEFT, padx=5)
'''
    # Wstawiamy za ramką tolerancji (przed tabelą)
    insertion_point = 'self.tolerance_spin.pack(side=tk.LEFT, padx=5)'
    if insertion_point in content:
        content = content.replace(insertion_point + '\n',
                                  insertion_point + '\n' + value_section + '\n')
    else:
        print("UWAGA: Nie znaleziono punktu wstawienia sekcji wartościowej.")
    print("Dodano sekcję trybu wartościowego.")
else:
    print("Sekcja trybu wartościowego już istnieje.")

# -------------------------------------------
# 2. Dodajemy kolumnę "Źródło" do tabeli
# -------------------------------------------
if '"source"' not in content:
    old_columns = 'columns = ("id", "byte", "value", "background", "confidence")'
    new_columns = 'columns = ("id", "byte", "value", "background", "confidence", "source")'
    content = content.replace(old_columns, new_columns)

    # Dodajemy nagłówek i szerokość kolumny "source"
    if 'self.tree.heading("confidence"' in content:
        old_heading = 'self.tree.heading("confidence", text="Pewność (%)")'
        new_heading = 'self.tree.heading("confidence", text="Pewność (%)")\n        self.tree.heading("source", text="Źródło")'
        content = content.replace(old_heading, new_heading)

        old_col_conf = 'self.tree.column("confidence", width=80)'
        new_col_conf = 'self.tree.column("confidence", width=80)\n        self.tree.column("source", width=100)'
        content = content.replace(old_col_conf, new_col_conf)
        print("Dodano kolumnę 'Źródło' do tabeli.")
else:
    print("Kolumna 'Źródło' już istnieje.")

# -------------------------------------------
# 3. Dodajemy nowe metody: commit_value, undo_last_value
# -------------------------------------------
if "def commit_value" not in content:
    new_methods = '''
    def commit_value(self, event=None):
        """Zatwierdza wartość referencyjną i przekazuje do kontrolera."""
        if not self.controller or not self.controller.running:
            messagebox.showwarning("Uwaga", "Najpierw rozpocznij uczenie.")
            return
        val_str = self.value_var.get().strip()
        if not val_str:
            return
        try:
            val = float(val_str)
        except ValueError:
            messagebox.showerror("Błąd", "Wartość musi być liczbą.")
            return
        self.controller.commit_value(val)
        self.value_var.set("")
        self.app.log(f"[Assoc] Zatwierdzono wartość referencyjną: {val}")
        # Aktualizuj historię
        self._update_value_history()

    def undo_last_value(self):
        """Cofa ostatnią zatwierdzoną wartość."""
        if self.controller:
            self.controller.undo_last_value()
            self._update_value_history()
            self.app.log("[Assoc] Cofnięto ostatnią wartość referencyjną.")

    def _update_value_history(self):
        """Odświeża etykietę historii wartości."""
        if self.controller:
            vals = self.controller.get_value_history()
            if vals:
                self.history_var.set(" → ".join(str(v) for v in vals[-5:]))
            else:
                self.history_var.set("(pusta)")
'''
    # Wstawiamy przed _refresh_loop
    if "def _refresh_loop" in content:
        content = content.replace("    def _refresh_loop", new_methods + "\n    def _refresh_loop")
    else:
        content += "\n" + new_methods
    print("Dodano metody commit_value, undo_last_value, _update_value_history.")
else:
    print("Metody trybu wartościowego już istnieją.")

# -------------------------------------------
# 4. Aktualizacja _update_candidates_table o kolumnę źródła
# -------------------------------------------
if '"source"' in content and 'c.get("source"' not in content:
    old_table_fill = '''            self.tree.insert("", "end", values=(
                f"0x{c['id']:X}",
                c['byte'],
                f"0x{c['value']:02X}",
                bg,
                f"{c['confidence']:.1f}"
            ))'''
    new_table_fill = '''            src = c.get("source", "zdarzenie")
            self.tree.insert("", "end", values=(
                f"0x{c['id']:X}",
                c['byte'],
                f"0x{c['value']:02X}",
                bg,
                f"{c['confidence']:.1f}",
                src
            ))'''
    content = content.replace(old_table_fill, new_table_fill)
    print("Zaktualizowano wypełnianie tabeli o kolumnę źródła.")
else:
    print("Wypełnianie tabeli już zawiera kolumnę źródła.")

with open("gui/tabs/associative_tab.py", "w") as f:
    f.write(content)

print("Zapisano zmiany w associative_tab.py.")
PYEOF

python3 -m py_compile gui/tabs/associative_tab.py && echo "  associative_tab.py OK" || echo "  associative_tab.py BŁĄD"

echo ""
echo "=== Faza 8a zakończona ==="
echo "Uruchom kolejno: update_F8b.sh potem update_F8c.sh"
