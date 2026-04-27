#!/bin/bash
# update_F.sh – Faza 0: Infrastruktura dla uczenia asocjacyjnego
# Uruchom w katalogu can_simulator/

set -e

echo "=== Wdrażanie Fazy 0: Uczenie asocjacyjne – infrastruktura ==="

# ---------- 1. Tworzenie katalogów ----------
mkdir -p controllers gui/tabs

# ---------- 2. associative_controller.py (szkielet) ----------
if [ ! -f controllers/associative_controller.py ]; then
    cat > controllers/associative_controller.py << 'EOF'
"""Kontroler interaktywnego uczenia asocjacyjnego."""
import logging

logger = logging.getLogger("AssociativeController")


class AssociativeController:
    def __init__(self, app):
        self.app = app
        self.running = False
        self.event_active = False
        self.listener_id = None

    def start(self):
        if self.running:
            return
        self.running = True
        # Podłączenie nasłuchu CAN
        self.listener_id = self.app.can.add_listener(self._on_message)
        logger.info("AssociativeController uruchomiony")

    def stop(self):
        self.running = False
        if self.listener_id is not None:
            self.app.can.remove_listener(self.listener_id)
            self.listener_id = None
        logger.info("AssociativeController zatrzymany")

    def toggle_event(self):
        """Przełącza stan zdarzenia (hamulec wciśnięty/puszczony)."""
        self.event_active = not self.event_active
        if self.event_active:
            logger.info("Zdarzenie ROZPOCZĘTE")
        else:
            logger.info("Zdarzenie ZAKOŃCZONE")

    def _on_message(self, msg):
        if not self.running:
            return
        # TODO: buforowanie ramek
        pass
EOF
    echo "Utworzono controllers/associative_controller.py"
else
    echo "associative_controller.py już istnieje – pomijam."
fi

# ---------- 3. associative_tab.py (szablon GUI) ----------
if [ ! -f gui/tabs/associative_tab.py ]; then
    cat > gui/tabs/associative_tab.py << 'EOF'
"""Zakładka uczenia asocjacyjnego."""
import tkinter as tk
from tkinter import ttk, messagebox


class AssociativeTab(ttk.Frame):
    def __init__(self, app, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.create_widgets()

    def create_widgets(self):
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # Nagłówek
        ttk.Label(frame, text="Interaktywne uczenie asocjacyjne",
                  font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=(0,10))

        # Sterowanie
        ctrl_frame = ttk.Frame(frame)
        ctrl_frame.pack(fill=tk.X, pady=5)

        self.btn_start = ttk.Button(ctrl_frame, text="Start uczenia",
                                    command=self.start_learning)
        self.btn_start.pack(side=tk.LEFT, padx=5)

        self.btn_stop = ttk.Button(ctrl_frame, text="Stop uczenia",
                                   command=self.stop_learning, state='disabled')
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        self.btn_clear = ttk.Button(ctrl_frame, text="Wyczyść dane",
                                    command=self.clear_data)
        self.btn_clear.pack(side=tk.LEFT, padx=5)

        # Checkbox zdarzenia
        self.check_var = tk.BooleanVar()
        self.checkbox = ttk.Checkbutton(ctrl_frame, text="Zdarzenie (np. Hamulec)",
                                        variable=self.check_var,
                                        command=self.toggle_event)
        self.checkbox.pack(side=tk.RIGHT, padx=5)

        # Okno tolerancji
        tolerance_frame = ttk.Frame(frame)
        tolerance_frame.pack(fill=tk.X, pady=5)
        ttk.Label(tolerance_frame, text="Tolerancja czasowa (±ms):").pack(side=tk.LEFT)
        self.tolerance_var = tk.IntVar(value=200)
        ttk.Spinbox(tolerance_frame, from_=0, to=5000,
                    textvariable=self.tolerance_var, width=8).pack(side=tk.LEFT, padx=5)

        # Tabela wyników
        columns = ("id", "byte", "value", "confidence", "samples")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=8)
        self.tree.heading("id", text="CAN ID")
        self.tree.heading("byte", text="Bajt")
        self.tree.heading("value", text="Wartość")
        self.tree.heading("confidence", text="Pewność (%)")
        self.tree.heading("samples", text="Próbki")
        self.tree.column("id", width=100)
        self.tree.column("byte", width=60)
        self.tree.column("value", width=80)
        self.tree.column("confidence", width=100)
        self.tree.column("samples", width=80)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=10)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Pasek postępu
        status_frame = ttk.Frame(frame)
        status_frame.pack(fill=tk.X, pady=5)
        ttk.Label(status_frame, text="Postęp:").pack(side=tk.LEFT)
        self.progress = ttk.Progressbar(status_frame, length=200, mode='determinate')
        self.progress.pack(side=tk.LEFT, padx=5)
        self.iter_label = ttk.Label(status_frame, text="Iteracje: 0")
        self.iter_label.pack(side=tk.LEFT, padx=5)

    # Podstawowe metody – logika zostanie dodana w kolejnych fazach
    def start_learning(self):
        if not self.app.can.connected:
            messagebox.showerror("Błąd", "Połącz się z CAN przed rozpoczęciem uczenia.")
            return
        # TODO: uruchomienie kontrolera
        self.btn_start.config(state='disabled')
        self.btn_stop.config(state='normal')
        self.app.log("[Assoc] Rozpoczęto uczenie asocjacyjne")

    def stop_learning(self):
        # TODO: zatrzymanie kontrolera
        self.btn_start.config(state='normal')
        self.btn_stop.config(state='disabled')
        self.app.log("[Assoc] Zatrzymano uczenie asocjacyjne")

    def clear_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.progress['value'] = 0
        self.iter_label.config(text="Iteracje: 0")
        self.app.log("[Assoc] Wyczyszczono dane")

    def toggle_event(self):
        if self.check_var.get():
            self.app.log("[Assoc] Zdarzenie ROZPOCZĘTE")
        else:
            self.app.log("[Assoc] Zdarzenie ZAKOŃCZONE")
        # TODO: powiadomienie kontrolera
EOF
    echo "Utworzono gui/tabs/associative_tab.py"
else
    echo "associative_tab.py już istnieje – pomijam."
fi

# ---------- 4. Modyfikacja gui/app.py (dodanie kategorii i skrótu) ----------
if [ -f gui/app.py ]; then
    python3 << 'PYEOF'
import re

with open("gui/app.py", "r") as f:
    content = f.read()

# a) Dodaj import (jeśli brak)
if "from gui.tabs.associative_tab import AssociativeTab" not in content:
    # Wstaw po ostatnim from gui.tabs...
    content = content.replace(
        "from gui.tabs.ecu_tab import EcuTab",
        "from gui.tabs.ecu_tab import EcuTab\nfrom gui.tabs.associative_tab import AssociativeTab"
    )

# b) Dodaj kategorię „Uczenie asocjacyjne” do listy categories (jeśli brak)
if '"Uczenie asocjacyjne"' not in content:
    old_snippet = '("DBC Manager", self._create_dbc_frame),'
    new_snippet = '("DBC Manager", self._create_dbc_frame),\n            ("Uczenie asocjacyjne", self._create_associative_frame),'
    content = content.replace(old_snippet, new_snippet)

# c) Dodaj metodę _create_associative_frame (jeśli brak)
if "def _create_associative_frame" not in content:
    method = '''
    def _create_associative_frame(self, parent):
        self.associative_tab = AssociativeTab(self, parent)
        self.associative_tab.pack(fill=tk.BOTH, expand=True)
'''
    # Wstaw przed _create_dbc_frame (lub przed bind_shortcuts)
    if "def _create_dbc_frame" in content:
        content = content.replace("    def _create_dbc_frame", method + "\n    def _create_dbc_frame")
    else:
        # fallback: przed bind_shortcuts
        content = content.replace("    def bind_shortcuts(self):", method + "\n    def bind_shortcuts(self):")

# d) Dodaj skrót Ctrl+H do bind_shortcuts (jeśli brak)
if "'<Control-h>'" not in content and '"<Control-h>"' not in content:
    content = content.replace(
        "self.root.bind('<Control-o>', lambda e: self.import_project())",
        "self.root.bind('<Control-o>', lambda e: self.import_project())\n        self.root.bind('<Control-h>', lambda e: self.associative_tab.toggle_event())"
    )

with open("gui/app.py", "w") as f:
    f.write(content)
print("Zaktualizowano gui/app.py o kategorię uczenia asocjacyjnego i skrót Ctrl+H.")
PYEOF
else
    echo "UWAGA: gui/app.py nie istnieje!"
fi

# ---------- 5. Sprawdzenie składni ----------
echo ""
echo "Sprawdzanie składni nowych/modyfikowanych plików:"
python3 -m py_compile controllers/associative_controller.py 2>&1 && echo "  associative_controller.py OK" || echo "  associative_controller.py BŁĄD"
python3 -m py_compile gui/tabs/associative_tab.py 2>&1 && echo "  associative_tab.py OK" || echo "  associative_tab.py BŁĄD"
python3 -m py_compile gui/app.py 2>&1 && echo "  app.py OK" || echo "  app.py BŁĄD"

echo ""
echo "=== Faza 0 wdrożona pomyślnie ==="
echo "Możesz teraz uruchomić aplikację i zobaczyć nową kategorię 'Uczenie asocjacyjne'."
echo "W kolejnych fazach dodamy bufor i analizę."
