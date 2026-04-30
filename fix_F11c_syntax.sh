#!/bin/bash
# fix_F11c_syntax.sh – naprawia błąd składni w export_to_html
# Uruchom w katalogu can_simulator/

set -e

echo "=== Naprawa składni w associative_controller.py ==="

if [ ! -f controllers/associative_controller.py ]; then
    echo "BŁĄD: controllers/associative_controller.py nie istnieje."
    exit 1
fi

python3 << 'PYEOF'
with open("controllers/associative_controller.py", "r") as f:
    content = f.read()

# Poprawiamy błędny fragment w metodzie export_to_html
old_bug = '''        with open(filepath, "w") as f:
            f.write("
.join(html))'''

correct = '''        with open(filepath, "w") as f:
            f.write("\\n".join(html))'''

if old_bug in content:
    content = content.replace(old_bug, correct)
    print("Poprawiono błąd składni w export_to_html.")
else:
    # Może bug wygląda inaczej? Próbujemy regex
    import re
    pattern = r'with open\(filepath, "w"\) as f:\s*f\.write\("[^"]*\.join\(html\)\)'
    if re.search(pattern, content):
        content = re.sub(pattern, correct, content)
        print("Poprawiono błąd składni (regex).")
    else:
        print("Nie znaleziono błędnego fragmentu – być może już poprawiony.")

with open("controllers/associative_controller.py", "w") as f:
    f.write(content)

print("Zapisano zmiany.")
PYEOF

python3 -m py_compile controllers/associative_controller.py && echo "  controller OK" || echo "  controller BŁĄD"

echo ""
echo "=== Naprawa zakończona ==="
echo "Możesz teraz ponownie uruchomić ./run.sh"
