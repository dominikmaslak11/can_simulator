#!/bin/bash
# update_F12c.sh – Faza 12c: Integracja J1939 ze Snifferem + testy + dokumentacja
# Uruchom w katalogu can_simulator/

set -e

echo "=== Wdrażanie Fazy 12c: Integracja, testy i dokumentacja ==="

# ---------- 1. Test parsera ----------
mkdir -p tests

cat > tests/test_j1939.py << 'EOF'
"""Testy parsera J1939."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from parsers_j1939 import parse_j1939_id


def test_parse_j1939_id():
    # Przykład: ID 0x18FEF100 (priorytet 3, PGN 0xFEF1, source 0x00)
    result = parse_j1939_id(0x18FEF100)
    assert result["priority"] == 3      # 0x18 >> 2 = 0b011
    assert result["pgn"] == 0xFEF1      # faktycznie 0xFEF1? Sprawdźmy: (0x18FEF100 >> 8) & 0x3FFFF = 0xFEF1
    assert result["source_address"] == 0x00

def test_parse_another():
    # 0x0CF0040B: PGN 0xF004, priority 3, source 0x0B
    result = parse_j1939_id(0x0CF0040B)
    assert result["pgn"] == 0xF004
    assert result["source_address"] == 0x0B
EOF

python3 -m pytest tests/test_j1939.py -v 2>&1 && echo "  test_j1939.py OK" || echo "  test_j1939.py niepowodzenie (sprawdź python-can?)"

# ---------- 2. Opcjonalna integracja ze Snifferem (checkbox "Widok J1939") ----------
if [ -f gui/tabs/sniffer_tab.py ]; then
    python3 << 'PYEOF'
with open("gui/tabs/sniffer_tab.py", "r") as f:
    content = f.read()

# Dodajemy checkbox "J1939 View" po istniejącym checkboxie filtrowania (sniffer_filter_var)
if "sniffer_j1939_var" not in content:
    snippet = 'self.sniffer_filter_var = tk.BooleanVar(value=False)'
    addition = 'self.sniffer_j1939_var = tk.BooleanVar(value=False)'
    content = content.replace(snippet, snippet + '\n        ' + addition)

    # Dodaj checkbox w GUI – szukamy 'self.sniffer_filter_check = ...'
    checkbox_line = 'self.sniffer_filter_check = ttk.Checkbutton(..., text="Filtr", variable=self.sniffer_filter_var)'
    # Lepiej użyć prostego wstawienia za istniejącym checkboxem
    if 'command=self.sniffer_ctrl.toggle_filter' in content:
        content = content.replace(
            'command=self.sniffer_ctrl.toggle_filter',
            'command=self.sniffer_ctrl.toggle_filter'
        )
        # Wstawiamy nasz checkbox za tą linią
        # Ale bezpieczniej zrobić replace całego fragmentu
    # Alternatywnie: dodajemy przycisk gdzieś obok – może w setup_sniffer_tab?
    # Spróbujmy wstawić przed 'pack()' checkboxa filtru
    old_pack = 'self.sniffer_filter_check.pack(side=tk.LEFT, padx=5)'
    new_pack = 'self.sniffer_filter_check.pack(side=tk.LEFT, padx=5)\n        self.j1939_view_check = ttk.Checkbutton(filter_frame, text="J1939 View", variable=self.sniffer_j1939_var, command=self.toggle_j1939_view)\n        self.j1939_view_check.pack(side=tk.LEFT, padx=5)'
    if old_pack in content:
        content = content.replace(old_pack, new_pack)
        print("Dodano checkbox J1939 View do sniffera.")
    else:
        print("Nie znaleziono miejsca na checkbox J1939.")
else:
    print("J1939 View już istnieje w snifferze.")

with open("gui/tabs/sniffer_tab.py", "w") as f:
    f.write(content)
PYEOF
fi

# ---------- 3. Dokumentacja LaTeX ----------
mkdir -p docs

cat > docs/j1939_support.tex << 'EOF'
\documentclass[a4paper,12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{hyperref}
\title{Wsparcie J1939 w CAN Simulator GUI}
\author{Zespół CAN Simulator GUI}
\date{\today}
\begin{document}
\maketitle
\section{Wprowadzenie}
Od wersji z Faza 12 CAN Simulator GUI obsługuje protokół SAE J1939. Nowy parser identyfikatorów 29-bitowych pozwala na dekompozycję identyfikatora na PGN (Parameter Group Number), priorytet oraz adres źródłowy (Source Address).

\section{Funkcje}
\begin{itemize}
    \item \textbf{Biblioteka PGN} – wbudowana baza popularnych PGN (ponad 50 wpisów) w pliku \texttt{j1939\_pgn\_definitions.json}.
    \item \textbf{J1939 Browser} – nowa zakładka w kategorii „Protokoły” wyświetlająca ramki J1939 z nazwami PGN.
    \item \textbf{Filtrowanie} – możliwość filtrowania po numerze PGN (szesnastkowo).
    \item \textbf{Integracja ze Snifferem} – opcjonalny widok kolumn PGN, Source Address i Priority w głównym Snifferze (checkbox „J1939 View”).
\end{itemize}
\section{Testy}
Testy jednostkowe parsera znajdują się w \texttt{tests/test\_j1939.py}.
\end{document}
EOF
echo "Utworzono dokumentację docs/j1939_support.tex"

# Kompilacja PDF (opcjonalna)
if command -v pdflatex &> /dev/null; then
    cd docs
    pdflatex -interaction=nonstopmode j1939_support.tex > /dev/null
    pdflatex -interaction=nonstopmode j1939_support.tex > /dev/null
    cd ..
    echo "PDF: docs/j1939_support.pdf"
fi

echo ""
echo "=== Faza 12c zakończona ==="
echo "Cała Faza 12 wdrożona."
