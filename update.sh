#!/bin/bash
# =============================================================================
# Poprawka integracji DBC: odświeżanie list sygnałów w GUI
# =============================================================================

set -e

# Kopie zapasowe
BACKUP_DIR="backup_dbc_fix_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp gui/app.py gui/tabs/dbc_manager_tab.py gui/tabs/chart_tab.py gui/tabs/advanced_ml_tab.py "$BACKUP_DIR/"
echo "Kopie zapasowe utworzone w: $BACKUP_DIR"

# -----------------------------------------------------------------------------
# 1. Dodanie self.dbc_signals w app.py
# -----------------------------------------------------------------------------
python3 - <<'EOF'
import re
file = 'gui/app.py'
with open(file, 'r', encoding='utf-8') as f:
    content = f.read()

if 'self.dbc_signals' not in content:
    pattern = r'(self\.theme_var = tk\.StringVar\(value="light"\)\n)'
    replacement = r'\1        self.dbc_signals = []\n'
    content = re.sub(pattern, replacement, content)
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)
    print("app.py: dodano self.dbc_signals")
else:
    print("app.py: self.dbc_signals już istnieje")
EOF

# -----------------------------------------------------------------------------
# 2. dbc_manager_tab.py – zapisanie sygnałów do app.dbc_signals
# -----------------------------------------------------------------------------
python3 - <<'EOF'
import re
file = 'gui/tabs/dbc_manager_tab.py'
with open(file, 'r', encoding='utf-8') as f:
    content = f.read()

# Po pomyślnym wczytaniu DBC ustaw app.dbc_signals
pattern = r'(if app\.dbc_manager\.load_dbc\(path\):\s*\n\s*status_var\.set.*?\n.*?app\.log.*?\n)'
replacement = r'\1            update_signal_list()\n            app.dbc_signals = app.dbc_manager.get_available_signals()\n'
content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Usuń niepotrzebne, stare próby odwołań
content = re.sub(r'if hasattr\(app, "chart_tab"\).*?app\.chart_tab\.signal_combo\["values"\] = signals\n', '', content, flags=re.DOTALL)
content = re.sub(r'if hasattr\(app, "forecast_signal_combo"\).*?app\.forecast_signal_combo\["values"\] = signals\n', '', content, flags=re.DOTALL)

with open(file, 'w', encoding='utf-8') as f:
    f.write(content)
print("dbc_manager_tab.py: ustawiono app.dbc_signals")
EOF

# -----------------------------------------------------------------------------
# 3. chart_tab.py – dodanie comboboxa DBC
# -----------------------------------------------------------------------------
python3 - <<'EOF'
import re
file = 'gui/tabs/chart_tab.py'
with open(file, 'r', encoding='utf-8') as f:
    content = f.read()

if 'lub sygnał z DBC' not in content:
    # Wstawiamy nowy wiersz po refresh_btn
    pattern = r'(refresh_btn\.grid\(row=0, column=4, padx=5, pady=2\)\n)'
    replacement = (r'\1'
                   r'    ttk.Label(control_frame, text="lub sygnał z DBC:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)\n'
                   r'    chart_signal_combo = ttk.Combobox(control_frame, state="readonly", width=40)\n'
                   r'    chart_signal_combo.grid(row=1, column=1, columnspan=2, sticky=tk.W, padx=5, pady=2)\n'
                   r'    chart_signal_combo.bind("<Button-1>", lambda e: chart_signal_combo.configure(values=app.dbc_signals if hasattr(app, "dbc_signals") else []))\n'
                   r'    chart_signal_combo.bind("<<ComboboxSelected>>", lambda e: on_signal_selected(app, id_var, byte_var, chart_signal_combo))\n'
                   r'    app.chart_signal_combo = chart_signal_combo\n'
                   r'\n')
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    # Dodaj funkcję on_signal_selected wewnątrz setup_chart_tab
    func_def = '''
    def on_signal_selected(app, id_var, byte_var, combo):
        selected = combo.get()
        if not selected or not hasattr(app, 'dbc_manager'):
            return
        try:
            msg_name, sig_name = selected.split('.')
            db = app.dbc_manager.db
            msg = db.get_message_by_name(msg_name)
            id_var.set(hex(msg.frame_id))
            sig = msg.get_signal_by_name(sig_name)
            byte_var.set(sig.start // 8)
        except Exception:
            pass
'''
    # Wstaw przed "Inicjalizacja listy ID"
    content = re.sub(r'(\n    # Inicjalizacja listy ID\n)', func_def + r'\1', content, flags=re.DOTALL)

with open(file, 'w', encoding='utf-8') as f:
    f.write(content)
print("chart_tab.py: dodano combobox DBC")
EOF

# -----------------------------------------------------------------------------
# 4. advanced_ml_tab.py – combobox korzysta z app.dbc_signals
# -----------------------------------------------------------------------------
python3 - <<'EOF'
import re
file = 'gui/tabs/advanced_ml_tab.py'
with open(file, 'r', encoding='utf-8') as f:
    content = f.read()

pattern = r'(forecast_signal_combo = ttk\.Combobox\(frame, state="readonly", width=40\)\n)'
replacement = r'\1    forecast_signal_combo.bind("<Button-1>", lambda e: forecast_signal_combo.configure(values=app.dbc_signals if hasattr(app, "dbc_signals") else []))\n'
content = re.sub(pattern, replacement, content)

# Usuń stare próby wypełniania
content = re.sub(r'if hasattr\(app, "dbc_manager".*?forecast_signal_combo\["values"\] = signals\n', '', content, flags=re.DOTALL)

with open(file, 'w', encoding='utf-8') as f:
    f.write(content)
print("advanced_ml_tab.py: combobox DBC zaktualizowany")
EOF

echo ""
echo "=== Wszystkie poprawki zostały wprowadzone ==="
echo "Uruchom aplikację i przetestuj:"
echo "1. Wczytaj plik DBC w zakładce 'DBC Manager'."
echo "2. Sprawdź, czy lista sygnałów się wypełniła."
echo "3. Przejdź do zakładki 'Wykresy' – kliknij combobox 'lub sygnał z DBC'."
echo "4. W zakładce 'Zaawansowane ML → Prognozowanie' kliknij combobox sygnałów DBC."
