#!/bin/bash
# generate_shortcuts_doc.sh – generuje dokument LaTeX z listą skrótów klawiszowych
# Uruchom w katalogu can_simulator/

mkdir -p docs

cat > docs/keyboard_shortcuts.tex << 'EOF'
\documentclass[a4paper,12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{tabularx}
\usepackage{hyperref}
\usepackage[table]{xcolor}
\hypersetup{colorlinks=true,linkcolor=blue}
\title{Zestawienie skrótów klawiszowych\\CAN Simulator GUI}
\author{Zespół CAN Simulator GUI}
\date{\today}

\begin{document}
\maketitle
\section*{Skróty globalne}
\begin{center}
\rowcolors{2}{gray!15}{white}
\begin{tabularx}{0.8\textwidth}{|l|X|l|}
\hline
\rowcolor{gray!30}
\textbf{Skrót} & \textbf{Działanie} & \textbf{Kontekst} \\
\hline
F1 & Pomoc & Globalny \\
F5 & Start Sniffera & Globalny \\
F6 & Stop Sniffera & Globalny \\
F7 / Ctrl+L & Wyczyść Sniffera & Globalny \\
Ctrl+S & Eksportuj projekt (.csp) & Globalny \\
Ctrl+O & Importuj projekt (.csp) & Globalny \\
\hline
\end{tabularx}
\end{center}

\section*{Uczenie asocjacyjne}
\begin{center}
\rowcolors{2}{gray!15}{white}
\begin{tabularx}{0.8\textwidth}{|l|X|l|}
\hline
\rowcolor{gray!30}
\textbf{Skrót} & \textbf{Działanie} & \textbf{Kontekst} \\
\hline
Ctrl+H & Przełącz zdarzenie (checkbox) & Zakładka ,,Uczenie asocjacyjne'' \\
Ctrl+Shift+V & Zatwierdź wartość referencyjną & Zakładka ,,Uczenie asocjacyjne'' \\
Ctrl+Shift+Z & Cofnij ostatnią wartość & Zakładka ,,Uczenie asocjacyjne'' \\
Ctrl+Shift+S & Szukaj sekwencji & Zakładka ,,Uczenie asocjacyjne'' \\
\hline
\end{tabularx}
\end{center}

\vfill
\noindent\small Dokument wygenerowany automatycznie przez CAN Simulator GUI.
\end{document}
EOF

echo "Utworzono docs/keyboard_shortcuts.tex"

# Opcjonalna kompilacja
if command -v pdflatex &> /dev/null; then
    cd docs
    pdflatex -interaction=nonstopmode keyboard_shortcuts.tex > /dev/null
    pdflatex -interaction=nonstopmode keyboard_shortcuts.tex > /dev/null
    cd ..
    echo "PDF gotowy: docs/keyboard_shortcuts.pdf"
fi
