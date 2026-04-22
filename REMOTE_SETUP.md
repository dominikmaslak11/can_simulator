# Instrukcja zdalnego dostępu do CAN przez internet (WSS)

## Dla właściciela serwera (Ty)

### 1. Konfiguracja dynamicznego DNS (DuckDNS)
- Wejdź na https://www.duckdns.org
- Zaloguj się (np. przez GitHub).
- Dodaj subdomenę (np. `twojserwer.duckdns.org`).
- Zapisz token.
- Zainstaluj skrypt aktualizujący IP (na Linux):
  ```bash
  mkdir ~/duckdns
  cd ~/duckdns
  echo 'echo url="https://www.duckdns.org/update?domains=twojserwer&token=TWÓJ_TOKEN&ip=" | curl -k -o ~/duckdns/duck.log -K -' > duck.sh
  chmod 700 duck.sh
