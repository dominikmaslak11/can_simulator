#!/bin/bash
# update_F14c.sh – Faza 14c: Testy J1939 asocjacji + dokumentacja LaTeX
# Uruchom w katalogu can_simulator/

set -e

echo "=== Wdrażanie Fazy 14c: Testy i dokumentacja ==="

# ---------- 1. Test integracyjny dla asocjacji J1939 ----------
mkdir -p tests

cat > tests/test_j1939_associative.py << 'TESTEOF'
"""Test integracyjny dla asocjacji J1939 (wymaga vcan0 i python-can)."""
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
    from can_interface import CanInterface
    from controllers.j1939_associative_controller import J1939AssociativeController
    from parsers_j1939 import parse_j1939_id


class DummyApp:
    """Minimalny obiekt aplikacji dla testów."""
    def __init__(self):
        self.can = CanInterface()
        self.can.connected = False

    def connect(self, interface='vcan0'):
        try:
            self.can.connect(interface)
            self.can.connected = True
        except Exception:
            self.can.connected = False

    def log(self, msg):
        pass  # w testach pomijamy logowanie


@unittest.skipUnless(HAS_CAN, "python-can nie jest dostępny")
class TestJ1939Associative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import subprocess
        result = subprocess.run(['ip', 'link', 'show', 'vcan0'],
                                capture_output=True, text=True)
        if result.returncode != 0:
            raise unittest.SkipTest("vcan0 nie istnieje.")

    def setUp(self):
        self.app = DummyApp()
        self.app.connect('vcan0')
        if not self.app.can.connected:
            self.skipTest("Nie można połączyć z vcan0")
        # Używamy specjalistycznego kontrolera J1939
        self.controller = J1939AssociativeController(self.app)
        self.controller.start()

    def tearDown(self):
        self.controller.stop()
        self.app.can.disconnect()

    def test_event_toggle_j1939(self):
        """Test podstawowego przełączania zdarzeń."""
        self.assertEqual(self.controller.get_iteration_count(), 0)
        self.controller.toggle_event()
        self.controller.toggle_event()
        self.assertEqual(self.controller.get_iteration_count(), 1)

    def test_candidates_pgn_enriched(self):
        """Sprawdza, czy kandydaci z J1939 mają pola pgn i source_address."""
        import can as can_lib
        bus = can_lib.interface.Bus(channel='vcan0', bustype='socketcan')

        # Wysyłamy kilka ramek J1939 (29-bit)
        for _ in range(3):
            msg = can_lib.Message(arbitration_id=0x18FEF100, data=[0x01, 0x02, 0x03, 0x04],
                                  is_extended_id=True)
            bus.send(msg)
            time.sleep(0.02)

        self.controller.toggle_event()
        time.sleep(0.1)
        self.controller.toggle_event()

        candidates = self.controller.get_candidates()
        self.assertGreater(len(candidates), 0, "Powinien być przynajmniej jeden kandydat")
        first = candidates[0]
        # Sprawdź obecność pól J1939
        self.assertIn("pgn", first, "Kandydat powinien mieć pole 'pgn'")
        self.assertIn("source_address", first, "Kandydat powinien mieć pole 'source_address'")
        # Sprawdź, czy PGN jest poprawny
        self.assertEqual(first["pgn"], 0xFEF1)

        bus.shutdown()

    def test_export_j1939_pattern(self):
        """Test eksportu wzorca J1939 do JSON."""
        import json, tempfile, os
        # Symulujemy kandydata
        self.controller.candidates = [{
            "id": 0x18FEF100,
            "byte": 1,
            "value": 0x02,
            "background": 0x00,
            "confidence": 95.0,
            "source": "j1939",
            "pgn": 0xFEF1,
            "pgn_name": "Cruise Control / Vehicle Speed Setup (CCVS1)",
            "source_address": 0x00
        }]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            filepath = tmp.name
        try:
            self.controller.export_pattern(filepath)
            with open(filepath, 'r') as f:
                data = json.load(f)
            self.assertEqual(data["format_version"], 2)
            self.assertEqual(data["pgn"], 0xFEF1)
            self.assertIn("Cruise Control", data["pgn_name"])
        finally:
            os.unlink(filepath)


if __name__ == '__main__':
    unittest.main()
TESTEOF
echo "Utworzono tests/test_j1939_associative.py"

# ---------- 2. Dokumentacja LaTeX ----------
mkdir -p docs

cat > docs/j1939_associative_learning.tex << 'LATEXEOF'
\documentclass[a4paper,12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{hyperref}
\usepackage{listings}
\usepackage{xcolor}
\hypersetup{colorlinks=true}
\title{Asocjacja J1939\\Rozszerzenie uczenia asocjacyjnego CAN Simulator GUI}
\author{Zespół CAN Simulator GUI}
\date{\today}

\begin{document}
\maketitle
\tableofcontents

\section{Wprowadzenie}
Od Fazy~14 aplikacja CAN Simulator GUI obsługuje uczenie asocjacyjne w protokole SAE~J1939. Nowy kontroler \texttt{J1939AssociativeController} dziedziczy wszystkie możliwości analityczne (zdarzenia, wartości, sekwencje, klasyfikator online) i automatycznie wzbogaca wyniki o metadane J1939: numer grupy parametrów (PGN), nazwę PGN (z wbudowanej bazy) oraz adres źródłowy (Source Address).

\section{Nowe funkcje}
\begin{itemize}
    \item \textbf{Przełącznik trybu magistrali} – w zakładce ,,Uczenie asocjacyjne'' pojawiły się przyciski radiowe \texttt{CAN 2.0} oraz \texttt{J1939}.
    \item \textbf{Wyniki z nazwami PGN} – tabela kandydatów w trybie J1939 wyświetla dodatkowe kolumny: PGN (z nazwą), adres źródłowy.
    \item \textbf{Eksport wzorca v2} – plik JSON zawiera teraz pełne dane J1939 (format\_version=2).
    \item \textbf{Wyszukiwanie sekwencji w J1939} – algorytm uwzględnia nazwy PGN przy prezentacji sekwencji.
\end{itemize}

\section{Testy}
Testy jednostkowe i integracyjne znajdują się w pliku \texttt{tests/test\_j1939\_associative.py}. Wymagają one wirtualnej magistrali \texttt{vcan0}.

\section{Użycie}
\begin{enumerate}
    \item Uruchom aplikację, podłącz interfejs CAN (np. \texttt{vcan0}).
    \item Przejdź do zakładki ,,Uczenie asocjacyjne''.
    \item Wybierz tryb \textbf{J1939}.
    \item Rozpocznij uczenie (przycisk \texttt{Start}).
    \item Zaznaczaj zdarzenia lub wpisuj wartości referencyjne – wyniki natychmiast pokażą PGN i adres źródłowy.
\end{enumerate}

\section{Podsumowanie}
Integracja J1939 z uczeniem asocjacyjnym przekształca CAN Simulator GUI w potężne narzędzie do analizy magistrali w pojazdach ciężarowych, maszynach rolniczych i autobusach. Automatyczne mapowanie surowych identyfikatorów na nazwy parametrów znacząco skraca czas diagnostyki.

\end{document}
LATEXEOF
echo "Utworzono docs/j1939_associative_learning.tex"

# Opcjonalna kompilacja PDF
if command -v pdflatex &> /dev/null; then
    cd docs
    pdflatex -interaction=nonstopmode j1939_associative_learning.tex > /dev/null
    pdflatex -interaction=nonstopmode j1939_associative_learning.tex > /dev/null
    cd ..
    echo "PDF: docs/j1939_associative_learning.pdf"
fi

# ---------- 3. Sprawdzenie składni ----------
echo ""
echo "Sprawdzanie składni:"
python3 -m py_compile tests/test_j1939_associative.py 2>&1 && echo "  test_j1939_associative.py OK" || echo "  test_j1939_associative.py BŁĄD"
python3 -m py_compile gui/tabs/associative_tab.py 2>&1 && echo "  associative_tab.py OK" || echo "  associative_tab.py BŁĄD"
python3 -m py_compile controllers/j1939_associative_controller.py 2>&1 && echo "  j1939_associative_controller.py OK" || echo "  j1939_associative_controller.py BŁĄD"

echo ""
echo "=== Faza 14c wdrożona ==="
echo "Wszystkie części Fazy 14 zakończone."
echo "Test integracyjny: python3 -m pytest tests/test_j1939_associative.py -v"
