from .base_controller import BaseController
from tkinter import filedialog, messagebox
from parsers import load_frames_from_file
from threads import WizardSearchThread
from session_manager import SessionManager
import threading


class WizardController(BaseController):
    def __init__(self, app):
        super().__init__(app)
        self.app.wizard_frames = []
        self.app.wizard_sequence = []
        self.app.wizard_thread = None
        self.app.wizard_answer_event = threading.Event()
        self.app.wizard_answer = None
        self.app.wizard_history = []
        self.app.wizard_left = 0
        self.app.wizard_right = 0

    def load_file(self, file_var, info_label, start_btn):
        path = file_var.get()
        if not path:
            messagebox.showerror("Błąd", "Wybierz plik")
            return
        try:
            self.app.wizard_frames = load_frames_from_file(path)
            info_label.config(text=f"Wczytano {len(self.app.wizard_frames)} ramek")
            self.log(f"[Kreator] Wczytano {len(self.app.wizard_frames)} ramek z {path}")
            start_btn.config(state='normal')
            self.app.wizard_left = 0
            self.app.wizard_right = len(self.app.wizard_frames) - 1
            self.app._redraw_wizard_progress()
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się wczytać pliku: {e}")

    def add_sequence_frame(self):
        import tkinter as tk
        from tkinter import ttk
        dialog = tk.Toplevel(self.app.root)
        dialog.title("Dodaj ramkę do sekwencji")
        dialog.geometry("300x200")
        dialog.transient(self.app.root)
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
                self.app.wizard_sequence.append((cid, data, is_ext))
                self.app.wizard_seq_listbox.insert(tk.END, f"ID=0x{cid:08X} Data={data.hex().upper() if data else '-'} EXT={is_ext}")
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Błąd", "Nieprawidłowy format ID lub danych")

        ttk.Button(dialog, text="Dodaj", command=save).grid(row=3, column=0, columnspan=2, pady=10)

    def remove_sequence_frame(self):
        selection = self.app.wizard_seq_listbox.curselection()
        if selection:
            index = selection[0]
            self.app.wizard_seq_listbox.delete(index)
            del self.app.wizard_sequence[index]

    def reset(self):
        if self.app.wizard_thread and self.app.wizard_thread.is_alive():
            self.app.wizard_thread.stop()
        self.app.wizard_start_btn.config(state='normal')
        self.app.wizard_yes_btn.config(state='disabled')
        self.app.wizard_no_btn.config(state='disabled')
        self.app.wizard_stop_btn.config(state='disabled')
        self.app.wizard_undo_btn.config(state='disabled')
        if hasattr(self.app, 'wizard_export_btn'):
            self.app.wizard_export_btn.config(state='disabled')
        self.app.wizard_progress.config(text="Postęp: --")
        self.app.wizard_left = 0
        self.app.wizard_right = len(self.app.wizard_frames) - 1 if self.app.wizard_frames else 0
        self.app.wizard_history.clear()
        self.app._redraw_wizard_progress()
        self.log("[Kreator] Reset.")

    def start_search(self):
        if not self.app.wizard_frames:
            messagebox.showerror("Błąd", "Najpierw wczytaj plik")
            return
        if not self.app.can.connected:
            messagebox.showerror("Błąd", "Połącz się z CAN")
            return

        mode = self.app.wizard_mode_var.get()
        if mode == "single":
            try:
                target_id = int(self.app.wizard_id_var.get().strip(), 16)
                data_str = self.app.wizard_data_var.get().strip()
                target_data = bytes.fromhex(data_str) if data_str else None
                target_is_ext = self.app.wizard_extended_var.get()
                target = (target_id, target_data, target_is_ext)
            except ValueError:
                messagebox.showerror("Błąd", "Nieprawidłowy format ID lub danych")
                return
        else:
            if not self.app.wizard_sequence:
                messagebox.showerror("Błąd", "Dodaj co najmniej jedną ramkę do sekwencji")
                return
            target = list(self.app.wizard_sequence)

        self.app.wizard_target = target
        self.app.wizard_left = 0
        self.app.wizard_right = len(self.app.wizard_frames) - 1
        self.app.wizard_history.clear()

        self.app.wizard_start_btn.config(state='disabled')
        self.app.wizard_yes_btn.config(state='normal')
        self.app.wizard_no_btn.config(state='normal')
        self.app.wizard_stop_btn.config(state='normal')
        self.app.wizard_undo_btn.config(state='normal')
        if hasattr(self.app, 'wizard_export_btn'):
            self.app.wizard_export_btn.config(state='normal')

        self.app.wizard_thread = WizardSearchThread(self.app, self.log)
        self.app.wizard_thread.setup(
            self.app.wizard_frames,
            self.app.wizard_interval.get(),
            target,
            self.app.wizard_parts_var.get(),
            self.app.wizard_use_timestamps.get()
        )
        self.app.wizard_thread.start()
        self.app._update_wizard_progress()

    def answer_yes(self):
        if self.app.wizard_thread and self.app.wizard_thread.is_alive():
            self.app.wizard_answer = True
            self.app.wizard_answer_event.set()
            self.log("[Kreator] TAK")
            self.app._update_wizard_progress()

    def answer_no(self):
        if self.app.wizard_thread and self.app.wizard_thread.is_alive():
            self.app.wizard_answer = False
            self.app.wizard_answer_event.set()
            self.log("[Kreator] NIE")
            self.app._update_wizard_progress()

    def stop_search(self):
        if self.app.wizard_thread:
            self.app.wizard_thread.stop()
        self.app.wizard_start_btn.config(state='normal')
        self.app.wizard_yes_btn.config(state='disabled')
        self.app.wizard_no_btn.config(state='disabled')
        self.app.wizard_stop_btn.config(state='disabled')
        self.app.wizard_undo_btn.config(state='disabled')
        if hasattr(self.app, 'wizard_export_btn'):
            self.app.wizard_export_btn.config(state='disabled')
        self.log("[Kreator] Zatrzymano.")

    def undo_step(self):
        if self.app.wizard_history:
            self.app.wizard_history.pop()
            if self.app.wizard_history:
                self.app.wizard_left, self.app.wizard_right = self.app.wizard_history[-1]
            else:
                self.app.wizard_left, self.app.wizard_right = 0, len(self.app.wizard_frames) - 1
            self.app._update_wizard_progress()
            self.log(f"[Kreator] Cofnięto do zakresu [{self.app.wizard_left} .. {self.app.wizard_right}]")
        else:
            messagebox.showinfo("Cofnij", "Brak wcześniejszego stanu.")

    def _add_history(self, left, right):
        self.app.wizard_history.append((left, right))

    def export_session(self):
        if not self.app.wizard_thread or not self.app.wizard_thread.history:
            messagebox.showwarning("Eksport", "Brak aktywnej sesji kreatora.")
            return
        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not filepath:
            return
        settings = {
            "interval": self.app.wizard_interval.get(),
            "use_timestamps": self.app.wizard_use_timestamps.get(),
            "num_parts": self.app.wizard_parts_var.get()
        }
        source = self.app.wizard_file_var.get()
        session = self.app.wizard_thread.export_session(settings, source)
        SessionManager.save_to_file(session, filepath)
        self.log(f"[Kreator] Sesja wyeksportowana do {filepath}")

    def import_session(self):
        filepath = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not filepath:
            return
        try:
            session = SessionManager.load_from_file(filepath)
        except Exception as e:
            messagebox.showerror("Import", f"Błąd odczytu pliku: {e}")
            return

        if not self.app.wizard_frames:
            messagebox.showwarning("Import", "Najpierw wczytaj plik z ramkami.")
            return

        self.app.wizard_interval.set(session['settings']['interval'])
        self.app.wizard_use_timestamps.set(session['settings'].get('use_timestamps', False))
        self.app.wizard_parts_var.set(session['settings'].get('num_parts', 2))

        self.app.wizard_left = 0
        self.app.wizard_right = len(self.app.wizard_frames) - 1
        self.app.wizard_history = session.get('history', [])
        if self.app.wizard_history:
            last = self.app.wizard_history[-1]
            self.app.wizard_left = last['left']
            self.app.wizard_right = last['right']

        self.app._update_wizard_progress()
        self.app.wizard_start_btn.config(state='normal')
        self.log(f"[Kreator] Sesja zaimportowana z {filepath}")
