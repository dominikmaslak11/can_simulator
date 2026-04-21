#!/bin/bash
# fix_app_indentation_final.sh – definitywna naprawa wcięć w gui/app.py
# Uruchom w głównym katalogu projektu (can_simulator)

set -e

echo "==> Definitywna naprawa wcięć w gui/app.py"

python3 << 'PYTHON_EOF'
import re

with open('gui/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Wyszukujemy metodę on_closing i podmieniamy ją na poprawną wersję
new_on_closing = '''    def on_closing(self):
        self.manual_cyclic_active = False
        if self.sim_thread:
            self.sim_thread.stop()
        if self.binary_thread:
            self.binary_thread.stop()
        from session_manager import SessionManager
        SessionManager.save_session(self)
        self.can.disconnect()
        self.root.destroy()'''

# Używamy wyrażenia regularnego, aby znaleźć i zastąpić starą metodę
pattern = r'    def on_closing\(self\):.*?(?=\n    def |\nclass |\Z)'
content = re.sub(pattern, new_on_closing, content, flags=re.DOTALL)

# Dodatkowo upewniamy się, że metoda load_session jest poprawnie wcięta
new_load_session = '''    def load_session(self):
        """Wczytuje poprzednią sesję."""
        from session_manager import SessionManager
        if SessionManager.load_session(self):
            self.log("Przywrócono poprzednią sesję.")'''

content = re.sub(r'    def load_session\(self\):.*?(?=\n    def |\nclass |\Z)',
                 new_load_session, content, flags=re.DOTALL)

# Zapisujemy
with open('gui/app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Metody on_closing i load_session zostały poprawione.")
PYTHON_EOF

echo "==> Sprawdzanie składni..."
python3 -m py_compile gui/app.py

echo "==> Gotowe. Aplikacja powinna się teraz uruchomić."
