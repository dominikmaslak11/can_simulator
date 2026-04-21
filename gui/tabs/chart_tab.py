import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


def setup_chart_tab(app, tab):
    if not MATPLOTLIB_AVAILABLE:
        ttk.Label(tab, text="Brak biblioteki matplotlib. Zainstaluj ją (pip install matplotlib).",
                  foreground="red").pack(pady=20)
        return

    frame = ttk.Frame(tab, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)

    # Panel sterowania
    control_frame = ttk.LabelFrame(frame, text="Konfiguracja wykresu", padding=5)
    control_frame.pack(fill=tk.X, pady=(0, 10))

    ttk.Label(control_frame, text="ID ramki:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
    id_var = tk.StringVar()
    id_combo = ttk.Combobox(control_frame, textvariable=id_var, state="readonly", width=20)
    id_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)

    ttk.Label(control_frame, text="Indeks bajtu (0-7):").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
    byte_var = tk.IntVar(value=0)
    byte_spin = ttk.Spinbox(control_frame, from_=0, to=7, textvariable=byte_var, width=5)
    byte_spin.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)

    refresh_btn = ttk.Button(control_frame, text="Odśwież listę ID",
                             command=lambda: refresh_id_list(app, id_combo))
    refresh_btn.grid(row=0, column=4, padx=5, pady=2)

    draw_btn = ttk.Button(control_frame, text="Rysuj wykres",
                          command=lambda: draw_chart(app, id_var.get(), byte_var.get()))
    draw_btn.grid(row=0, column=5, padx=5, pady=2)

    hist_btn = ttk.Button(control_frame, text="Histogram częstotliwości",
                          command=lambda: draw_histogram(app, id_var.get()))
    hist_btn.grid(row=0, column=6, padx=5, pady=2)

    clear_btn = ttk.Button(control_frame, text="Wyczyść wykres",
                           command=lambda: clear_chart(app))
    clear_btn.grid(row=0, column=7, padx=5, pady=2)

    highlight_btn = ttk.Button(control_frame, text="Podświetl w Snifferze",
                               command=lambda: highlight_selected_range(app))
    highlight_btn.grid(row=1, column=5, padx=5, pady=2)

    reset_highlight_btn = ttk.Button(control_frame, text="Resetuj podświetlenie",
                                     command=lambda: reset_highlight(app))
    reset_highlight_btn.grid(row=1, column=6, padx=5, pady=2)

    # Ramka na wykres
    chart_frame = ttk.Frame(frame)
    chart_frame.pack(fill=tk.BOTH, expand=True)

    fig = Figure(figsize=(8, 5), dpi=100)
    ax = fig.add_subplot(111)
    ax.set_xlabel("Czas [s]")
    ax.set_ylabel("Wartość bajtu")
    ax.grid(True, linestyle='--', alpha=0.7)

    canvas = FigureCanvasTkAgg(fig, master=chart_frame)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # Status
    status_var = tk.StringVar(value="Gotowy")
    status_label = ttk.Label(frame, textvariable=status_var)
    status_label.pack(fill=tk.X, pady=(5, 0))

    # Zmienne do przechowywania danych wykresu i selekcji
    app.chart_fig = fig
    app.chart_ax = ax
    app.chart_canvas = canvas
    app.chart_status = status_var
    app.chart_id_combo = id_combo
    app.chart_byte_var = byte_var
    app.chart_data = {"timestamps": [], "values": [], "items": [], "id_str": "", "byte_index": 0}
    app.chart_span = None  # obiekt prostokąta zaznaczenia

    # Inicjalizacja listy ID
    refresh_id_list(app, id_combo)

    # Połączenie zdarzeń myszy
    fig.canvas.mpl_connect('button_press_event', lambda event: on_mouse_press(app, event))
    fig.canvas.mpl_connect('button_release_event', lambda event: on_mouse_release(app, event))
    fig.canvas.mpl_connect('motion_notify_event', lambda event: on_mouse_move(app, event))

    app.chart_pressed = False
    app.chart_start_x = None


def refresh_id_list(app, combo):
    if not hasattr(app, 'sniffer_tree'):
        messagebox.showerror("Błąd", "Najpierw uruchom Sniffera, aby zebrać dane.")
        return
    tree = app.sniffer_tree
    ids = set()
    for item in tree.get_children():
        values = tree.item(item, 'values')
        if len(values) >= 2:
            ids.add(values[1])
    id_list = sorted(list(ids))
    combo['values'] = id_list
    if id_list:
        combo.current(0)
    app.chart_status.set(f"Dostępne ID: {len(id_list)}")


def draw_chart(app, id_str, byte_index):
    if not id_str:
        messagebox.showerror("Błąd", "Wybierz ID ramki.")
        return
    tree = app.sniffer_tree
    timestamps = []
    values = []
    items = []
    for item in tree.get_children():
        vals = tree.item(item, 'values')
        if len(vals) >= 5 and vals[1] == id_str:
            try:
                ts = datetime.strptime(vals[0], "%H:%M:%S.%f").timestamp()
            except:
                continue
            data_hex = vals[4]
            if ' ' in data_hex:
                data_hex = app.sniffer_ctrl._bits_to_hex(data_hex)
            try:
                data_bytes = bytes.fromhex(data_hex)
                if byte_index < len(data_bytes):
                    val = data_bytes[byte_index]
                    timestamps.append(ts)
                    values.append(val)
                    items.append(item)
            except:
                continue

    if not timestamps:
        app.chart_status.set("Brak danych dla wybranego ID/bajtu.")
        return

    t0 = timestamps[0]
    rel_times = [t - t0 for t in timestamps]

    app.chart_data = {
        "timestamps": rel_times,
        "values": values,
        "items": items,
        "id_str": id_str,
        "byte_index": byte_index
    }

    ax = app.chart_ax
    ax.clear()
    ax.plot(rel_times, values, 'b-', linewidth=1, marker='.', markersize=2)
    ax.set_xlabel("Czas [s]")
    ax.set_ylabel(f"Wartość bajtu {byte_index}")
    ax.set_title(f"ID: {id_str} – bajt {byte_index}")
    ax.grid(True, linestyle='--', alpha=0.7)
    app.chart_canvas.draw()
    app.chart_status.set(f"Wykres dla ID {id_str}, bajt {byte_index} – {len(timestamps)} punktów.")
    app.chart_span = None


def draw_histogram(app, id_str):
    if not id_str:
        messagebox.showerror("Błąd", "Wybierz ID ramki.")
        return
    tree = app.sniffer_tree
    timestamps = []
    for item in tree.get_children():
        vals = tree.item(item, 'values')
        if len(vals) >= 2 and vals[1] == id_str:
            try:
                ts = datetime.strptime(vals[0], "%H:%M:%S.%f").timestamp()
                timestamps.append(ts)
            except:
                continue

    if len(timestamps) < 2:
        app.chart_status.set("Za mało ramek do obliczenia interwałów.")
        return

    diffs = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]

    ax = app.chart_ax
    ax.clear()
    ax.hist(diffs, bins=30, edgecolor='black', alpha=0.7)
    ax.set_xlabel("Odstęp czasu [s]")
    ax.set_ylabel("Liczba wystąpień")
    ax.set_title(f"Histogram odstępów – ID: {id_str}")
    ax.grid(True, linestyle='--', alpha=0.7)
    app.chart_canvas.draw()
    app.chart_status.set(f"Histogram dla ID {id_str} – średni odstęp: {sum(diffs)/len(diffs):.4f}s.")
    app.chart_span = None


def clear_chart(app):
    app.chart_ax.clear()
    app.chart_ax.set_xlabel("Czas [s]")
    app.chart_ax.set_ylabel("Wartość")
    app.chart_ax.grid(True, linestyle='--', alpha=0.7)
    app.chart_canvas.draw()
    app.chart_status.set("Wykres wyczyszczony.")
    app.chart_span = None
    app.chart_data = {"timestamps": [], "values": [], "items": [], "id_str": "", "byte_index": 0}


# ---------- Interaktywne zaznaczanie ----------
def on_mouse_press(app, event):
    if event.inaxes != app.chart_ax:
        return
    app.chart_pressed = True
    app.chart_start_x = event.xdata


def on_mouse_move(app, event):
    if not app.chart_pressed or event.inaxes != app.chart_ax:
        return
    if app.chart_start_x is None or event.xdata is None:
        return
    # Usuń poprzedni prostokąt
    if app.chart_span:
        app.chart_span.remove()
        app.chart_span = None
    # Rysuj nowy
    xmin = min(app.chart_start_x, event.xdata)
    xmax = max(app.chart_start_x, event.xdata)
    app.chart_span = app.chart_ax.axvspan(xmin, xmax, alpha=0.3, color='yellow')
    app.chart_canvas.draw_idle()


def on_mouse_release(app, event):
    if not app.chart_pressed:
        return
    app.chart_pressed = False
    if app.chart_start_x is None or event is None or event.xdata is None:
        return
    x1, x2 = app.chart_start_x, event.xdata
    if abs(x1 - x2) < 0.001:  # kliknięcie, nie zaznaczenie
        return
    xmin, xmax = min(x1, x2), max(x1, x2)
    app.chart_status.set(f"Zaznaczono zakres: {xmin:.3f}s – {xmax:.3f}s")


def highlight_selected_range(app):
    if app.chart_span is None:
        messagebox.showinfo("Brak zaznaczenia", "Najpierw zaznacz zakres na wykresie (przytrzymaj lewy przycisk myszy).")
        return
    # Pobierz granice z prostokąta
    bbox = app.chart_span.get_bbox()
    xmin, xmax = bbox.xmin, bbox.xmax

    data = app.chart_data
    if not data["items"]:
        return

    tree = app.sniffer_tree
    # Resetuj poprzednie podświetlenia
    for item in tree.get_children():
        tree.item(item, tags=())
    tree.tag_configure('highlighted', background='yellow')

    # Znajdź punkty w zakresie
    count = 0
    for i, (t, item) in enumerate(zip(data["timestamps"], data["items"])):
        if xmin <= t <= xmax:
            tree.item(item, tags=('highlighted',))
            count += 1

    # Przewiń tabelę do pierwszego podświetlonego wiersza
    if count > 0:
        for item in tree.get_children():
            if 'highlighted' in tree.item(item, 'tags'):
                tree.see(item)
                break

    app.chart_status.set(f"Podświetlono {count} ramek w zakresie {xmin:.3f}s – {xmax:.3f}s.")


def reset_highlight(app):
    tree = app.sniffer_tree
    for item in tree.get_children():
        tree.item(item, tags=())
    app.chart_status.set("Podświetlenie wyczyszczone.")
