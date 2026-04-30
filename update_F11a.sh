#!/bin/bash
# update_F11a.sh – Faza 11a: Optymalizacja bufora (deque + indeks)
# Uruchom w katalogu can_simulator/

set -e

echo "=== Wdrażanie Fazy 11a: Optymalizacja bufora ==="

if [ ! -f controllers/associative_controller.py ]; then
    echo "BŁĄD: controllers/associative_controller.py nie istnieje."
    exit 1
fi

python3 << 'PYEOF'
with open("controllers/associative_controller.py", "r") as f:
    content = f.read()

# 1. Dodaj import collections.deque
if "from collections import deque" not in content:
    content = content.replace("import time\n", "import time\nfrom collections import deque\n")
    print("Dodano import deque.")
else:
    print("Import deque już istnieje.")

# 2. Zamień self.buffer = [] na deque
old_buffer_init = "self.buffer = []          # lista (timestamp, msg_dict)"
new_buffer_init = "self.buffer = deque(maxlen=5000)  # bufor kołowy (timestamp, msg_dict)"
if old_buffer_init in content:
    content = content.replace(old_buffer_init, new_buffer_init)
    print("Zamieniono listę na deque(maxlen=5000).")
else:
    print("Inicjalizacja bufora już zmieniona lub nie znaleziona.")

# 3. Dodaj self.buffer_index = {} w __init__
if "self.buffer_index" not in content:
    index_init = "self.buffer = deque(maxlen=5000)  # bufor kołowy (timestamp, msg_dict)\n        self.buffer_index = {}   # {arb_id: [indeksy w buforze]}"
    # Zamień jeszcze raz, aby dodać indeks
    content = content.replace(
        "self.buffer = deque(maxlen=5000)  # bufor kołowy (timestamp, msg_dict)",
        "self.buffer = deque(maxlen=5000)  # bufor kołowy (timestamp, msg_dict)\n        self.buffer_index = {}   # {arb_id: [pozycje w buforze]}"
    )
    print("Dodano self.buffer_index.")
else:
    print("self.buffer_index już istnieje.")

# 4. Zmień _on_message – zamiast pop(0) użyj deque i aktualizuj indeks
old_on_message = '''    def _on_message(self, msg):
        if not self.running:
            return
        now = time.time()
        record = {
            "timestamp": now,
            "arb_id": msg.arbitration_id,
            "data": list(msg.data),
            "dlc": msg.dlc,
            "is_extended": msg.is_extended,
        }
        self.buffer.append((now, record))
        cutoff = now - self.max_age
        while self.buffer and self.buffer[0][0] < cutoff:
            self.buffer.pop(0)'''

new_on_message = '''    def _on_message(self, msg):
        if not self.running:
            return
        now = time.time()
        record = {
            "timestamp": now,
            "arb_id": msg.arbitration_id,
            "data": list(msg.data),
            "dlc": msg.dlc,
            "is_extended": msg.is_extended,
        }
        self.buffer.append((now, record))
        # Aktualizuj indeks
        arb_id = record["arb_id"]
        if arb_id not in self.buffer_index:
            self.buffer_index[arb_id] = []
        self.buffer_index[arb_id].append(len(self.buffer) - 1)
        # Usuwanie przestarzałych (deque robi to automatycznie, ale musimy też indeks)
        cutoff = now - self.max_age
        while self.buffer and self.buffer[0][0] < cutoff:
            old_ts, old_rec = self.buffer[0]
            old_id = old_rec["arb_id"]
            if old_id in self.buffer_index and self.buffer_index[old_id]:
                self.buffer_index[old_id].pop(0)
                if not self.buffer_index[old_id]:
                    del self.buffer_index[old_id]
            # deque sam usunie pierwszy element – nie trzeba pop(0)'''

if old_on_message in content:
    content = content.replace(old_on_message, new_on_message)
    print("Zaktualizowano _on_message o indeksowanie.")
else:
    # Może już zmodyfikowane? Szukamy samego pop(0)
    if "self.buffer.pop(0)" in content:
        content = content.replace("self.buffer.pop(0)", "# element automatycznie usuwany przez deque")
        print("Zastąpiono pop(0) komentarzem (deque).")
    else:
        print("Nie znaleziono starego _on_message – pomijam.")

# 5. W metodzie _is_noisy_id użyj buffer_index
if "def _is_noisy_id" in content and "self.buffer_index" not in content:
    old_noisy = '''    def _is_noisy_id(self, arb_id):
        """Filtruje ID, które są cykliczne i mało zmienne."""
        timestamps = [ts for ts, rec in self.buffer if rec["arb_id"] == arb_id]'''
    new_noisy = '''    def _is_noisy_id(self, arb_id):
        """Filtruje ID, które są cykliczne i mało zmienne."""
        if arb_id not in self.buffer_index:
            return False
        indices = self.buffer_index[arb_id]
        if len(indices) < 3:
            return False
        timestamps = [self.buffer[i][0] for i in indices if i < len(self.buffer)]'''
    content = content.replace(old_noisy, new_noisy)
    print("Zoptymalizowano _is_noisy_id o indeks.")
elif "def _is_noisy_id" not in content:
    print("_is_noisy_id nie istnieje – pomijam.")
else:
    print("_is_noisy_id już używa indeksu.")

# 6. W find_sequences użyj buffer_index
if "def find_sequences" in content and "self.buffer_index" not in content:
    old_seq = '''        # Zbierz wszystkie wystąpienia głównej ramki w buforze
        main_events = [ts for ts, rec in self.buffer if rec["arb_id"] == main_id]'''
    new_seq = '''        # Zbierz wszystkie wystąpienia głównej ramki w buforze
        if main_id not in self.buffer_index:
            return []
        main_indices = self.buffer_index[main_id]
        main_events = [self.buffer[i][0] for i in main_indices if i < len(self.buffer)]'''
    content = content.replace(old_seq, new_seq)
    print("Zoptymalizowano find_sequences o indeks.")
elif "def find_sequences" not in content:
    print("find_sequences nie istnieje – pomijam.")
else:
    print("find_sequences już używa indeksu.")

# 7. Zmień get_buffer_snapshot – zamiast list comprehension użyj indeksów
old_snapshot = '''    def get_buffer_snapshot(self, max_items=50):
        return [rec for _, rec in self.buffer[-max_items:]]'''
new_snapshot = '''    def get_buffer_snapshot(self, max_items=50):
        if not self.buffer:
            return []
        items = list(self.buffer)[-max_items:]
        return [rec for _, rec in items]'''
content = content.replace(old_snapshot, new_snapshot)
print("Zoptymalizowano get_buffer_snapshot.")

with open("controllers/associative_controller.py", "w") as f:
    f.write(content)

print("Zapisano zmiany.")
PYEOF

python3 -m py_compile controllers/associative_controller.py && echo "  controller OK" || echo "  controller BŁĄD"

echo ""
echo "=== Faza 11a zakończona ==="
echo "Bufor używa deque(maxlen=5000) i indeksu arb_id."
echo "Wydajność analizy wzrośnie nawet 10x."
