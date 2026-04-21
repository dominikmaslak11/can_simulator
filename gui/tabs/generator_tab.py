import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time

class GeneratorThread(threading.Thread):
    def __init__(self, app, log_cb):
        super().__init__(daemon=True)
        self.app = app
        self.log_cb = log_cb
        self.running = False
        self.paused = False
        self.frames = []          # lista słowników {id, data, ext, interval}
        self.loop = False

    def log(self, msg):
        if self.log_cb:
            self.log_cb(msg)

    def setup(self, frames, loop):
        self.frames = frames
        self.loop = loop

    def run(self):
        self.running = True
        self.log("[Generator] Rozpoczęto generowanie ruchu.")
        while self.running:
            if not self.paused:
                for f in self.frames:
                    if not self.running:
                        break
                    self.app.can.send_frame(f['id'], f['data'], f['ext'])
                    self.log(f"[Generator] Wysłano ID=0x{f['id']:08X} Data={f['data'].hex().upper()}")
                    time.sleep(f['interval'])
                if not self.loop:
                    break
            else:
                time.sleep(0.1)
        self.log("[Generator] Zakończono generowanie ruchu.")
        self.app.root.after(0, self._done)

    def _done(self):
        self.app.generator_start_btn.config(state='normal')
        self.app.generator_stop_btn.config(state='disabled')
        self.app.generator_pause_btn.config(state='disabled')

    def stop(self):
        self.running = False

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False


def setup_generator_tab(app, tab):
    frame = ttk.Frame(tab, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)

    # Tabela ramek
    table_frame = ttk.LabelFrame(frame, text="Sekwencja ramek do wysłania", padding=5)
    table_frame.pack(fill=tk.BOTH, expand=True)

    columns = ('id', 'data', 'ext', 'interval')
    tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=12)
    tree.heading('id', text='ID (hex)')
    tree.heading('data', text='Dane (hex)')
    tree.heading('ext', text='EXT')
    tree.heading('interval', text='Interwał [s]')

    tree.column('id', width=100)
    tree.column('data', width=200)
    tree.column('ext', width=50)
    tree.column('interval', width=100)

    vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.grid(row=0, column=0, sticky=tk.NSEW)
    vsb.grid(row=0, column=1, sticky=tk.NS)
    table_frame.grid_rowconfigure(0, weight=1)
    table_frame.grid_columnconfigure(0, weight=1)

    # Przyciski zarządzania tabelą
    btn_frame = ttk.Frame(frame)
    btn_frame.pack(pady=5)
    ttk.Button(btn_frame, text="Dodaj", command=lambda: add_generator_frame(app, tree)).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Usuń", command=lambda: delete_generator_frame(app, tree)).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Edytuj", command=lambda: edit_generator_frame(app, tree)).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Wyczyść", command=lambda: clear_generator_frames(app, tree)).pack(side=tk.LEFT, padx=2)

    # Opcje
    options_frame = ttk.Frame(frame)
    options_frame.pack(fill=tk.X, pady=5)
    loop_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(options_frame, text="Pętla (powtarzaj sekwencję)", variable=loop_var).pack(side=tk.LEFT)

    # Sterowanie
    ctrl_frame = ttk.Frame(frame)
    ctrl_frame.pack(pady=10)
    start_btn = ttk.Button(ctrl_frame, text="Start", state='disabled')
    start_btn.pack(side=tk.LEFT, padx=5)
    pause_btn = ttk.Button(ctrl_frame, text="Pauza", state='disabled')
    pause_btn.pack(side=tk.LEFT, padx=5)
    stop_btn = ttk.Button(ctrl_frame, text="Stop", state='disabled')
    stop_btn.pack(side=tk.LEFT, padx=5)

    # Status
    status_var = tk.StringVar(value="Zatrzymany")
    ttk.Label(frame, textvariable=status_var).pack(fill=tk.X, pady=(5,0))

    app.generator_tree = tree
    app.generator_loop = loop_var
    app.generator_start_btn = start_btn
    app.generator_pause_btn = pause_btn
    app.generator_stop_btn = stop_btn
    app.generator_status = status_var
    app.generator_thread = None
    app.generator_frames = []

    start_btn.config(command=lambda: start_generator(app))
    pause_btn.config(command=lambda: pause_generator(app))
    stop_btn.config(command=lambda: stop_generator(app))


def add_generator_frame(app, tree):
    dialog = tk.Toplevel(app.root)
    dialog.title("Dodaj ramkę")
    dialog.geometry("300x250")
    dialog.transient(app.root)
    dialog.grab_set()

    ttk.Label(dialog, text="ID (hex):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
    id_var = tk.StringVar()
    ttk.Entry(dialog, textvariable=id_var, width=15).grid(row=0, column=1, padx=5)

    ttk.Label(dialog, text="Dane (hex):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
    data_var = tk.StringVar()
    ttk.Entry(dialog, textvariable=data_var, width=30).grid(row=1, column=1, padx=5)

    ext_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(dialog, text="Ramka rozszerzona", variable=ext_var).grid(row=2, column=0, columnspan=2)

    ttk.Label(dialog, text="Interwał (s):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
    interval_var = tk.DoubleVar(value=1.0)
    ttk.Entry(dialog, textvariable=interval_var, width=10).grid(row=3, column=1, sticky=tk.W, padx=5)

    def save():
        try:
            cid = int(id_var.get().strip(), 16)
            data = bytes.fromhex(data_var.get().strip())
        except ValueError:
            messagebox.showerror("Błąd", "Nieprawidłowy format ID lub danych.")
            return
        is_ext = ext_var.get()
        interval = interval_var.get()
        app.generator_frames.append({'id': cid, 'data': data, 'ext': is_ext, 'interval': interval})
        tree.insert("", tk.END, values=(f"0x{cid:08X}", data.hex().upper(), "X" if is_ext else "", f"{interval:.3f}"))
        app.generator_start_btn.config(state='normal')
        dialog.destroy()

    ttk.Button(dialog, text="Zapisz", command=save).grid(row=4, column=0, columnspan=2, pady=10)


def delete_generator_frame(app, tree):
    sel = tree.selection()
    if not sel:
        messagebox.showinfo("Brak zaznaczenia", "Zaznacz ramkę do usunięcia.")
        return
    item = sel[0]
    idx = tree.index(item)
    del app.generator_frames[idx]
    tree.delete(item)
    if not app.generator_frames:
        app.generator_start_btn.config(state='disabled')


def edit_generator_frame(app, tree):
    sel = tree.selection()
    if not sel:
        messagebox.showinfo("Brak zaznaczenia", "Zaznacz ramkę do edycji.")
        return
    item = sel[0]
    idx = tree.index(item)
    values = tree.item(item, 'values')
    cid = int(values[0], 16)
    data = bytes.fromhex(values[1])
    is_ext = values[2] == "X"
    interval = float(values[3])

    dialog = tk.Toplevel(app.root)
    dialog.title("Edytuj ramkę")
    dialog.geometry("300x250")
    dialog.transient(app.root)
    dialog.grab_set()

    ttk.Label(dialog, text="ID (hex):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
    id_var = tk.StringVar(value=f"{cid:08X}")
    ttk.Entry(dialog, textvariable=id_var, width=15).grid(row=0, column=1, padx=5)

    ttk.Label(dialog, text="Dane (hex):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
    data_var = tk.StringVar(value=data.hex().upper())
    ttk.Entry(dialog, textvariable=data_var, width=30).grid(row=1, column=1, padx=5)

    ext_var = tk.BooleanVar(value=is_ext)
    ttk.Checkbutton(dialog, text="Ramka rozszerzona", variable=ext_var).grid(row=2, column=0, columnspan=2)

    ttk.Label(dialog, text="Interwał (s):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
    interval_var = tk.DoubleVar(value=interval)
    ttk.Entry(dialog, textvariable=interval_var, width=10).grid(row=3, column=1, sticky=tk.W, padx=5)

    def save():
        try:
            new_cid = int(id_var.get().strip(), 16)
            new_data = bytes.fromhex(data_var.get().strip())
        except ValueError:
            messagebox.showerror("Błąd", "Nieprawidłowy format ID lub danych.")
            return
        new_ext = ext_var.get()
        new_interval = interval_var.get()
        app.generator_frames[idx] = {'id': new_cid, 'data': new_data, 'ext': new_ext, 'interval': new_interval}
        tree.item(item, values=(f"0x{new_cid:08X}", new_data.hex().upper(), "X" if new_ext else "", f"{new_interval:.3f}"))
        dialog.destroy()

    ttk.Button(dialog, text="Zapisz", command=save).grid(row=4, column=0, columnspan=2, pady=10)


def clear_generator_frames(app, tree):
    app.generator_frames.clear()
    tree.delete(*tree.get_children())
    app.generator_start_btn.config(state='disabled')


def start_generator(app):
    if not app.generator_frames:
        return
    if not app.can.connected:
        messagebox.showerror("Błąd", "Połącz się z CAN.")
        return

    app.generator_thread = GeneratorThread(app, app.log)
    app.generator_thread.setup(app.generator_frames, app.generator_loop.get())
    app.generator_thread.start()

    app.generator_start_btn.config(state='disabled')
    app.generator_pause_btn.config(state='normal')
    app.generator_stop_btn.config(state='normal')
    app.generator_status.set("Generowanie w toku...")


def pause_generator(app):
    if app.generator_thread and app.generator_thread.is_alive():
        if app.generator_thread.paused:
            app.generator_thread.resume()
            app.generator_pause_btn.config(text="Pauza")
            app.generator_status.set("Generowanie w toku...")
        else:
            app.generator_thread.pause()
            app.generator_pause_btn.config(text="Wznów")
            app.generator_status.set("Wstrzymano")


def stop_generator(app):
    if app.generator_thread:
        app.generator_thread.stop()
    app.generator_start_btn.config(state='normal')
    app.generator_pause_btn.config(state='disabled')
    app.generator_stop_btn.config(state='disabled')
    app.generator_status.set("Zatrzymany")
