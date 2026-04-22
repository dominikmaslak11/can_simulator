#!/bin/bash
# update.sh – Etap C: Integracja z ekosystemem (Parquet, MDF4, edytor DBC)
# Uruchom w głównym katalogu projektu (can_simulator)

set -e

echo "==> Rozpoczynam aktualizację – Etap C: Integracja z ekosystemem"

# ----------------------------------------------------------------------
# 1. Dodanie zależności
# ----------------------------------------------------------------------
echo "  -> Aktualizacja requirements.txt"

if ! grep -q "pyarrow" requirements.txt; then
    echo "pyarrow>=14.0.0" >> requirements.txt
fi
if ! grep -q "asammdf" requirements.txt; then
    echo "asammdf>=7.0.0" >> requirements.txt
fi

# Instalacja nowych bibliotek
source venv/bin/activate
pip install pyarrow asammdf

# ----------------------------------------------------------------------
# 2. Eksport do Parquet w Snifferze
# ----------------------------------------------------------------------
echo "  -> Dodawanie eksportu do Parquet"

cat >> controllers/sniffer/export.py << 'EOF'

    def export_parquet(self):
        """Eksportuje zawartość tabeli do pliku Parquet."""
        from tkinter import filedialog
        import pyarrow as pa
        import pyarrow.parquet as pq

        filepath = filedialog.asksaveasfilename(
            defaultextension=".parquet",
            filetypes=[("Pliki Parquet", "*.parquet"), ("Wszystkie pliki", "*.*")]
        )
        if not filepath:
            return

        tree = self.app.sniffer_tree
        rows = []
        for item in tree.get_children():
            values = tree.item(item, 'values')
            if len(values) >= 5:
                timestamp = values[0]
                can_id = int(values[1], 16)
                data_hex = values[4]
                if ' ' in data_hex:
                    data_hex = self._bits_to_hex(data_hex)
                rows.append({
                    'timestamp': timestamp,
                    'can_id': can_id,
                    'data': data_hex,
                    'dlc': len(bytes.fromhex(data_hex))
                })

        if rows:
            table = pa.Table.from_pylist(rows)
            pq.write_table(table, filepath)
            self.log(f"[Sniffer] Wyeksportowano {len(rows)} ramek do Parquet: {filepath}")
EOF

# Dodanie przycisku w sniffer_tab.py
python3 << 'PYTHON_EOF'
with open('gui/tabs/sniffer_tab.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'text="Eksportuj do Parquet"' not in content:
    content = content.replace(
        'export_asc_btn = ttk.Button(toolbar, text="Eksportuj do ASC", command=app.sniffer_ctrl.export_asc)',
        'export_asc_btn = ttk.Button(toolbar, text="Eksportuj do ASC", command=app.sniffer_ctrl.export_asc)\n    export_parquet_btn = ttk.Button(toolbar, text="Eksportuj do Parquet", command=app.sniffer_ctrl.export_parquet)\n    export_parquet_btn.pack(side=tk.LEFT, padx=2)'
    )
    with open('gui/tabs/sniffer_tab.py', 'w', encoding='utf-8') as f:
        f.write(content)
print("Dodano przycisk eksportu Parquet w Snifferze.")
PYTHON_EOF

# ----------------------------------------------------------------------
# 3. Eksport do MDF4
# ----------------------------------------------------------------------
echo "  -> Dodawanie eksportu do MDF4"

cat >> controllers/sniffer/export.py << 'EOF'

    def export_mdf4(self):
        """Eksportuje zawartość tabeli do pliku MDF4."""
        from tkinter import filedialog
        import asammdf
        import numpy as np
        from datetime import datetime

        filepath = filedialog.asksaveasfilename(
            defaultextension=".mf4",
            filetypes=[("Pliki MDF4", "*.mf4"), ("Wszystkie pliki", "*.*")]
        )
        if not filepath:
            return

        tree = self.app.sniffer_tree
        signals = {}
        timestamps = []

        for item in tree.get_children():
            values = tree.item(item, 'values')
            if len(values) >= 5:
                ts_str = values[0]
                try:
                    dt = datetime.strptime(ts_str, "%H:%M:%S.%f")
                    t = dt.hour*3600 + dt.minute*60 + dt.second + dt.microsecond/1e6
                except:
                    t = 0.0
                timestamps.append(t)
                can_id = values[1]
                data_hex = values[4]
                if ' ' in data_hex:
                    data_hex = self._bits_to_hex(data_hex)
                data_bytes = bytes.fromhex(data_hex)
                for i, byte in enumerate(data_bytes):
                    sig_name = f"{can_id}_B{i}"
                    signals.setdefault(sig_name, []).append(byte)

        if timestamps:
            mdf = asammdf.MDF()
            timestamps_np = np.array(timestamps, dtype=np.float64)
            for name, values in signals.items():
                if len(values) == len(timestamps):
                    sig = asammdf.Signal(
                        samples=np.array(values, dtype=np.uint8),
                        timestamps=timestamps_np,
                        name=name,
                        unit=''
                    )
                    mdf.append(sig)
            mdf.save(filepath, overwrite=True)
            self.log(f"[Sniffer] Wyeksportowano do MDF4: {filepath}")
EOF

# Dodanie przycisku
python3 << 'PYTHON_EOF'
with open('gui/tabs/sniffer_tab.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'text="Eksportuj do MDF4"' not in content:
    content = content.replace(
        'export_parquet_btn = ttk.Button(toolbar, text="Eksportuj do Parquet", command=app.sniffer_ctrl.export_parquet)',
        'export_parquet_btn = ttk.Button(toolbar, text="Eksportuj do Parquet", command=app.sniffer_ctrl.export_parquet)\n    export_mdf4_btn = ttk.Button(toolbar, text="Eksportuj do MDF4", command=app.sniffer_ctrl.export_mdf4)\n    export_mdf4_btn.pack(side=tk.LEFT, padx=2)'
    )
    with open('gui/tabs/sniffer_tab.py', 'w', encoding='utf-8') as f:
        f.write(content)
print("Dodano przycisk eksportu MDF4 w Snifferze.")
PYTHON_EOF

# ----------------------------------------------------------------------
# 4. Edytor DBC w GUI
# ----------------------------------------------------------------------
echo "  -> Dodawanie podstawowego edytora DBC"

cat >> controllers/sniffer/dbc_handler.py << 'EOF'

    def open_dbc_editor(self):
        """Otwiera okno edytora DBC."""
        if not self.dbc_db:
            messagebox.showinfo("Brak DBC", "Najpierw wczytaj plik DBC.")
            return

        win = tk.Toplevel(self.app.root)
        win.title("Edytor DBC")
        win.geometry("800x600")
        win.transient(self.app.root)
        win.grab_set()

        tree = ttk.Treeview(win, columns=('message', 'signal', 'start', 'length'), show='headings')
        tree.heading('message', text='ID (hex)')
        tree.heading('signal', text='Sygnał')
        tree.heading('start', text='Start bit')
        tree.heading('length', text='Długość')

        for msg in self.dbc_db.messages:
            for sig in msg.signals:
                tree.insert('', tk.END, values=(
                    f"0x{msg.frame_id:08X}",
                    sig.name,
                    sig.start,
                    sig.length
                ))

        tree.pack(fill=tk.BOTH, expand=True)
        ttk.Button(win, text="Zapisz jako...", command=lambda: self.save_dbc_as()).pack(pady=10)

    def save_dbc_as(self):
        """Zapisuje aktualną bazę DBC do nowego pliku."""
        from tkinter import filedialog
        import cantools

        filepath = filedialog.asksaveasfilename(defaultextension=".dbc", filetypes=[("Pliki DBC", "*.dbc")])
        if not filepath:
            return
        try:
            cantools.database.dump_file(self.dbc_db, filepath)
            self.log(f"[DBC] Zapisano do {filepath}")
        except Exception as e:
            messagebox.showerror("Błąd zapisu", str(e))
EOF

# Dodanie przycisku w sniffer_tab.py
python3 << 'PYTHON_EOF'
with open('gui/tabs/sniffer_tab.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'text="Edytor DBC"' not in content:
    content = content.replace(
        'dbc_load_btn = ttk.Button(toolbar, text="Wczytaj DBC", command=app.sniffer_ctrl.load_dbc_file)',
        'dbc_load_btn = ttk.Button(toolbar, text="Wczytaj DBC", command=app.sniffer_ctrl.load_dbc_file)\n    dbc_edit_btn = ttk.Button(toolbar, text="Edytor DBC", command=app.sniffer_ctrl.open_dbc_editor)\n    dbc_edit_btn.pack(side=tk.LEFT, padx=2)'
    )
    with open('gui/tabs/sniffer_tab.py', 'w', encoding='utf-8') as f:
        f.write(content)
print("Dodano przycisk Edytor DBC.")
PYTHON_EOF

# ----------------------------------------------------------------------
# 5. Sprawdzenie składni
# ----------------------------------------------------------------------
echo "  -> Sprawdzanie składni..."
python3 -m py_compile controllers/sniffer/export.py
python3 -m py_compile controllers/sniffer/dbc_handler.py
python3 -m py_compile gui/tabs/sniffer_tab.py

echo "==> Etap C zakończony!"
echo "Nowe funkcje:"
echo "  - Eksport do Parquet (przycisk w Snifferze)"
echo "  - Eksport do MDF4 (przycisk w Snifferze)"
echo "  - Podstawowy edytor DBC (przycisk 'Edytor DBC')"
