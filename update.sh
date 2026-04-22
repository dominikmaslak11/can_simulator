#!/bin/bash
# =============================================================================
# Naprawa session_manager.py – usunięcie odwołania do notebooka
# =============================================================================

set -e

FILE="session_manager.py"
BACKUP="${FILE}.backup_session_$(date +%Y%m%d_%H%M%S)"

cp "$FILE" "$BACKUP"
echo "Kopia zapasowa: $BACKUP"

python3 - "$FILE" <<'EOF'
import re
import sys

file_path = sys.argv[1]
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Usuń linię z "notebook_tab"
content = re.sub(r'[ \t]*"notebook_tab": app\.notebook\.index\(.*?\),?\n', '', content)

# 2. W _collect_state dodaj zapis current_category (jeśli istnieje)
collect_pattern = r'(def _collect_state\(app\):.*?state = {.*?)\n(.*?return state)'
if 'current_category' not in content:
    new_line = '\n        if hasattr(app, "current_category"):\n            state["current_category"] = app.current_category\n'
    content = re.sub(collect_pattern, r'\1' + new_line + r'\2', content, flags=re.DOTALL)

# 3. W _restore_state dodaj odtworzenie kategorii
restore_pattern = r'(def _restore_state\(app, state\):.*?)(if "theme" in state:)'
restore_code = '''
        if "current_category" in state:
            cat = state["current_category"]
            for i, name in enumerate(app.sidebar.get(0, tk.END)):
                if name == cat:
                    app.sidebar.selection_set(i)
                    app._on_category_select()
                    break
'''
content = re.sub(restore_pattern, r'\1' + restore_code + r'\n        \2', content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("session_manager.py został naprawiony.")
EOF

echo ""
echo "=== Gotowe ==="
echo "Uruchom aplikację: sudo ./run.sh"
