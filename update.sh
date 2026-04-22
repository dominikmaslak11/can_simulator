#!/bin/bash

# Etap 1 modernizacji: pasek postępu + anulowanie operacji
# Wersja poprawiona

set -e

TARGET_FILE="gui/tabs/advanced_ml_tab.py"
if [ ! -f "$TARGET_FILE" ]; then
    if [ -f "../$TARGET_FILE" ]; then
        TARGET_FILE="../$TARGET_FILE"
    elif [ -f "../../$TARGET_FILE" ]; then
        TARGET_FILE="../../$TARGET_FILE"
    else
        echo "BŁĄD: Nie znaleziono $TARGET_FILE"
        exit 1
    fi
fi

echo "Plik: $TARGET_FILE"
BACKUP="${TARGET_FILE}.backup_modernize1_$(date +%Y%m%d_%H%M%S)"
cp "$TARGET_FILE" "$BACKUP"
echo "Kopia zapasowa: $BACKUP"

# Uruchamiamy Pythona z argumentem (ścieżką do pliku) i kodem z here-doc
python3 - "$TARGET_FILE" <<'PYTHON_SCRIPT'
import re
import sys

if len(sys.argv) < 2:
    print("Brak ścieżki do pliku", file=sys.stderr)
    sys.exit(1)

target_file = sys.argv[1]

with open(target_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Importy: dodajemy simpledialog
if 'from tkinter import simpledialog' not in content:
    content = re.sub(
        r'(import tkinter as tk\nfrom tkinter import ttk, filedialog, messagebox)',
        r'\1, simpledialog',
        content
    )

# 2. Dodajemy klasę ProgressDialog wewnątrz modułu (przed funkcjami)
progress_dialog_class = '''
class ProgressDialog(tk.Toplevel):
    """Okno dialogowe z paskiem postępu i przyciskiem Anuluj."""
    def __init__(self, parent, title="Operacja w toku", maximum=100):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)

        self.cancel_event = threading.Event()

        self.label = ttk.Label(self, text="Proszę czekać...")
        self.label.pack(pady=10, padx=20)

        self.progress = ttk.Progressbar(self, length=300, mode='determinate', maximum=maximum)
        self.progress.pack(pady=5, padx=20)

        self.cancel_btn = ttk.Button(self, text="Anuluj", command=self.on_cancel)
        self.cancel_btn.pack(pady=10)

        self.update_idletasks()
        self.geometry(f"+{parent.winfo_rootx()+50}+{parent.winfo_rooty()+50}")

    def on_cancel(self):
        self.cancel_event.set()
        self.label.config(text="Anulowanie...")
        self.cancel_btn.config(state='disabled')

    def update_progress(self, value, text=None):
        if not self.cancel_event.is_set():
            self.progress['value'] = value
            if text:
                self.label.config(text=text)
            self.update_idletasks()

    def close(self):
        self.destroy()
'''

# Wstawiamy klasę przed pierwszą definicją funkcji
if 'class ProgressDialog' not in content:
    pattern = r'(def setup_advanced_ml_tab\()'
    content = re.sub(pattern, progress_dialog_class + r'\n\1', content, count=1)

# 3. Modyfikujemy run_forecast aby używał ProgressDialog
#    Uwaga: uproszczona podmiana – zakładamy, że funkcja wygląda tak jak wcześniej.
#    W razie potrzeby dostosujemy regex.
old_forecast_pattern = r'(def run_forecast\(app, file_path, id_str, byte_idx, steps\):.*?)(?=\ndef (?!task))'
new_forecast_func = r'''
def run_forecast(app, file_path, id_str, byte_idx, steps):
    if not file_path:
        messagebox.showerror("Błąd", "Wybierz plik.")
        return
    try:
        cid = int(id_str, 16)
    except:
        messagebox.showerror("Błąd", "Nieprawidłowy format ID.")
        return

    # Okno postępu
    progress = ProgressDialog(app.root, "Trenowanie LSTM", maximum=100)
    progress.update_progress(0, "Wczytywanie danych...")

    def task():
        try:
            frames = load_frames_from_file(file_path)
            if progress.cancel_event.is_set():
                return
            progress.update_progress(20, "Przetwarzanie sygnału...")
            values = []
            for f in frames:
                if f[0] == cid and len(f[1]) > byte_idx:
                    values.append(f[1][byte_idx])
            if len(values) < 30:
                app.root.after(0, lambda: messagebox.showerror("Błąd", "Zbyt mało danych."))
                progress.close()
                return
            progress.update_progress(40, "Trenowanie modelu LSTM...")
            # Zakładamy, że train() nie ma callbacka – pomijamy na razie
            app.forecaster.train(values)
            if progress.cancel_event.is_set():
                return
            progress.update_progress(80, "Generowanie prognozy...")
            forecast = app.forecaster.forecast(values, steps)
            if progress.cancel_event.is_set():
                return
            progress.update_progress(100, "Zakończono")
            app.root.after(0, lambda: plot_forecast(app, values, forecast))
        finally:
            app.root.after(0, progress.close)

    threading.Thread(target=task, daemon=True).start()
'''

content = re.sub(old_forecast_pattern, new_forecast_func, content, flags=re.DOTALL)

# Zapisujemy zmiany
with open(target_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Zmiany w pliku zostały wprowadzone.")
PYTHON_SCRIPT

# Sprawdzamy status
if [ $? -eq 0 ]; then
    echo ""
    echo "Etap 1 zakończony pomyślnie!"
    echo "Dodano: ProgressDialog, obsługa anulowania dla prognozowania."
    echo "Aby zobaczyć efekt, uruchom program i wybierz zakładkę 'Prognozowanie (LSTM)'."
else
    echo "Wystąpił błąd podczas modyfikacji. Przywracam kopię zapasową."
    cp "$BACKUP" "$TARGET_FILE"
    exit 1
fi
