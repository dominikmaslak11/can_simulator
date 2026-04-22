# CAN Simulator – Instrukcja użytkownika

## Spis treści
1. [Wymagania](#wymagania)
2. [Instalacja](#instalacja)
3. [Uruchamianie](#uruchamianie)
4. [Zdalny monitoring (dla Wojtka)](#zdalny-monitoring-dla-wojtka)
5. [Używanie plików DBC](#używanie-plików-dbc)
6. [Mostek vCAN (WebSocket → wirtualny CAN)](#mostek-vcan-websocket--wirtualny-can)
7. [Rozwiązywanie problemów](#rozwiązywanie-problemów)

---

## Wymagania

- System Linux (z jądrem obsługującym `vcan`)
- Python 3.8+ (jeśli uruchamiasz bez Dockera)
- Docker (opcjonalnie, dla łatwego wdrożenia)

## Instalacja

### Sposób 1: Uruchomienie przez Docker (zalecane)
```bash
git clone https://github.com/TwojaNazwa/magistralaCAN.git
cd can_simulator
./run_docker.sh
