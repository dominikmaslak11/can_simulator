#!/bin/bash
# Naprawia błąd wcięć w app.py (metoda _create_network_frame wewnątrz innej metody)

set -e

APP_FILE="gui/app.py"
BACKUP="${APP_FILE}.backup_indent_$(date +%Y%m%d_%H%M%S)"

cp "$APP_FILE" "$BACKUP"
echo "Kopia zapasowa: $BACKUP"

python3 - "$APP_FILE" <<'EOF'
import re
import sys

file_path = sys.argv[1]
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Usuń źle wciętą metodę _create_network_frame (wraz z ciałem)
pattern_bad = r'        def _create_network_frame\(self, parent\):.*?(?=\n    def _create_macro_frame)'
content = re.sub(pattern_bad, '', content, flags=re.DOTALL)

# Wstaw poprawnie sformatowaną metodę przed _create_macro_frame
new_method = '''    def _create_network_frame(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)

        tab_server = ttk.Frame(notebook)
        notebook.add(tab_server, text="Serwer TCP")
        server_tab.setup_server_tab(self, tab_server)

        tab_remote = ttk.Frame(notebook)
        notebook.add(tab_remote, text="Zdalny monitoring")
        setup_remote_monitor_tab(self, tab_remote)

        tab_generator = ttk.Frame(notebook)
        notebook.add(tab_generator, text="Generator ruchu")
        generator_tab.setup_generator_tab(self, tab_generator)

        tab_bridge = ttk.Frame(notebook)
        notebook.add(tab_bridge, text="Mostek vCAN")
        setup_bridge_tab(self, tab_bridge)

'''
content = re.sub(r'(\n    def _create_macro_frame\(self, parent\):)', new_method + r'\1', content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Poprawiono wcięcia w app.py.")
EOF

echo "Gotowe. Uruchom aplikację: sudo ./run.sh"
