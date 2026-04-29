#!/bin/bash
# update_F8c.sh – Faza 8c: Integracja GUI, eksport wzorca, testy
# Uruchom w katalogu can_simulator/

set -e

echo "=== Wdrażanie Fazy 8c: Integracja i testy ==="

# ---------- 1. Aktualizacja _update_candidates_table (filtrowanie po źródle, jeśli potrzebne) ----------
if [ -f gui/tabs/associative_tab.py ]; then
    python3 << 'PYEOF'
with open("gui/tabs/associative_tab.py", "r") as f:
    content = f.read()

# Dodajemy przycisk czyszczenia tylko wtedy, gdy jeszcze go nie ma (już jest)
# Dodajemy opcjonalnie filtr źródła – checkbox "Pokaż tylko wartościowe" (jeśli chcemy)
if "self.filter_var" not in content:
    filter_section = '''
        # Filtr źródła
        filter_frame = ttk.Frame(value_frame)
        filter_frame.pack(fill=tk.X, pady=2)
        self.filter_var = tk.StringVar(value="all")
        ttk.Radiobutton(filter_frame, text="Wszystkie", variable=self.filter_var,
                        value="all", command=self._update_candidates_table).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(filter_frame, text="Tylko zdarzenia", variable=self.filter_var,
                        value="zdarzenie", command=self._update_candidates_table).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(filter_frame, text="Tylko wartości", variable=self.filter_var,
                        value="wartosc", command=self._update_candidates_table).pack(side=tk.LEFT, padx=5)
'''
    # Wstawiamy przed końcem sekcji value_frame
    if 'self.correlation_type_var' in content and filter_section not in content:
        # Znajdź linię z Radiobutton dla any_change i wstaw po niej
        insertion = 'value="any_change").pack(side=tk.LEFT, padx=5)'
        content = content.replace(insertion + '\n', insertion + '\n' + filter_section + '\n')
        print("Dodano filtr źródła.")
    else:
        print("Filtr źródła już istnieje lub brak punktu wstawienia.")

# Aktualizuj _update_candidates_table o filtrowanie
if "def _update_candidates_table" in content:
    if "filter_var" in content and 'c.get("source"' not in content:
        old_for_loop = "for c in candidates:"
        new_for_loop = '''        filter_mode = getattr(self, 'filter_var', None)
        for c in candidates:
            if filter_mode and filter_mode.get() != "all":
                src = c.get("source", "zdarzenie")
                if src != filter_mode.get():
                    continue'''
        content = content.replace(old_for_loop, new_for_loop)
        print("Zaktualizowano pętlę tabeli o filtrowanie źródła.")
else:
    print("Metoda _update_candidates_table nie znaleziona.")

with open("gui/tabs/associative_tab.py", "w") as f:
    f.write(content)
print("Zapisano zmiany w associative_tab.py.")
PYEOF
else
    echo "associative_tab.py nie istnieje – pomijam."
fi

# ---------- 2. Rozszerzenie eksportu wzorca w kontrolerze ----------
if [ -f controllers/associative_controller.py ]; then
    python3 << 'PYEOF'
with open("controllers/associative_controller.py", "r") as f:
    content = f.read()

if "def export_pattern" in content and '"source"' not in content:
    old_pattern = '''            "confidence": best["confidence"],
            "description": "Wzorzec wygenerowany przez uczenie asocjacyjne"'''
    new_pattern = '''            "confidence": best["confidence"],
            "source": best.get("source", "zdarzenie"),
            "correlation_type": best.get("correlation_type", ""),
            "description": "Wzorzec wygenerowany przez uczenie asocjacyjne"'''
    content = content.replace(old_pattern, new_pattern)
    print("Rozszerzono eksport wzorca o źródło i typ korelacji.")

with open("controllers/associative_controller.py", "w") as f:
    f.write(content)
PYEOF
fi

# ---------- 3. Rozszerzenie testów ----------
if [ -f tests/test_associative.py ]; then
    python3 << 'PYEOF'
with open("tests/test_associative.py", "r") as f:
    content = f.read()

if "test_value_correlation" not in content:
    new_test = '''
    def test_value_correlation(self):
        """Test trybu wartościowego – korelacja liniowa."""
        import can as can_lib
        bus = can_lib.interface.Bus(channel='vcan0', bustype='socketcan')
        # Symulacja: temperatura rośnie, bajt 2 rośnie proporcjonalnie
        for temp in range(20, 30):
            byte_val = temp + 30   # bajt 2 = temp + 30
            msg = can_lib.Message(arbitration_id=0x300, data=[0x00, 0x00, byte_val, 0x00],
                                  is_extended_id=False)
            bus.send(msg)
            time.sleep(0.05)
            # Zatwierdź wartość referencyjną
            self.controller.commit_value(float(temp))
            time.sleep(0.05)

        # Wymuś analizę
        self.controller._analyze()
        candidates = self.controller.get_candidates()
        # Powinien być kandydat dla ID 0x300, bajt 2
        matching = [c for c in candidates if c['id'] == 0x300 and c['byte'] == 2]
        self.assertTrue(len(matching) > 0, "Nie znaleziono korelacji dla ID 0x300 bajt 2")
        bus.shutdown()
'''
    # Wstawiamy przed końcem klasy (przed ostatnią metodą)
    content = content.rstrip() + "\n" + new_test + "\n"
    with open("tests/test_associative.py", "w") as f:
        f.write(content)
    print("Dodano test test_value_correlation.")
else:
    print("Test wartościowy już istnieje.")
PYEOF
fi

# ---------- 4. Sprawdzenie składni ----------
echo ""
echo "Sprawdzanie składni:"
python3 -m py_compile controllers/associative_controller.py && echo "  controller OK" || echo "  controller BŁĄD"
python3 -m py_compile gui/tabs/associative_tab.py && echo "  tab OK" || echo "  tab BŁĄD"
python3 -m py_compile tests/test_associative.py 2>/dev/null && echo "  test OK" || echo "  test BŁĄD (lub brak)"

echo ""
echo "=== Faza 8c zakończona ==="
echo "Wszystkie części Fazy 8 wdrożone."
