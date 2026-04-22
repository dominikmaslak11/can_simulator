import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from macro_recorder import MacroRecorder

def setup_macro_tab(app, tab):
    frame = ttk.Frame(tab, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)

    # Inicjalizacja rejestratora
    app.macro_recorder = MacroRecorder(app)

    # Panel nagrywania
    rec_frame = ttk.LabelFrame(frame, text="Nagrywanie", padding=5)
    rec_frame.pack(fill=tk.X, pady=5)

    rec_btn = ttk.Button(rec_frame, text="Rozpocznij nagrywanie", command=lambda: start_recording(app))
    rec_btn.pack(side=tk.LEFT, padx=5)
    stop_rec_btn = ttk.Button(rec_frame, text="Zakończ nagrywanie", state='disabled', command=lambda: stop_recording(app))
    stop_rec_btn.pack(side=tk.LEFT, padx=5)
    save_btn = ttk.Button(rec_frame, text="Zapisz makro", state='disabled', command=lambda: save_macro(app))
    save_btn.pack(side=tk.LEFT, padx=5)
    load_btn = ttk.Button(rec_frame, text="Wczytaj makro", command=lambda: load_macro(app))
    load_btn.pack(side=tk.LEFT, padx=5)

    # Panel odtwarzania
    play_frame = ttk.LabelFrame(frame, text="Odtwarzanie", padding=5)
    play_frame.pack(fill=tk.X, pady=5)

    loop_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(play_frame, text="Pętla", variable=loop_var).pack(side=tk.LEFT, padx=5)
    play_btn = ttk.Button(play_frame, text="Odtwórz", state='disabled', command=lambda: play_macro(app))
    play_btn.pack(side=tk.LEFT, padx=5)
    stop_play_btn = ttk.Button(play_frame, text="Zatrzymaj", state='disabled', command=lambda: stop_playback(app))
    stop_play_btn.pack(side=tk.LEFT, padx=5)

    # Lista zdarzeń (podgląd)
    list_frame = ttk.LabelFrame(frame, text="Zarejestrowane zdarzenia", padding=5)
    list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

    events_list = tk.Listbox(list_frame, height=10)
    events_list.pack(fill=tk.BOTH, expand=True)

    # Status
    status_var = tk.StringVar(value="Gotowy")
    ttk.Label(frame, textvariable=status_var).pack(fill=tk.X)

    # Przechowaj referencje
    app.macro_rec_btn = rec_btn
    app.macro_stop_rec_btn = stop_rec_btn
    app.macro_save_btn = save_btn
    app.macro_play_btn = play_btn
    app.macro_stop_play_btn = stop_play_btn
    app.macro_loop = loop_var
    app.macro_events_list = events_list
    app.macro_status = status_var


def start_recording(app):
    app.macro_recorder.start_recording()
    app.macro_rec_btn.config(state='disabled')
    app.macro_stop_rec_btn.config(state='normal')
    app.macro_save_btn.config(state='disabled')
    app.macro_play_btn.config(state='disabled')
    app.macro_status.set("Nagrywanie...")
    app.macro_events_list.delete(0, tk.END)


def stop_recording(app):
    app.macro_recorder.stop_recording()
    app.macro_rec_btn.config(state='normal')
    app.macro_stop_rec_btn.config(state='disabled')
    app.macro_save_btn.config(state='normal')
    app.macro_play_btn.config(state='normal')
    app.macro_status.set(f"Zarejestrowano {len(app.macro_recorder.events)} zdarzeń.")
    # Wypełnij listę
    app.macro_events_list.delete(0, tk.END)
    for ev in app.macro_recorder.events:
        app.macro_events_list.insert(tk.END, f"{ev['time']:.3f}s: {ev['type']} {ev['args']}")


def save_macro(app):
    filepath = filedialog.asksaveasfilename(defaultextension=".macro", filetypes=[("Pliki makr", "*.macro")])
    if not filepath:
        return
    app.macro_recorder.save(filepath)


def load_macro(app):
    filepath = filedialog.askopenfilename(filetypes=[("Pliki makr", "*.macro")])
    if not filepath:
        return
    app.macro_recorder.load(filepath)
    app.macro_play_btn.config(state='normal')
    app.macro_status.set(f"Wczytano {len(app.macro_recorder.events)} zdarzeń.")
    app.macro_events_list.delete(0, tk.END)
    for ev in app.macro_recorder.events:
        app.macro_events_list.insert(tk.END, f"{ev['time']:.3f}s: {ev['type']} {ev['args']}")


def play_macro(app):
    app.macro_recorder.play(loop=app.macro_loop.get())
    app.macro_play_btn.config(state='disabled')
    app.macro_stop_play_btn.config(state='normal')
    app.macro_status.set("Odtwarzanie...")


def stop_playback(app):
    app.macro_recorder.stop_playback()
    app.macro_play_btn.config(state='normal')
    app.macro_stop_play_btn.config(state='disabled')
    app.macro_status.set("Zatrzymano odtwarzanie.")
