import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import threading
import time
from parsers import load_frames_from_file


def setup_wizard_tab(app, tab):
    frame = ttk.Frame(tab, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame, text="Plik candump/log:").grid(row=0, column=0, sticky=tk.W)
    file_var = tk.StringVar()
    ttk.Entry(frame, textvariable=file_var, width=50).grid(row=0, column=1, padx=5)
    ttk.Button(frame, text="Przeglądaj", command=lambda: browse_wizard_file(file_var)).grid(row=0, column=2)
    ttk.Button(frame, text="Wczytaj plik", command=lambda: load_wizard_file(app, file_var, info_label, start_btn)).grid(row=0, column=3, padx=5)

    info_label = ttk.Label(frame, text="Nie wczytano pliku")
    info_label.grid(row=1, column=0, columnspan=4, pady=5)

    ttk.Label(frame, text="Szukana ramka/sekwencja:").grid(row=2, column=0, sticky=tk.W, pady=5)
    search_frame = ttk.LabelFrame(frame, text="Definicja", padding=5)
    search_frame.grid(row=3, column=0, columnspan=4, sticky='ew', pady=5)

    ttk.Label(search_frame, text="Tryb:").grid(row=0, column=0, sticky=tk.W)
    mode_var = tk.StringVar(value="single")
    mode_frame = ttk.Frame(search_frame)
    mode_frame.grid(row=0, column=1, columnspan=3, sticky=tk.W)
    ttk.Radiobutton(mode_frame, text="Pojedyncza ramka", variable=mode_var, value="single").pack(side=tk.LEFT, padx=5)
    ttk.Radiobutton(mode_frame, text="Sekwencja ramek", variable=mode_var, value="sequence").pack(side=tk.LEFT, padx=5)

    single_frame = ttk.Frame(search_frame)
    single_frame.grid(row=1, column=0, columnspan=4, sticky='ew', pady=5)

    ttk.Label(single_frame, text="ID (hex):").grid(row=0, column=0, sticky=tk.W)
    id_var = tk.StringVar(value="0C00008F")
    ttk.Entry(single_frame, textvariable=id_var, width=15).grid(row=0, column=1, padx=5)

    ttk.Label(single_frame, text="Dane (hex, opcjonalnie):").grid(row=1, column=0, sticky=tk.W)
    data_var = tk.StringVar(value="")
    ttk.Entry(single_frame, textvariable=data_var, width=30).grid(row=1, column=1, padx=5)

    extended_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(single_frame, text="Ramka rozszerzona (29-bit)", variable=extended_var).grid(row=2, column=0, columnspan=2, pady=5)

    seq_frame = ttk.Frame(search_frame)
    seq_frame.grid(row=1, column=0, columnspan=4, sticky='ew', pady=5)

    seq_listbox = tk.Listbox(seq_frame, height=4)
    seq_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    seq_scroll = ttk.Scrollbar(seq_frame, orient=tk.VERTICAL, command=seq_listbox.yview)
    seq_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    seq_listbox.config(yscrollcommand=seq_scroll.set)

    seq_btn_frame = ttk.Frame(search_frame)
    seq_btn_frame.grid(row=2, column=0, columnspan=4, pady=5)
    ttk.Button(seq_btn_frame, text="Dodaj ramkę", command=lambda: add_sequence_frame(app)).pack(side=tk.LEFT, padx=5)
    ttk.Button(seq_btn_frame, text="Usuń zaznaczoną", command=lambda: remove_sequence_frame(app)).pack(side=tk.LEFT, padx=5)

    def toggle_mode(*args):
        if mode_var.get() == "single":
            single_frame.grid()
            seq_frame.grid_remove()
            seq_btn_frame.grid_remove()
        else:
            single_frame.grid_remove()
            seq_frame.grid()
            seq_btn_frame.grid()

    mode_var.trace('w', toggle_mode)
    toggle_mode()

    ttk.Label(frame, text="Liczba części do podziału:").grid(row=4, column=0, sticky=tk.W)
    parts_var = tk.IntVar(value=2)
    ttk.Spinbox(frame, from_=2, to=20, textvariable=parts_var, width=5).grid(row=4, column=1, sticky=tk.W)

    ttk.Label(frame, text="Interwał odtwarzania (s):").grid(row=5, column=0, sticky=tk.W)
    interval_var = tk.DoubleVar(value=0.1)
    ttk.Spinbox(frame, from_=0.001, to=1.0, increment=0.01, textvariable=interval_var, width=10).grid(
        row=5, column=1, sticky=tk.W)

    timestamps_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(frame, text="Użyj oryginalnych odstępów czasowych (z logu)",
                    variable=timestamps_var).grid(row=5, column=2, columnspan=2, sticky=tk.W)

    canvas_frame = ttk.Frame(frame)
    canvas_frame.grid(row=6, column=0, columnspan=4, pady=5, sticky='ew')
    canvas = tk.Canvas(canvas_frame, height=30, bg='white', relief='sunken', borderwidth=1)
    canvas.pack(fill=tk.X, padx=5)

    progress_label = ttk.Label(frame, text="Postęp: --")
    progress_label.grid(row=7, column=0, columnspan=4, pady=5)

    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=8, column=0, columnspan=4, pady=10)

    start_btn = ttk.Button(btn_frame, text="Rozpocznij wyszukiwanie", state='disabled')
    start_btn.pack(side=tk.LEFT, padx=5)
    yes_btn = ttk.Button(btn_frame, text="Tak (wystąpiło)", state='disabled')
    yes_btn.pack(side=tk.LEFT, padx=5)
    no_btn = ttk.Button(btn_frame, text="Nie (brak)", state='disabled')
    no_btn.pack(side=tk.LEFT, padx=5)
    stop_btn = ttk.Button(btn_frame, text="Stop", state='disabled')
    stop_btn.pack(side=tk.LEFT, padx=5)
    undo_btn = ttk.Button(btn_frame, text="Cofnij", state='disabled', command=lambda: undo_wizard_step(app))
    undo_btn.pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Reset", command=lambda: reset_wizard(app)).pack(side=tk.LEFT, padx=5)

    app.wizard_file_var = file_var
    app.wizard_info = info_label
    app.wizard_id_var = id_var
    app.wizard_data_var = data_var
    app.wizard_extended_var = extended_var
    app.wizard_mode_var = mode_var
    app.wizard_seq_listbox = seq_listbox
    app.wizard_parts_var = parts_var
    app.wizard_interval = interval_var
    app.wizard_use_timestamps = timestamps_var
    app.wizard_canvas = canvas
    app.wizard_progress = progress_label
    app.wizard_start_btn = start_btn
    app.wizard_yes_btn = yes_btn
    app.wizard_no_btn = no_btn
    app.wizard_stop_btn = stop_btn
    app.wizard_undo_btn = undo_btn

    start_btn.config(command=lambda: start_wizard_search(app))
    yes_btn.config(command=lambda: wizard_answer_yes(app))
    no_btn.config(command=lambda: wizard_answer_no(app))
    stop_btn.config(command=lambda: stop_wizard_search(app))

    app.wizard_frames = []
    app.wizard_sequence = []
    app.wizard_thread = None
    app.wizard_answer_event = threading.Event()
    app.wizard_answer = None
    app.wizard_history = []
    app.wizard_left = 0
    app.wizard_right = 0


def browse_wizard_file(file_var):
    path = filedialog.askopenfilename(filetypes=[("Logi", "*.txt *.log"), ("Wszystkie", "*.*")])
    if path: file_var.set(path)


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
        app.wizard_left = 0
        app.wizard_right = len(app.wizard_frames) - 1
        app._redraw_wizard_progress()
    except Exception as e:
        messagebox.showerror("Błąd", f"Nie udało się wczytać pliku: {e}")


def add_sequence_frame(app):
    dialog = tk.Toplevel(app.root)
    dialog.title("Dodaj ramkę do sekwencji")
    dialog.geometry("300x200")
    dialog.transient(app.root)
    dialog.grab_set()

    ttk.Label(dialog, text="ID (hex):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
    id_var = tk.StringVar()
    ttk.Entry(dialog, textvariable=id_var, width=15).grid(row=0, column=1, padx=5)

    ttk.Label(dialog, text="Dane (hex, opcjonalnie):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
    data_var = tk.StringVar()
    ttk.Entry(dialog, textvariable=data_var, width=30).grid(row=1, column=1, padx=5)

    ext_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(dialog, text="Ramka rozszerzona", variable=ext_var).grid(row=2, column=0, columnspan=2, pady=5)

    def save():
        try:
            cid = int(id_var.get().strip(), 16)
            data_str = data_var.get().strip()
            data = bytes.fromhex(data_str) if data_str else b''
            is_ext = ext_var.get()
            app.wizard_sequence.append((cid, data, is_ext))
            app.wizard_seq_listbox.insert(tk.END, f"ID=0x{cid:08X} Data={data.hex().upper() if data else '-'} EXT={is_ext}")
            dialog.destroy()
        except ValueError:
            messagebox.showerror("Błąd", "Nieprawidłowy format ID lub danych")

    ttk.Button(dialog, text="Dodaj", command=save).grid(row=3, column=0, columnspan=2, pady=10)


def remove_sequence_frame(app):
    selection = app.wizard_seq_listbox.curselection()
    if selection:
        index = selection[0]
        app.wizard_seq_listbox.delete(index)
        del app.wizard_sequence[index]


def reset_wizard(app):
    if app.wizard_thread and app.wizard_thread.is_alive():
        app.wizard_thread.stop()
    app.wizard_start_btn.config(state='normal')
    app.wizard_yes_btn.config(state='disabled')
    app.wizard_no_btn.config(state='disabled')
    app.wizard_stop_btn.config(state='disabled')
    app.wizard_undo_btn.config(state='disabled')
    app.wizard_progress.config(text="Postęp: --")
    app.wizard_left = 0
    app.wizard_right = len(app.wizard_frames) - 1 if app.wizard_frames else 0
    app.wizard_history.clear()
    app._redraw_wizard_progress()
    app.log("[Kreator] Reset.")


def start_wizard_search(app):
    if not app.wizard_frames:
        messagebox.showerror("Błąd", "Najpierw wczytaj plik")
        return
    if not app.can.connected:
        messagebox.showerror("Błąd", "Połącz się z CAN")
        return

    mode = app.wizard_mode_var.get()
    if mode == "single":
        try:
            target_id = int(app.wizard_id_var.get().strip(), 16)
            data_str = app.wizard_data_var.get().strip()
            target_data = bytes.fromhex(data_str) if data_str else None
            target_is_ext = app.wizard_extended_var.get()
            target = (target_id, target_data, target_is_ext)
        except ValueError:
            messagebox.showerror("Błąd", "Nieprawidłowy format ID lub danych")
            return
    else:
        if not app.wizard_sequence:
            messagebox.showerror("Błąd", "Dodaj co najmniej jedną ramkę do sekwencji")
            return
        target = list(app.wizard_sequence)

    app.wizard_target = target
    app.wizard_left = 0
    app.wizard_right = len(app.wizard_frames) - 1
    app.wizard_history.clear()

    app.wizard_start_btn.config(state='disabled')
    app.wizard_yes_btn.config(state='normal')
    app.wizard_no_btn.config(state='normal')
    app.wizard_stop_btn.config(state='normal')
    app.wizard_undo_btn.config(state='normal')

    app.wizard_thread = WizardSearchThread(app, app.log)
    app.wizard_thread.setup(app.wizard_frames, app.wizard_interval.get(),
                            target, app.wizard_parts_var.get(),
                            app.wizard_use_timestamps.get())
    app.wizard_thread.start()
    app._update_wizard_progress()


class WizardSearchThread(threading.Thread):
    def __init__(self, app, log_cb):
        super().__init__(daemon=True)
        self.app = app
        self.log_cb = log_cb
        self.running = False
        self.frames = []
        self.interval = 0.5
        self.use_timestamps = False
        self.target = None
        self.num_parts = 2
        self.left = 0
        self.right = 0

    def log(self, msg):
        self.log_cb(msg)

    def setup(self, frames, interval, target, num_parts=2, use_timestamps=False):
        self.frames = frames
        self.interval = interval
        self.target = target
        self.num_parts = num_parts
        self.use_timestamps = use_timestamps
        self.left = 0
        self.right = len(frames) - 1
        self.running = True

    def run(self):
        while self.running and self.left <= self.right:
            total = self.right - self.left + 1
            part_size = max(1, total // self.num_parts)
            parts = []
            for i in range(self.num_parts):
                s = self.left + i * part_size
                e = self.right if i == self.num_parts - 1 else s + part_size - 1
                parts.append((s, e))

            found_part = None
            for idx, (s, e) in enumerate(parts):
                if not self.running:
                    return
                self.log(f"[Kreator] Odtwarzanie części {idx+1}/{len(parts)}: [{s} .. {e}]")
                self._play_range(s, e)
                if not self.running:
                    return

                self.app.wizard_answer_event.clear()
                self.app.wizard_answer_event.wait()
                answer = self.app.wizard_answer
                if answer is None:
                    self.log("[Kreator] Anulowano")
                    return

                if answer:
                    found_part = (s, e)
                    break

            if found_part is None:
                self.log("[Kreator] Nie znaleziono szukanej ramki/sekwencji w żadnej części.")
                break

            self.left, self.right = found_part
            self.app.wizard_history.append((self.left, self.right))
            self.app._update_wizard_progress()
            self.log(f"[Kreator] Zawężono zakres do [{self.left} .. {self.right}]")

            if self.left == self.right:
                if self._matches(self.frames[self.left]):
                    self.log(f"[Kreator] Znaleziono szukaną ramkę na indeksie {self.left}")
                else:
                    self.log(f"[Kreator] Nie znaleziono dokładnego dopasowania. Zatrzymano na indeksie {self.left}")
                break

            self.app.wizard_answer_event.clear()
            change = self._ask("Czy chcesz zmienić liczbę części dla następnego kroku?", input_type='yesno')
            if change:
                new_parts = self._ask("Podaj nową liczbę części:", input_type='integer', default=self.num_parts)
                if new_parts and new_parts > 0:
                    self.num_parts = new_parts

        self.running = False
        self.app.root.after(0, self._done)
        self.log("[Kreator] Wyszukiwanie zakończone.")

    def _play_range(self, start, end):
        last_ts = None
        for i in range(start, end + 1):
            if not self.running:
                break
            cid, data, is_ext, ts = self.frames[i]
            if self.use_timestamps and ts is not None:
                if last_ts is not None and ts > last_ts:
                    time.sleep(ts - last_ts)
                last_ts = ts
            else:
                time.sleep(self.interval)
            self.app.can.send_frame(cid, data, is_ext)

    def _matches(self, frame):
        if isinstance(self.target, tuple):
            tid, tdata, tis_ext = self.target
            cid, data, is_ext, _ = frame
            if cid != tid or is_ext != tis_ext:
                return False
            if tdata is not None and data != tdata:
                return False
            return True
        else:
            seq = self.target
            idx = self.frames.index(frame)
            if idx + len(seq) > len(self.frames):
                return False
            for i, (sid, sdata, sis_ext) in enumerate(seq):
                cid, data, is_ext, _ = self.frames[idx + i]
                if cid != sid or is_ext != sis_ext:
                    return False
                if sdata and data != sdata:
                    return False
            return True

    def _ask(self, prompt, input_type='yesno', default=None):
        if input_type == 'yesno':
            return messagebox.askyesno("Pytanie", prompt)
        elif input_type == 'integer':
            return simpledialog.askinteger("Liczba", prompt, initialvalue=default)
        return None

    def _done(self):
        self.app.wizard_start_btn.config(state='normal')
        self.app.wizard_yes_btn.config(state='disabled')
        self.app.wizard_no_btn.config(state='disabled')
        self.app.wizard_stop_btn.config(state='disabled')
        self.app.wizard_undo_btn.config(state='disabled')

    def stop(self):
        self.running = False
        self.app.wizard_answer_event.set()


def wizard_answer_yes(app):
    if app.wizard_thread and app.wizard_thread.is_alive():
        app.wizard_answer = True
        app.wizard_answer_event.set()
        app.log("[Kreator] Odpowiedź: TAK")
        app._update_wizard_progress()


def wizard_answer_no(app):
    if app.wizard_thread and app.wizard_thread.is_alive():
        app.wizard_answer = False
        app.wizard_answer_event.set()
        app.log("[Kreator] Odpowiedź: NIE")
        app._update_wizard_progress()


def stop_wizard_search(app):
    if app.wizard_thread:
        app.wizard_thread.stop()
    app.wizard_start_btn.config(state='normal')
    app.wizard_yes_btn.config(state='disabled')
    app.wizard_no_btn.config(state='disabled')
    app.wizard_stop_btn.config(state='disabled')
    app.wizard_undo_btn.config(state='disabled')
    app.log("[Kreator] Zatrzymano.")


def undo_wizard_step(app):
    if app.wizard_history:
        app.wizard_history.pop()
        if app.wizard_history:
            app.wizard_left, app.wizard_right = app.wizard_history[-1]
        else:
            app.wizard_left, app.wizard_right = 0, len(app.wizard_frames) - 1
        app._update_wizard_progress()
        app.log(f"[Kreator] Cofnięto do zakresu [{app.wizard_left} .. {app.wizard_right}]")
    else:
        messagebox.showinfo("Cofnij", "Brak wcześniejszego stanu.")


def _update_wizard_progress(app):
    if app.wizard_frames:
        total = len(app.wizard_frames)
        app.wizard_progress.config(text=f"Zakres: [{app.wizard_left} .. {app.wizard_right}] (razem: {total})")
        app._redraw_wizard_progress()


def _redraw_wizard_progress(app):
    canvas = app.wizard_canvas
    canvas.delete("all")
    total = len(app.wizard_frames)
    if total == 0:
        return
    width = canvas.winfo_width()
    if width <= 10:
        width = 600

    left, right = app.wizard_left, app.wizard_right

    def idx_to_x(idx):
        return int((idx / (total - 1)) * width) if total > 1 else 0

    x_left = idx_to_x(left)
    x_right = idx_to_x(right)
    mid = (left + right) // 2
    x_mid = idx_to_x(mid)

    canvas.create_rectangle(0, 0, width, 30, fill='lightgray', outline='')
    canvas.create_rectangle(x_left, 0, x_right, 30, fill='lightblue', outline='darkblue')
    canvas.create_line(x_mid, 0, x_mid, 30, fill='red', width=2)
    canvas.create_text(x_left, 15, text=str(left), anchor='e', font=('Arial', 8))
    canvas.create_text(x_right, 15, text=str(right), anchor='w', font=('Arial', 8))
    canvas.create_text(x_mid, 0, text=str(mid), anchor='s', font=('Arial', 8, 'bold'), fill='red')
