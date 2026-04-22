#!/bin/bash
# =============================================================================
# Etap 7: Walidacja sygnałów DBC w Snifferze (podświetlanie poza zakresem)
# =============================================================================

set -e

BASE_DIR="$(pwd)"
SNIFFER_FILE="${BASE_DIR}/gui/tabs/sniffer_tab.py"
DBC_MANAGER_FILE="${BASE_DIR}/dbc_manager.py"
BACKUP_DIR="${BASE_DIR}/backup_dbc_validation_$(date +%Y%m%d_%H%M%S)"

echo "=== Etap 7: Walidacja zakresów DBC w Snifferze ==="

mkdir -p "$BACKUP_DIR"
cp "$SNIFFER_FILE" "$DBC_MANAGER_FILE" "$BACKUP_DIR/" 2>/dev/null || true
echo "Kopie zapasowe w: $BACKUP_DIR"

# -----------------------------------------------------------------------------
# 1. Rozszerzenie dbc_manager.py – zwracanie granic sygnałów
# -----------------------------------------------------------------------------
python3 - "$DBC_MANAGER_FILE" <<'EOF'
import re
import sys

file_path = sys.argv[1]
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Zmieniamy metodę decode_frame, aby zwracała także granice sygnałów
pattern = r'(def decode_frame\(self, frame_id: int, data: bytes\).*?return \{)'
if re.search(pattern, content, flags=re.DOTALL):
    replacement = '''def decode_frame(self, frame_id: int, data: bytes):
        if not self.db:
            return None
        try:
            message = self.db.get_message_by_frame_id(frame_id)
            decoded = message.decode(data)
            # Zbierz granice dla każdego sygnału
            limits = {}
            for sig in message.signals:
                limits[sig.name] = (sig.minimum, sig.maximum)
            return {
                "message_name": message.name,
                "signals": decoded,
                "limits": limits
            }
        except Exception:
            return None'''
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    print("dbc_manager.py: decode_frame rozszerzony o granice.")
else:
    print("UWAGA: Nie znaleziono metody decode_frame w dbc_manager.py")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
EOF

# -----------------------------------------------------------------------------
# 2. Modyfikacja sniffer_tab.py – podświetlanie i ostrzeżenia
# -----------------------------------------------------------------------------
python3 - "$SNIFFER_FILE" <<'EOF'
import re
import sys

file_path = sys.argv[1]
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 2.1 Dodajemy konfigurację tagu dla wierszy poza zakresem
if 'tree.tag_configure("out_of_range"' not in content:
    tag_config = '\n        tree.tag_configure("out_of_range", background="#ffcccc", foreground="black")\n'
    # Wstawiamy po utworzeniu tree
    content = re.sub(r'(self\.tree = ttk\.Treeview\(.*?\))', r'\1' + tag_config, content, flags=re.DOTALL)

# 2.2 W pętli przetwarzającej ramki, po dekodowaniu dodajemy walidację
loop_pattern = r'(        # Dekodowanie DBC.*?decoded_str = ", "\.join\(f"\{k\}=\{v:\.2f\}" for k, v in sigs\.items\(\)\)\n)'
if re.search(loop_pattern, content, flags=re.DOTALL):
    validation_code = '''        # Walidacja zakresów DBC
        out_of_range = False
        if dec and "limits" in dec:
            limits = dec["limits"]
            for sig_name, value in sigs.items():
                min_val, max_val = limits.get(sig_name, (None, None))
                if min_val is not None and max_val is not None:
                    if value < min_val or value > max_val:
                        out_of_range = True
                        decoded_str += " [!]"
                        app.log(f"[DBC] Wartość poza zakresem: {sig_name} = {value:.2f} (zakres: {min_val}..{max_val})")
                        break  # wystarczy jedna nieprawidłowa wartość, aby oznaczyć wiersz
'''
    content = re.sub(loop_pattern, r'\1' + validation_code, content, flags=re.DOTALL)
    print("Sniffer: dodano walidację zakresów DBC.")
else:
    print("UWAGA: Nie znaleziono bloku dekodowania w sniffer_tab.py")

# 2.3 Modyfikacja tree.insert – dodanie tagu
insert_pattern = r'(tree\.insert\("", tk\.END, values=\([^)]+\))(\))'
if re.search(insert_pattern, content):
    replacement = r'\1, tags=("out_of_range",) if out_of_range else ()\2'
    content = re.sub(insert_pattern, replacement, content)
    print("Sniffer: dodano tagowanie wierszy poza zakresem.")
else:
    print("UWAGA: Nie znaleziono tree.insert w sniffer_tab.py")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
EOF

echo ""
echo "=== Etap 7 zakończony pomyślnie ==="
echo "Nowa funkcja: w Snifferze CAN ramki z wartościami spoza zakresu DBC"
echo "są podświetlane na czerwono, a w logu pojawia się ostrzeżenie."
echo ""
echo "Uruchom aplikację: sudo ./run.sh"
echo "Po wczytaniu pliku DBC i uruchomieniu sniffera przetestuj walidację."
echo ""
echo "Aby wypchnąć zmiany na GitHub:"
echo "  git add -A"
echo "  git commit -m 'Etap 7: Walidacja zakresów DBC w Snifferze'"
echo "  git push"
