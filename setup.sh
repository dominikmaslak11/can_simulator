#!/bin/bash
echo "==> Tworzenie wirtualnego środowiska..."
python3 -m venv venv
source venv/bin/activate
echo "==> Instalacja zależności..."
pip install --upgrade pip
pip install -r requirements.txt
echo "==> Gotowe. Aplikację uruchomisz komendą: ./run.sh"
