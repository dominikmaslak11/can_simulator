#!/bin/bash
# =============================================================================
# Tworzenie środowiska Docker dla CAN Simulator (WERSJA KOMPLETNA)
# =============================================================================

set -e

BASE_DIR="$(pwd)"
DOCKERFILE="${BASE_DIR}/Dockerfile"
DOCKER_COMPOSE="${BASE_DIR}/docker-compose.yml"
RUN_SCRIPT="${BASE_DIR}/run_docker.sh"
README="${BASE_DIR}/README.md"

echo "=== Tworzenie konfiguracji Docker dla CAN Simulator ==="

# -----------------------------------------------------------------------------
# 1. Dockerfile
# -----------------------------------------------------------------------------
cat > "$DOCKERFILE" << 'EOF'
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
EOF

echo "Utworzono Dockerfile"

# -----------------------------------------------------------------------------
# 2. docker-compose.yml
# -----------------------------------------------------------------------------
cat > "$DOCKER_COMPOSE" << 'EOF'
version: '3.8'

services:
  can-simulator:
    build: .
    container_name: can_simulator
    network_mode: host
    privileged: true
    environment:
      - DISPLAY=${DISPLAY}
    volumes:
      - /tmp/.X11-unix:/tmp/.X11-unix
      - ./data:/app/data
    stdin_open: true
    tty: true
EOF

echo "Utworzono docker-compose.yml"

# -----------------------------------------------------------------------------
# 3. run_docker.sh
# -----------------------------------------------------------------------------
cat > "$RUN_SCRIPT" << 'EOF'
#!/bin/bash
# Skrypt do budowania i uruchamiania CAN Simulator w Dockerze

xhost +local:docker
docker build -t can-simulator .
docker run -it --rm \
    --privileged \
    --network host \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v $(pwd)/data:/app/data \
    --name can_simulator \
    can-simulator
xhost -local:docker
EOF

chmod +x "$RUN_SCRIPT"
echo "Utworzono run_docker.sh"

# -----------------------------------------------------------------------------
# 4. Aktualizacja README.md
# -----------------------------------------------------------------------------
if [ -f "$README" ]; then
    if ! grep -q "## Uruchamianie w Dockerze" "$README"; then
        cat >> "$README" << 'EOF'

## Uruchamianie w Dockerze

Aplikację można uruchomić w kontenerze Docker, co eliminuje konieczność ręcznej instalacji zależności.

### Wymagania
- Zainstalowany Docker
- System Linux z serwerem X11 (do wyświetlania GUI)

### Instrukcja
1. Sklonuj repozytorium:
   ```bash
   git clone <adres_repo>
   cd can_simulator
