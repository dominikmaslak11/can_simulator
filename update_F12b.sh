#!/bin/bash
# update_F12b.sh – Faza 12b: GUI J1939 Browser i nowa kategoria w sidebarze
# Uruchom w katalogu can_simulator/

set -e

echo "=== Wdrażanie Fazy 12b: GUI J1939 ==="

# ---------- 1. gui/tabs/j1939_tab.py ----------
mkdir -p gui/tabs

if [ ! -f gui/tabs/j1939_tab.py ]; then
    cat > gui/tabs/j1939_tab.py << 'EOF'
"""Zakładka J1939 Browser."""
import tkinter as tk
from tkinter import ttk, messagebox
from controllers.j1939_controller import J1939Controller
from parsers_j1939 import parse_j1939_id


class J1939Tab(ttk.Frame):
    def __init__(self, app, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.controller = None
        self.create_widgets()

    def create_widgets(self):
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # Nagłówek
        ttk.Label(frame, text="J1939 Browser",
                  font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=(0,10))

        # Sterowanie
        ctrl_frame = ttk.Frame(frame)
        ctrl_frame.pack(fill=tk.X, pady=5)

        self.btn_start = ttk.Button(ctrl_frame, text="Start", command=self.start_browser)
        self.btn_start.pack(side=tk.LEFT, padx=5)

        self.btn_stop = ttk.Button(ctrl_frame, text="Stop", command=self.stop_browser, state='disabled')
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        self.btn_clear = ttk.Button(ctrl_frame, text="Wyczyść", command=self.clear)
        self.btn_clear.pack(side=tk.LEFT, padx=5)

        # Filtr PGN
        ttk.Label(ctrl_frame, text="Filtr PGN (hex):").pack(side=tk.LEFT, padx=(20,5))
        self.filter_var = tk.StringVar()
        ttk.Entry(ctrl_frame, textvariable=self.filter_var, width=10).pack(side=tk.LEFT)
        ttk.Button(ctrl_frame, text="Zastosuj", command=self.refresh).pack(side=tk.LEFT, padx=5)

        # Tabela
        columns = ("timestamp", "pgn", "pgn_name", "priority", "source", "dlc", "data")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=15)
        self.tree.heading("timestamp", text="Czas")
        self.tree.heading("pgn", text="PGN")
        self.tree.heading("pgn_name", text="Nazwa PGN")
        self.tree.heading("priority", text="Prio")
        self.tree.heading("source", text="Source")
        self.tree.heading("dlc", text="DLC")
        self.tree.heading("data", text="Data")
        self.tree.column("timestamp", width=100)
        self.tree.column("pgn", width=80)
        self.tree.column("pgn_name", width=180)
        self.tree.column("priority", width=50)
        self.tree.column("source", width=60)
        self.tree.column("dlc", width=40)
        self.tree.column("data", width=150)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=10)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def start_browser(self):
        if not self.app.can.connected:
            messagebox.showerror("Błąd", "Połącz się z CAN przed uruchomieniem.")
            return
        if self.controller is None:
            self.controller = J1939Controller(self.app)
        self.controller.start()
        self.btn_start.config(state='disabled')
        self.btn_stop.config(state='normal')
        self.app.log("[J1939] Browser uruchomiony")
        self._refresh_loop()

    def stop_browser(self):
        if self.controller:
            self.controller.stop()
        self.btn_start.config(state='normal')
        self.btn_stop.config(state='disabled')
        self.app.log("[J1939] Browser zatrzymany")

    def clear(self):
        if self.controller:
            self.controller.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)

    def refresh(self):
        self._fill_table()

    def _fill_table(self):
        if not self.controller:
            return
        frames = self.controller.get_frames()
        filter_str = self.filter_var.get().strip()
        # Usuwamy stare wpisy (prosta strategia – możemy też dodawać tylko nowe)
        for item in self.tree.get_children():
            self.tree.delete(item)
        for rec in reversed(frames):
            parsed = parse_j1939_id(rec["arb_id"])
            pgn = parsed["pgn"]
            # Filtrowanie
            if filter_str:
                try:
                    wanted = int(filter_str, 16)
                    if pgn != wanted:
                        continue
                except ValueError:
                    self.app.log("[J1939] Niepoprawny filtr PGN")
                    return
            pgn_name = self.controller.get_pgn_name(pgn) or ""
            values = (
                f"{rec['timestamp']:.3f}",
                f"0x{pgn:04X}",
                pgn_name,
                str(parsed["priority"]),
                f"0x{parsed['source_address']:02X}",
                str(rec["dlc"]),
                bytes(rec["data"]).hex().upper()
            )
            self.tree.insert("", "end", values=values)

    def _refresh_loop(self):
        if self.controller and self.controller.running:
            self._fill_table()
            self.after(1000, self._refresh_loop)
        else:
            self._fill_table()  # ostatnie dane po zatrzymaniu
EOF
    echo "Utworzono gui/tabs/j1939_tab.py"
else
    echo "j1939_tab.py już istnieje"
fi

# ---------- 2. Aktualizacja gui/app.py (nowa kategoria "Protokoły") ----------
if [ -f gui/app.py ]; then
    python3 << 'PYEOF'
with open("gui/app.py", "r") as f:
    content = f.read()

# a) Import (jeśli brak)
if "from gui.tabs.j1939_tab import J1939Tab" not in content:
    content = content.replace(
        "from gui.tabs.associative_tab import AssociativeTab",
        "from gui.tabs.associative_tab import AssociativeTab\nfrom gui.tabs.j1939_tab import J1939Tab"
    )
    print("Dodano import J1939Tab.")

# b) Dodaj kategorię "Protokoły" do listy categories
if '"Protokoły"' not in content:
    old_line = '("Uczenie asocjacyjne", self._create_associative_frame),'
    new_line = '("Uczenie asocjacyjne", self._create_associative_frame),\n            ("Protokoły", self._create_protocols_frame),'
    content = content.replace(old_line, new_line)
    print("Dodano kategorię 'Protokoły'.")

# c) Dodaj metodę _create_protocols_frame
if "def _create_protocols_frame" not in content:
    method = '''
    def _create_protocols_frame(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)
        tab_j1939 = ttk.Frame(notebook)
        notebook.add(tab_j1939, text="J1939 Browser")
        self.j1939_tab = J1939Tab(self, tab_j1939)
        self.j1939_tab.pack(fill=tk.BOTH, expand=True)
'''
    # Wstaw przed _create_associative_frame
    if "def _create_associative_frame" in content:
        content = content.replace("    def _create_associative_frame", method + "\n    def _create_associative_frame")
        print("Dodano metodę _create_protocols_frame.")
    else:
        print("Nie znaleziono _create_associative_frame, wstawiam na końcu.")
        content += "\n" + method

with open("gui/app.py", "w") as f:
    f.write(content)
PYEOF
else
    echo "gui/app.py nie istnieje!"
fi

# Sprawdzenie składni
python3 -m py_compile gui/tabs/j1939_tab.py && echo "  j1939_tab.py OK" || echo "  j1939_tab.py BŁĄD"
python3 -m py_compile gui/app.py && echo "  app.py OK" || echo "  app.py BŁĄD"

echo ""
echo "=== Faza 12b zakończona ==="
echo "Uruchom update_F12c.sh"
