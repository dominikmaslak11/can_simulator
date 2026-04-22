# 1. Przejdź do katalogu projektu
cd /run/media/nz2xzhkzfeewkgbu/0C1A2332389DB1AF/magistralaCAN/can_simulator

# 2. Sprawdź stan repozytorium
git status

# 3. Dodaj wszystkie nowe i zmodyfikowane pliki
git add tests/ pytest.ini requirements-dev.txt .github/ run_tests.sh

# 4. Zatwierdź zmiany z opisowym komunikatem
git commit -m "Etap A: Fundamenty – testy jednostkowe (pytest) i CI (GitHub Actions)"

# 5. Pobierz ewentualne zmiany ze zdalnego repozytorium
git pull origin main --rebase

# 6. Wyślij lokalne commity na GitHub
git push origin main
