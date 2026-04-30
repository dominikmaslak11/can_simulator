#!/bin/bash
# update_F14b.sh – Faza 14b: Przełącznik trybu CAN/J1939 w GUI i integracja kontrolera
# Uruchom w katalogu can_simulator/

set -e

echo "=== Wdrażanie Fazy 14b: GUI – przełącznik CAN / J1939 ==="

if [ ! -f gui/tabs/associative_tab.py ]; then
    echo "BŁĄD: gui/tabs/associative_tab.py nie istnieje."
    exit 1
fi

python3 << 'PYEOF'
with open("gui/tabs/associative_tab.py", "r") as f:
    content = f.read()

# ------------------------------------------------------------
# 1. Import J1939AssociativeController (jeśli go nie ma)
# ------------------------------------------------------------
if "J1939AssociativeController" not in content:
    old_import = "from controllers.associative_controller import AssociativeController"
    new_import = ("from controllers.associative_controller import AssociativeController\n"
                  "from controllers.j1939_associative_controller import J1939AssociativeController")
    content = content.replace(old_import, new_import)
    print("Dodano import J1939AssociativeController.")
else:
    print("Import J1939AssociativeController już istnieje.")

# ------------------------------------------------------------
# 2. Dodanie zmiennej trybu (self.bus_mode_var) w __init__
# ------------------------------------------------------------
if "self.bus_mode_var" not in content:
    init_line = "self.controller = None"
    new_init = 'self.controller = None\n        self.bus_mode_var = tk.StringVar(value="can")'
    content = content.replace(init_line, new_init)
    print("Dodano zmienną bus_mode_var.")
else:
    print("Zmienna bus_mode_var już istnieje.")

# ------------------------------------------------------------
# 3. Dodanie ramki z przełącznikiem trybu w create_widgets
#    (wstawiamy za nagłówkiem, przed sekcją sterowania)
# ------------------------------------------------------------
if "Tryb magistrali:" not in content:
    mode_section = '''
        # --- Tryb magistrali (CAN / J1939) ---
        mode_frame = ttk.LabelFrame(frame, text="Tryb magistrali", padding=5)
        mode_frame.pack(fill=tk.X, pady=5)
        ttk.Radiobutton(mode_frame, text="CAN 2.0 (11/29-bit)", variable=self.bus_mode_var,
                        value="can", command=self.on_bus_mode_changed).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="J1939", variable=self.bus_mode_var,
                        value="j1939", command=self.on_bus_mode_changed).pack(side=tk.LEFT, padx=5)
'''
    # Wstawiamy za nagłówkiem
    old_header = 'font=(\'Arial\', 12, \'bold\')).pack(anchor=tk.W, pady=(0,10))'
    new_header = old_header + '\n' + mode_section
    content = content.replace(old_header, new_header)
    print("Dodano sekcję trybu magistrali.")
else:
    print("Sekcja trybu magistrali już istnieje.")

# ------------------------------------------------------------
# 4. Dodanie metody on_bus_mode_changed
# ------------------------------------------------------------
if "def on_bus_mode_changed" not in content:
    method = '''
    def on_bus_mode_changed(self):
        """Reaguje na zmianę trybu CAN / J1939."""
        mode = self.bus_mode_var.get()
        self.app.log(f"[Assoc] Przełączono tryb magistrali: {mode}")
        # Zatrzymaj obecny kontroler, jeśli działa
        if self.controller and self.controller.running:
            self.controller.stop()
        # Utwórz nowy kontroler odpowiedniego typu
        if mode == "j1939":
            self.controller = J1939AssociativeController(self.app)
        else:
            self.controller = AssociativeController(self.app)
        self.controller.set_tolerance(self.tolerance_var.get())
        # Jeśli uczenie było włączone, uruchom ponownie
        if self.btn_start['state'] == 'disabled':
            self.controller.start()
        self.app.log(f"[Assoc] Używany kontroler: {type(self.controller).__name__}")
'''
    # Wstawiamy przed start_learning
    if "def start_learning" in content:
        content = content.replace("    def start_learning", method + "\n    def start_learning")
        print("Dodano metodę on_bus_mode_changed.")
    else:
        print("Nie znaleziono start_learning – metoda nie została dodana.")
else:
    print("Metoda on_bus_mode_changed już istnieje.")

# ------------------------------------------------------------
# 5. Modyfikacja start_learning – tworzenie kontrolera zależnie od trybu
# ------------------------------------------------------------
if "J1939AssociativeController(self.app)" not in content:
    old_start = '''    def start_learning(self):
        if not self.app.can.connected:
            messagebox.showerror("Błąd", "Połącz się z CAN przed rozpoczęciem uczenia.")
            return
        if self.controller is None:
            self.controller = AssociativeController(self.app)'''
    new_start = '''    def start_learning(self):
        if not self.app.can.connected:
            messagebox.showerror("Błąd", "Połącz się z CAN przed rozpoczęciem uczenia.")
            return
        if self.controller is None:
            mode = self.bus_mode_var.get()
            if mode == "j1939":
                self.controller = J1939AssociativeController(self.app)
            else:
                self.controller = AssociativeController(self.app)'''
    content = content.replace(old_start, new_start)
    print("Zaktualizowano start_learning o wybór kontrolera.")
else:
    print("start_learning już zawiera J1939AssociativeController.")

# ------------------------------------------------------------
# 6. Modyfikacja _update_candidates_table – dynamiczne kolumny dla J1939
# ------------------------------------------------------------
if '"pgn"' not in content and 'bus_mode_var' in content:
    old_table = '''        for c in candidates:
            bg = f"0x{c['background']:02X}" if c['background'] is not None else "brak"
            src = c.get("source", "zdarzenie")
            seq_str = c.get("ids_order", "")
            if isinstance(seq_str, list):
                seq_str = " -> ".join(str(i) for i in seq_str)
            self.tree.insert("", "end", values=(
                f"0x{c['id']:X}",
                c['byte'],
                f"0x{c['value']:02X}",
                bg,
                f"{c['confidence']:.1f}",
                src,
                seq_str
            ))'''
    new_table = '''        mode = self.bus_mode_var.get() if hasattr(self, 'bus_mode_var') else "can"
        for c in candidates:
            bg = f"0x{c['background']:02X}" if c['background'] is not None else "brak"
            src = c.get("source", "zdarzenie")
            seq_str = c.get("ids_order", "")
            if isinstance(seq_str, list):
                seq_str = " -> ".join(str(i) for i in seq_str)
            if mode == "j1939":
                pgn = c.get("pgn", "")
                pgn_name = c.get("pgn_name", "")
                pgn_display = f"0x{pgn:04X}" if isinstance(pgn, int) else str(pgn)
                if pgn_name:
                    pgn_display += f" ({pgn_name})"
                self.tree.insert("", "end", values=(
                    pgn_display,
                    f"0x{c['id']:X}",
                    c.get("source_address", ""),
                    c['byte'],
                    f"0x{c['value']:02X}",
                    bg,
                    f"{c['confidence']:.1f}",
                    src,
                    seq_str
                ))
            else:
                self.tree.insert("", "end", values=(
                    f"0x{c['id']:X}",
                    c['byte'],
                    f"0x{c['value']:02X}",
                    bg,
                    f"{c['confidence']:.1f}",
                    src,
                    seq_str
                ))'''
    content = content.replace(old_table, new_table)
    print("Zaktualizowano _update_candidates_table o dynamiczne kolumny.")
else:
    print("_update_candidates_table już zawiera obsługę J1939 lub jest pomijane.")

# ------------------------------------------------------------
# 7. Zapis zmian
# ------------------------------------------------------------
with open("gui/tabs/associative_tab.py", "w") as f:
    f.write(content)

print("Zapisano zmiany w associative_tab.py.")
PYEOF

# Sprawdzenie składni
python3 -m py_compile gui/tabs/associative_tab.py && echo "  associative_tab.py OK" || echo "  associative_tab.py BŁĄD"
python3 -m py_compile controllers/j1939_associative_controller.py 2>/dev/null && echo "  j1939_associative_controller.py OK" || echo "  j1939_associative_controller.py BŁĄD (lub nie istnieje – uruchom F14a)"

echo ""
echo "=== Faza 14b wdrożona ==="
echo "W zakładce uczenia asocjacyjnego pojawił się przełącznik CAN / J1939."
echo "Po przełączeniu na J1939 wyniki pokażą PGN, nazwę i adres źródłowy."
echo ""
echo "Aby dokończyć Fazę 14, uruchom update_F14c.sh (testy + dokumentacja)."
