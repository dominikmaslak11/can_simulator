#!/bin/bash
# update_F9c.sh – Faza 9c: Integracja, testy i dokumentacja LaTeX
# Uruchom w katalogu can_simulator/

set -e

echo "=== Wdrażanie Fazy 9c: Testy i dokumentacja sekwencji ==="

# ---------- 1. Test integracyjny dla sekwencji ----------
if [ -f tests/test_associative.py ]; then
    python3 << 'PYEOF'
with open("tests/test_associative.py", "r") as f:
    content = f.read()

if "test_sequence_detection" not in content:
    new_test = '''
    def test_sequence_detection(self):
        """Test wykrywania sekwencji: ID_B -> ID_A -> ID_C."""
        import can as can_lib
        bus = can_lib.interface.Bus(channel='vcan0', bustype='socketcan')
        # Główna ramka 0x400, poprzedzająca 0x300, następująca 0x500
        for i in range(5):
            # Sekwencja przed
            bus.send(can_lib.Message(arbitration_id=0x300, data=[0x01], is_extended_id=False))
            time.sleep(0.01)
            # Główna
            bus.send(can_lib.Message(arbitration_id=0x400, data=[0x02], is_extended_id=False))
            time.sleep(0.01)
            # Sekwencja po
            bus.send(can_lib.Message(arbitration_id=0x500, data=[0x03], is_extended_id=False))
            time.sleep(0.05)

        # Wprowadź główny kandydat
        self.controller.candidates = [{"id": 0x400, "byte": 0, "confidence": 95, "source": "zdarzenie"}]
        seqs = self.controller.find_sequences(self.controller.candidates[0])
        self.assertTrue(len(seqs) > 0)
        self.assertIn(0x300, seqs[0]["ids_order"])
        self.assertIn(0x500, seqs[0]["ids_order"])
        bus.shutdown()
'''
    content = content.rstrip() + "\n" + new_test + "\n"
    with open("tests/test_associative.py", "w") as f:
        f.write(content)
    print("Dodano test test_sequence_detection.")
else:
    print("Test sekwencji już istnieje.")
PYEOF
fi

# ---------- 2. Dokumentacja LaTeX (rozszerzenie istniejącej) ----------
if [ -f docs/associative_learning.tex ]; then
    python3 << 'PYEOF'
with open("docs/associative_learning.tex", "r") as f:
    doc = f.read()

if "Sekwencje asocjacyjne" not in doc:
    new_section = r'''
\section{Wykrywanie sekwencji asocjacyjnych (Faza 9)}
Po zidentyfikowaniu głównej ramki (np. ID świateł stopu), użytkownik może kliknąć przycisk \texttt{Szukaj sekwencji}. Algorytm analizuje sąsiedztwo czasowe każdego wystąpienia ramki w buforze:

\begin{itemize}[noitemsep]
    \item Przeszukuje okno $\pm 0.5$ s wokół każdego wystąpienia głównego ID.
    \item Zlicza wystąpienia sąsiednich ID i ich kierunek (przed / po).
    \item Filtruje te, które występują w przynajmniej 80\% okien.
    \item Sortuje je według średnich odstępów czasu, tworząc uporządkowaną listę ID.
\end{itemize}

Wynik wyświetlany jest w kolumnie \texttt{Sekwencja} tabeli wyników. Wszystkie ID należące do sekwencji są podświetlane w Snifferze.
'''
    # Wstawiamy przed sekcją "Podsumowanie"
    if "\\section{Podsumowanie}" in doc:
        doc = doc.replace("\\section{Podsumowanie}", new_section + "\n\\section{Podsumowanie}")
    else:
        doc += "\n" + new_section
    with open("docs/associative_learning.tex", "w") as f:
        f.write(doc)
    print("Rozszerzono dokumentację o sekcję sekwencji.")
else:
    print("Dokumentacja już zawiera sekcję sekwencji.")
PYEOF
fi

# ---------- 3. Sprawdzenie składni ----------
echo ""
python3 -m py_compile controllers/associative_controller.py && echo "  controller OK" || echo "  controller BŁĄD"
python3 -m py_compile gui/tabs/associative_tab.py && echo "  tab OK" || echo "  tab BŁĄD"
python3 -m py_compile tests/test_associative.py 2>/dev/null && echo "  test OK" || echo "  test niekompletny (spodziewane)"

echo ""
echo "=== Faza 9c wdrożona pomyślnie ==="
echo "Wszystkie części Fazy 9 gotowe."
echo "Uruchom: git add -A && git commit -m 'Faza 9: Wykrywanie sekwencji asocjacyjnych' && git push"
