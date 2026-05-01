#!/bin/bash
# update_F14c.sh – Faza 14c: Testy integracyjne J1939 + dokumentacja
# Uruchom w katalogu can_simulator/

set -e

echo "=== Wdrażanie Fazy 14c: Testy i dokumentacja J1939 ==="

# ---------- 1. Test integracyjny ----------
mkdir -p tests

if [ ! -f tests/test_j1939_associative.py ]; then
    cat > tests/test_j1939_associative.py << 'TESTEOF'
"""Test integracyjny uczenia asocjacyjnego z ramkami J1939."""
import unittest
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import can
    HAS_CAN = True
except ImportError:
    HAS_CAN = False

if HAS_CAN:
    from controllers.j1939_associative_controller import J1939AssociativeController
    from can_interface import CanInterface


class DummyApp:
    """Minimalna aplikacja dla testów."""
    def __init__(self):
        self.can = CanInterface()
        self.can.connected = False

    def connect(self, interface='vcan0'):
        try:
            self.can.connect(interface)
            self.can.connected = True
        except Exception:
            self.can.connected = False


@unittest.skipUnless(HAS_CAN, "python-can nie jest dostępny")
class TestJ1939Associative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import subprocess
        result = subprocess.run(['ip', 'link', 'show', 'vcan0'],
                                capture_output=True, text=True)
        if result.returncode != 0:
            raise unittest.SkipTest("vcan0 nie istnieje")

    def setUp(self):
        self.app = DummyApp()
        self.app.connect('vcan0')
        if not self.app.can.connected:
            self.skipTest("Nie można połączyć z vcan0")
        self.controller = J1939AssociativeController(self.app)
        self.controller.start()

    def tearDown(self):
        self.controller.stop()
        self.app.can.disconnect()

    def test_j1939_candidates_contain_pgn(self):
        """Sprawdza, czy kandydaci z J1939 mają pola pgn i source_address."""
        import can as can_lib
        bus = can_lib.interface.Bus(channel='vcan0', bustype='socketcan')

        # Ramka J1939: 0x18FEF100 (priorytet 6, PGN 0xFEF1, source 0x00)
        msg = can_lib.Message(arbitration_id=0x18FEF100, data=[0x01, 0x02, 0x03],
                              is_extended_id=True)
        # Zdarzenie
        self.controller.toggle_event()
        bus.send(msg)
        time.sleep(0.05)
        self.controller.toggle_event()

        candidates = self.controller.get_candidates()
        self.assertTrue(len(candidates) > 0, "Brak kandydatów po zdarzeniu J1939")
        best = candidates[0]
        self.assertIn("pgn", best, "Kandydat nie zawiera pola pgn")
        self.assertIn("source_address", best, "Kandydat nie zawiera source_address")
        self.assertEqual(best["pgn"], 0xFEF1)

        bus.shutdown()

    def test_j1939_pattern_export(self):
        """Test eksportu wzorca J1939 do JSON."""
        import json, tempfile, os
        # Ręcznie dodajemy kandydata z polami J1939
        self.controller.candidates = [{
            "id": 0x18FEF100,
            "byte": 2,
            "value": 0x01,
            "background": 0x00,
            "confidence": 95.0,
            "pgn": 0xFEF1,
            "source_address": 0x00,
            "pgn_name": "Cruise Control / Vehicle Speed Setup (CCVS1)",
            "source": "j1939"
        }]
        with tempfile.TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "test_pattern.json")
            self.controller.export_pattern(filepath)
            with open(filepath, "r") as f:
                pattern = json.load(f)
            self.assertEqual(pattern["format_version"], 2)
            self.assertEqual(pattern["pgn"], 0xFEF1)
            self.assertIn("pgn_name", pattern)

    def test_find_sequences_j1939(self):
        """Test wyszukiwania sekwencji z nazwami PGN."""
        self.controller.candidates = [{
            "id": 0x18FEF100, "byte": 0, "value": 0x01,
            "confidence": 90.0, "pgn": 0xFEF1
        }]
        # Symulujemy bufor z dwoma dodatkowymi ID
        import can as can_lib
        bus = can_lib.interface.Bus(channel='vcan0', bustype='socketcan')
        for _ in range(3):
            bus.send(can_lib.Message(arbitration_id=0x18F00400, data=[0x00], is_extended_id=True))
            time.sleep(0.01)
            bus.send(can_lib.Message(arbitration_id=0x18FEF100, data=[0x01], is_extended_id=True))
            time.sleep(0.01)
            bus.send(can_lib.Message(arbitration_id=0x18F00500, data=[0x02], is_extended_id=True))
            time.sleep(0.05)

        seqs = self.controller.find_sequences(self.controller.candidates[0])
        self.assertTrue(len(seqs) > 0, "Nie znaleziono sekwencji J1939")
        self.assertIn("ids_order_named", seqs[0], "Brak nazwanych ID w sekwencji")

        bus.shutdown()


if __name__ == '__main__':
    unittest.main()
TESTEOF
    echo "Utworzono tests/test_j1939_associative.py"
else
    echo "Test j1939_associative już istnieje."
fi

# ---------- 2. Dokumentacja LaTeX (uzupełnienie) ----------
mkdir -p docs

cat > docs/j1939_associative.tex << 'LATEXEOF'
\documentclass[a4paper,12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{hyperref}
\usepackage{enumitem}
\hypersetup{colorlinks=true}
\title{Asocjacja J1939 w CAN Simulator GUI}
\author{Zespół CAN Simulator GUI}
\date{\today}

\begin{document}
\maketitle

\section{Wprowadzenie}
Od Fazy 14 CAN Simulator GUI łączy interaktywne uczenie asocjacyjne z protokołem SAE J1939. Użytkownik może teraz wskazać zdarzenie lub wartość referencyjną, a algorytm analizuje ramki J1939 na poziomie \textbf{PGN} (Parameter Group Number), \textbf{adresu źródłowego} i konkretnego \textbf{bajtu}.

\section{Działanie}
\begin{enumerate}[noitemsep]
    \item W zakładce \texttt{Uczenie asocjacyjne} wybierz tryb \textbf{J1939} (radiobutton).
    \item Rozpocznij uczenie i oznaczaj zdarzenia (checkbox) lub wprowadzaj wartości referencyjne (np. temperatura).
    \item Algorytm analizuje tylko ramki 29-bitowe (J1939), automatycznie wyodrębnia PGN i adres źródłowy.
    \item Wyniki w tabeli pokazują: \textbf{PGN (nazwa)}, \textbf{ID}, \textbf{Source Address}, \textbf{Bajt}, \textbf{Wartość}, \textbf{Pewność}.
    \item Eksport wzorca (JSON v2) zawiera pełne metadane J1939.
\end{enumerate}

\section{Komponenty}
\begin{itemize}[noitemsep]
    \item \texttt{controllers/j1939\_associative\_controller.py} – dziedziczy po \texttt{AssociativeController}, nadpisuje analizę i dodaje pola J1939.
    \item \texttt{parsers\_j1939.py} – dekompozycja 29-bit ID na PGN, priorytet i adres źródłowy.
    \item \texttt{j1939\_pgn\_definitions.json} – wbudowana baza nazw PGN (ponad 70 wpisów).
\end{itemize}

\section{Testy}
Testy integracyjne znajdują się w \texttt{tests/test\_j1939\_associative.py}. Uruchomienie:
\begin{verbatim}
python3 -m pytest tests/test_j1939_associative.py -v
\end{verbatim}

\section{Ograniczenia}
\begin{itemize}[noitemsep]
    \item Analizowane są wyłącznie ramki z rozszerzonym identyfikatorem (29-bit).
    \item Protokół transportowy J1939 (wieloramkowy) nie jest jeszcze obsługiwany.
\end{itemize}
\end{document}
LATEXEOF
echo "Utworzono docs/j1939_associative.tex"

# Kompilacja PDF (opcjonalna)
if command -v pdflatex &> /dev/null; then
    cd docs
    pdflatex -interaction=nonstopmode j1939_associative.tex > /dev/null
    pdflatex -interaction=nonstopmode j1939_associative.tex > /dev/null
    cd ..
    echo "PDF: docs/j1939_associative.pdf"
fi

# ---------- 3. Sprawdzenie składni ----------
echo ""
echo "Sprawdzanie składni:"
python3 -m py_compile controllers/j1939_associative_controller.py && echo "  j1939_associative_controller.py OK" || echo "  j1939_associative_controller.py BŁĄD"
python3 -m py_compile gui/tabs/associative_tab.py && echo "  associative_tab.py OK" || echo "  associative_tab.py BŁĄD"
python3 -m py_compile tests/test_j1939_associative.py 2>/dev/null && echo "  test_j1939_associative.py OK" || echo "  test_j1939_associative.py BŁĄD (lub brak)"

echo ""
echo "=== Faza 14c wdrożona ==="
echo "Cała Faza 14 (Asocjacja J1939) zakończona."
echo "Uruchom testy: python3 -m pytest tests/test_j1939_associative.py -v"
echo "Dokumentacja: docs/j1939_associative.tex (i PDF)"
