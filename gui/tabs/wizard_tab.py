import tkinter as tk
from tkinter import ttk


def setup_wizard_tab(app, tab):
    """Tworzy statyczny interfejs kreatora diagnostyki."""
    frame = ttk.Frame(tab, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)

    # Nagłówek
    ttk.Label(frame, text="Kreator diagnostyki", font=('Arial', 14, 'bold')).grid(
        row=0, column=0, columnspan=3, pady=(0, 10), sticky=tk.W)

    # Krok 1: Wczytaj plik
    ttk.Label(frame, text="Krok 1: Wczytaj plik z logiem", font=('Arial', 11, 'bold')).grid(
        row=1, column=0, columnspan=3, sticky=tk.W, pady=(5, 2))
    ttk.Button(frame, text="Przeglądaj...").grid(row=2, column=0, padx=5, pady=2, sticky=tk.W)
    file_label = ttk.Label(frame, text="Nie wczytano pliku")
    file_label.grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=5)

    # Krok 2: Wybierz alert (opcjonalnie)
    ttk.Label(frame, text="Krok 2: Wybierz alert (opcjonalnie)", font=('Arial', 11, 'bold')).grid(
        row=3, column=0, columnspan=3, sticky=tk.W, pady=(15, 2))
    ttk.Label(frame, text="Najczęstsze ID:").grid(row=4, column=0, sticky=tk.W, padx=5)
    id_listbox = tk.Listbox(frame, height=5, width=30)
    id_listbox.grid(row=4, column=1, sticky=tk.W, padx=5)
    ttk.Button(frame, text="Odśwież listę").grid(row=4, column=2, padx=5, sticky=tk.W)
    ttk.Button(frame, text="Pomiń wybór").grid(row=5, column=1, pady=5, sticky=tk.W)

    # Krok 3: Znajdź początek alertu
    ttk.Label(frame, text="Krok 3: Znajdź początek alertu", font=('Arial', 11, 'bold')).grid(
        row=6, column=0, columnspan=3, sticky=tk.W, pady=(15, 2))
    ttk.Button(frame, text="Start wyszukiwania").grid(row=7, column=0, padx=5, pady=2, sticky=tk.W)
    alert_result_label = ttk.Label(frame, text="Brak wyniku")
    alert_result_label.grid(row=7, column=1, columnspan=2, sticky=tk.W, padx=5)
    ttk.Button(frame, text="Testuj alert (10s)").grid(row=8, column=1, pady=2, sticky=tk.W)

    # Krok 4: Znajdź dezaktywator
    ttk.Label(frame, text="Krok 4: Znajdź dezaktywator", font=('Arial', 11, 'bold')).grid(
        row=9, column=0, columnspan=3, sticky=tk.W, pady=(15, 2))
    ttk.Button(frame, text="Start polowania").grid(row=10, column=0, padx=5, pady=2, sticky=tk.W)
    deact_result_label = ttk.Label(frame, text="Brak wyniku")
    deact_result_label.grid(row=10, column=1, columnspan=2, sticky=tk.W, padx=5)
    ttk.Button(frame, text="Testuj dezaktywator (10s)").grid(row=11, column=1, pady=2, sticky=tk.W)

    # Krok 5: Generuj raport
    ttk.Label(frame, text="Krok 5: Generuj raport", font=('Arial', 11, 'bold')).grid(
        row=12, column=0, columnspan=3, sticky=tk.W, pady=(15, 2))
    ttk.Button(frame, text="Generuj raport...").grid(row=13, column=0, padx=5, pady=2, sticky=tk.W)

    # Przycisk resetu kreatora
    ttk.Button(frame, text="Resetuj kreator", command=lambda: reset_wizard(app)).grid(
        row=14, column=2, pady=20, sticky=tk.E)

    # Zapis referencji do widgetów w obiekcie app
    app.wizard_file_label = file_label
    app.wizard_id_listbox = id_listbox
    app.wizard_alert_result_label = alert_result_label
    app.wizard_deact_result_label = deact_result_label


def reset_wizard(app):
    """Resetuje stan kreatora (na razie tylko czyści etykiety)."""
    app.wizard_file_label.config(text="Nie wczytano pliku")
    app.wizard_id_listbox.delete(0, tk.END)
    app.wizard_alert_result_label.config(text="Brak wyniku")
    app.wizard_deact_result_label.config(text="Brak wyniku")
    app.log("Kreator zresetowany.")
