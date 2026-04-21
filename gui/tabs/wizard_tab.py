import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import threading
import time
from parsers import load_frames_from_file


def setup_wizard_tab(app, tab):
    frame = ttk.Frame(tab, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)

    # Wybór pliku
    ttk.Label(frame, text="Plik candump/log:").grid(row=0, column=0, sticky=tk.W)
    file_var = tk.StringVar()
    ttk.Entry(frame, textvariable=file_var, width=50).grid(row=0, column=1, padx=5)
    ttk.Button(frame, text="Przeglądaj",
               command=lambda: browse_wizard_file(file_var)).grid(row=0, column=2)
    ttk.Button(frame, text="Wczytaj plik",
               command=lambda: load_wizard_file(app, file_var, info_label, start_btn)).grid(row=0, column=3, padx=5)

    info_label = ttk.Label(frame, text="Nie wczytano pliku")
    info_label.grid(row=1, column=0, columnspan=4, pady=5)

    # Ramka docelowa
    ttk.Label(frame, text="Szukana ramka:").grid(row=2, column=0, sticky=tk.W, pady=5)
    search_frame = ttk.LabelFrame(frame, text="Definicja ramki", padding=5)
    search_frame.grid(row=3, column=0, columnspan=4, sticky='ew', pady=5)

    ttk.Label(search_frame, text="ID (hex):").grid(row=0, column=0, sticky=tk.W)
    id_var = tk.StringVar(value="0C00008F")
    ttk.Entry(search_frame, textvariable=id_var, width=15).grid(row=0, column=1, padx=5)

    ttk.Label(search_frame, text="Dane (hex):").grid(row=1, column=0, sticky=tk.W)
    data_var = tk.StringVar(value="")
    ttk.Entry(search_frame, textvariable=data_var, width=30).grid(row=1, column=1, padx=5)

    extended_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(search_frame, text="Ramka rozszerzona (29-bit)",
                    variable=extended_var).grid(row=2, column=0, columnspan=2, pady=5)

    # Tryb wyszukiwania
    ttk.Label(frame, text="Tryb wyszukiwania:").grid(row=4, column=0, sticky=tk.W)
    mode_var = tk.StringVar(value="single")
    mode_frame = ttk.Frame(frame)
    mode_frame.grid(row=4, column=1, columnspan=3, sticky=tk.W)
    ttk.Radiobutton(mode_frame, text="Pojedyncza ramka", variable=mode_var, value="single").pack(side=tk.LEFT, padx=5)
    ttk.Radiobutton(mode_frame, text="Sekwencja ramek", variable=mode_var, value="sequence").pack(side=tk.LEFT, padx=5)

    # Interwał
    ttk.Label(frame, text="Interwał odtwarzania (s):").grid(row=5, column=0, sticky=tk.W)
    interval_var = tk.DoubleVar(value=0.1)
    ttk.Spinbox(frame, from_=0.001, to=1.0, increment=0.01, textvariable=interval_var, width=10).grid(
        row=5, column=1, sticky=tk.W)

    # Przyciski sterujące
    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=6, column=0, columnspan=4, pady=10)

    start_btn = ttk.Button(btn_frame, text="Rozpocznij wyszukiwanie", state='disabled')
    start_btn.pack(side=tk.LEFT, padx=5)
    stop_btn = ttk.Button(btn_frame, text="Stop", state='disabled')
    stop_btn.pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Reset", command=lambda: reset_wizard(app)).pack(side=tk.LEFT, padx=5)

    # Postęp
    progress_label = ttk.Label(frame, text="Postęp: --")
    progress_label.grid(row=7, column=0, columnspan=4, pady=5)

    # Przypisanie atrybutów do app
    app.wizard_file_var = file_var
    app.wizard_info = info_label
    app.wizard_id_frame = id_var
    app.wizard_data_frame = data_var
    app.wizard_is_extended = extended_var
    app.wizard_search_mode = mode_var
    app.wizard_interval = interval_var
    app.wizard_start_btn = start_btn
    app.wizard_stop_btn = stop_btn
    app.wizard_progress = progress_label

    start_btn.config(command=lambda: start_wizard_search(app))
    stop_btn.config(command=lambda: stop_wizard_search(app))


def browse_wizard_file(file_var):
    path = filedialog.askopenfilename(filetypes=[("Logi/pliki tekstowe", "*.txt *.log"), ("Wszystkie", "*.*")])
    if path:
        file_var.set(path)


def load_wizard_file(app, file_var, info_label, start_btn):
    path = file_var.get()
    if not path:
        messagebox.showerror("Błąd", "Wybierz plik")
        return
    try:
        app.wizard_frames = load_frames_from_file(path)
        info_label.config(text=f"Wczytano {len(app.wizard_frames)} ramek")
        app.log(f"[Kreator] Wczytano {len(app.wizard_frames)} ramek z {path}")
        start_btn.config(state='normal')
    except Exception as e:
        messagebox.showerror("Błąd", f"Nie udało się wczytać pliku: {e}")


def reset_wizard(app):
    if hasattr(app, 'wizard_thread') and app.wizard_thread:
        app.wizard_thread.stop()
    app.wizard_start_btn.config(state='normal')
    app.wizard_stop_btn.config(state='disabled')
    app.wizard_progress.config(text="Postęp: --")


def start_wizard_search(app):
    # Placeholder – tutaj można zaimplementować właściwe wyszukiwanie kreatorem
    app.log("[Kreator] Rozpoczęto wyszukiwanie (funkcja w trakcie implementacji)")
    # Na razie tylko wyświetlamy komunikat
    messagebox.showinfo("Kreator", "Funkcja wyszukiwania kreatorem zostanie zaimplementowana wkrótce.")


def stop_wizard_search(app):
    if hasattr(app, 'wizard_thread') and app.wizard_thread:
        app.wizard_thread.stop()
    app.wizard_start_btn.config(state='normal')
    app.wizard_stop_btn.config(state='disabled')
    app.log("[Kreator] Zatrzymano wyszukiwanie.")
