#!/bin/bash
# =============================================================================
# Generuje pliki LaTeX z kodem źródłowym mostka i serwera (dodatki do artykułu)
# Uruchom w głównym katalogu projektu (gdzie bridge_client.py i broadcaster/)
# =============================================================================

set -e

# Ścieżki do plików źródłowych
BRIDGE_FILE="bridge_client.py"
SERVER_FILE="broadcaster/server.py"

# Katalog wyjściowy (gdzie zostaną zapisane pliki .tex)
OUTPUT_DIR="latex_appendices"
mkdir -p "$OUTPUT_DIR"

echo "=== Generowanie plików LaTeX z kodem źródłowym ==="

# -----------------------------------------------------------------------------
# Funkcja escapująca znaki specjalne LaTeX
# -----------------------------------------------------------------------------
escape_latex() {
    sed -e 's/\\/\\textbackslash /g' \
        -e 's/_/\\_/g' \
        -e 's/#/\\#/g' \
        -e 's/%/\\%/g' \
        -e 's/&/\\&/g' \
        -e 's/\$/\\$/g' \
        -e 's/{/\\{/g' \
        -e 's/}/\\}/g' \
        -e 's/\^/\\^{}/g' \
        -e 's/~/\\textasciitilde{}/g'
}

# -----------------------------------------------------------------------------
# Generowanie appendix_code_bridge.tex
# -----------------------------------------------------------------------------
if [ -f "$BRIDGE_FILE" ]; then
    {
        echo "\\chapter{Kod źródłowy mostka vCAN (bridge\\_client.py)}"
        echo "\\label{app:bridge}"
        echo ""
        echo "Poniżej przedstawiono pełny kod pliku \\texttt{bridge\\_client.py} (wersja dwukierunkowa z obsługą auto-reconnect, filtrowania ID oraz wysyłania ramek z vcan0 do serwera)."
        echo ""
        echo "\\lstset{language=Python, basicstyle=\\ttfamily\\footnotesize, breaklines=true, frame=single, numbers=left, numberstyle=\\tiny, caption={}, captionpos=b}"
        echo "\\begin{lstlisting}"
        cat "$BRIDGE_FILE" | escape_latex
        echo "\\end{lstlisting}"
    } > "$OUTPUT_DIR/appendix_code_bridge.tex"
    echo "Wygenerowano: $OUTPUT_DIR/appendix_code_bridge.tex"
else
    echo "UWAGA: Nie znaleziono $BRIDGE_FILE – pomijam."
fi

# -----------------------------------------------------------------------------
# Generowanie appendix_code_server.tex
# -----------------------------------------------------------------------------
if [ -f "$SERVER_FILE" ]; then
    {
        echo "\\chapter{Kod źródłowy serwera WebSocket (server.py)}"
        echo "\\label{app:server}"
        echo ""
        echo "Poniżej przedstawiono pełny kod pliku \\texttt{broadcaster/server.py}. Serwer obsługuje tokeny, SSL, autoryzację ID, logowanie do pliku, powiadomienia Telegram oraz opcjonalny interfejs webowy (dashboard)."
        echo ""
        echo "\\lstset{language=Python, basicstyle=\\ttfamily\\footnotesize, breaklines=true, frame=single, numbers=left, numberstyle=\\tiny, caption={}, captionpos=b}"
        echo "\\begin{lstlisting}"
        cat "$SERVER_FILE" | escape_latex
        echo "\\end{lstlisting}"
    } > "$OUTPUT_DIR/appendix_code_server.tex"
    echo "Wygenerowano: $OUTPUT_DIR/appendix_code_server.tex"
else
    echo "UWAGA: Nie znaleziono $SERVER_FILE – pomijam."
fi

echo ""
echo "=== Generowanie zakończone ==="
echo "Pliki LaTeX znajdują się w katalogu: $OUTPUT_DIR"
echo "Skopiuj je do katalogu 'appendices/' w swoim projekcie LaTeX."
