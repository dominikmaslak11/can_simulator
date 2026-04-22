# Obraz bazowy z Python 3.10 (lekki, ale kompatybilny)
FROM python:3.10-slim

# Instalacja zależności systemowych wymaganych przez python-can i matplotlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    can-utils \
    tk \
    && rm -rf /var/lib/apt/lists/*

# Ustawienie katalogu roboczego
WORKDIR /app

# Kopiowanie pliku requirements.txt
COPY requirements.txt .

# Instalacja zależności Pythona
RUN pip install --no-cache-dir -r requirements.txt

# Kopiowanie reszty aplikacji
COPY . .

# Domyślny punkt wejścia – GUI (wymaga przekazania displayu)
CMD ["python", "main.py"]
