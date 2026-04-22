#!/bin/bash
# Naprawia błąd AttributeError w bridge_tab.py

set -e

FILE="gui/tabs/bridge_tab.py"
BACKUP="${FILE}.backup_order_$(date +%Y%m%d_%H%M%S)"

cp "$FILE" "$BACKUP"
echo "Kopia zapasowa: $BACKUP"

python3 - "$FILE" <<'EOF'
import re, sys
file_path = sys.argv[1]
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Usuń błędnie umieszczony blok wczytywania
content = re.sub(
    r'(\n        # Wczytaj zapisane ustawienia.*?self\.filter_var\.set\(app\.bridge_filter\)\n)',
    '',
    content,
    flags=re.DOTALL
)

# Wstaw poprawny blok po _process_queue()
pattern = r'(self\._process_queue\(\)\n)'
replacement = r'''\1
        # Wczytaj zapisane ustawienia
        if hasattr(app, 'bridge_url'):
            self.url_var.set(app.bridge_url)
        if hasattr(app, 'bridge_token'):
            self.token_var.set(app.bridge_token)
        if hasattr(app, 'bridge_filter'):
            self.filter_var.set(app.bridge_filter)
'''
content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("bridge_tab.py naprawiony.")
EOF

echo "Gotowe. Uruchom aplikację: sudo ./run.sh"
