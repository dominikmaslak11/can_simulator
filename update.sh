#!/bin/bash
# Usuwa duplikat "Mostek vCAN" z listy kategorii w sidebarze

set -e

APP_FILE="gui/app.py"
BACKUP="${APP_FILE}.backup_rm_dup_bridge_$(date +%Y%m%d_%H%M%S)"

cp "$APP_FILE" "$BACKUP"
echo "Kopia zapasowa: $BACKUP"

python3 - "$APP_FILE" <<'EOF'
import re
import sys

file_path = sys.argv[1]
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Znajdź listę categories (zakładamy, że jest w formacie jak wyżej)
pattern = r'(categories = \[\n.*?\n\s*\])'
match = re.search(pattern, content, flags=re.DOTALL)
if match:
    cat_block = match.group(1)
    lines = cat_block.split('\n')
    new_lines = []
    seen_bridge = False
    for line in lines:
        if '"Mostek vCAN"' in line:
            if not seen_bridge:
                new_lines.append(line)
                seen_bridge = True
            # else pomijamy duplikat
        else:
            new_lines.append(line)
    new_cat_block = '\n'.join(new_lines)
    content = content[:match.start()] + new_cat_block + content[match.end():]
    print("Duplikat 'Mostek vCAN' usunięty z listy kategorii.")
else:
    print("Nie znaleziono listy kategorii – sprawdź ręcznie.")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
EOF

echo "Gotowe. Uruchom aplikację: sudo ./run.sh"
