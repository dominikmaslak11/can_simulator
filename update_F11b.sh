#!/bin/bash
# update_F11b.sh – Faza 11b: Przeniesienie analizy do wątku roboczego
# Uruchom w katalogu can_simulator/

set -e

echo "=== Wdrażanie Fazy 11b: Analiza w wątku ==="

if [ ! -f controllers/associative_controller.py ]; then
    echo "BŁĄD: controllers/associative_controller.py nie istnieje."
    exit 1
fi

python3 << 'PYEOF'
with open("controllers/associative_controller.py", "r") as f:
    content = f.read()

# 1. Dodaj import threading
if "import threading" not in content:
    content = content.replace("import time\n", "import threading\nimport time\n")
    print("Dodano import threading.")
else:
    print("threading już zaimportowany.")

# 2. Dodaj atrybuty wątku w __init__
if "self.analysis_thread" not in content:
    attrs = '''
        # Wątek analizy
        self.analysis_thread = None
        self.analysis_lock = threading.Lock()
        self.pending_analysis = False
'''
    # Wstawiamy za self.classifier = ...
    old_clf = "self.classifier = PassiveAggressiveClassifier(warm_start=True, random_state=42)"
    if old_clf in content:
        content = content.replace(old_clf, old_clf + attrs)
        print("Dodano atrybuty wątku analizy.")
    else:
        # Wstawiamy za ostatnim atrybutem w __init__
        old_init_end = "self.value_labels = []           # etykiety dla bufora (słownik timestamp->wartość)"
        if old_init_end in content:
            content = content.replace(old_init_end, old_init_end + attrs)
            print("Dodano atrybuty wątku (wariant 2).")
else:
    print("Wątek analizy już istnieje.")

# 3. Dodaj metodę _run_analysis_in_thread
if "def _run_analysis_in_thread" not in content:
    analysis_thread_method = '''
    def _run_analysis_in_thread(self):
        """Uruchamia analizę w osobnym wątku, aby nie blokować GUI."""
        if self.analysis_thread and self.analysis_thread.is_alive():
            # Jeśli wątek jeszcze działa, ustaw flagę i poczekaj
            self.pending_analysis = True
            return
        self.analysis_thread = threading.Thread(target=self._analysis_worker, daemon=True)
        self.analysis_thread.start()
        logger.debug("Uruchomiono wątek analizy.")

    def _analysis_worker(self):
        """Wykonuje analizę w tle."""
        with self.analysis_lock:
            try:
                self._analyze()
                logger.debug("Analiza w tle zakończona.")
            except Exception as e:
                logger.error(f"Błąd analizy w wątku: {e}")
            finally:
                self.analysis_thread = None
                # Jeśli przyszło nowe żądanie, uruchom ponownie
                if self.pending_analysis:
                    self.pending_analysis = False
                    self._run_analysis_in_thread()
'''
    # Wstawiamy przed _analyze
    if "def _analyze(self):" in content:
        content = content.replace("    def _analyze(self):", analysis_thread_method + "\n    def _analyze(self):")
        print("Dodano metody wątku analizy.")
    else:
        print("Nie znaleziono _analyze.")
else:
    print("Metody wątku już istnieją.")

# 4. Zmień wywołanie _analyze w toggle_event na _run_analysis_in_thread
old_toggle = "self._analyze()"
new_toggle = "self._run_analysis_in_thread()"
if old_toggle in content and new_toggle not in content:
    content = content.replace(old_toggle, new_toggle)
    print("Zamieniono bezpośrednie wywołanie _analyze na wątek.")
else:
    print("toggle_event już używa wątku lub nie znaleziono.")

with open("controllers/associative_controller.py", "w") as f:
    f.write(content)
print("Zapisano zmiany.")
PYEOF

python3 -m py_compile controllers/associative_controller.py && echo "  controller OK" || echo "  controller BŁĄD"

echo ""
echo "=== Faza 11b zakończona ==="
echo "Analiza działa teraz w osobnym wątku – GUI pozostaje płynne."
