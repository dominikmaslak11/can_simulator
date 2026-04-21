from .base_controller import BaseController
from tkinter import messagebox, simpledialog
import threading
from threads import BinarySearchThread


class BinaryController(BaseController):
    def start_binary_search(self):
        if not self.app.binary_frames:
            messagebox.showerror("Błąd", "Najpierw wczytaj plik")
            return
        if not self.app.can.connected:
            messagebox.showerror("Błąd", "Połącz się z CAN")
            return

        self.app.binary_start_btn.config(state='disabled')
        self.app.binary_yes_btn.config(state='normal')
        self.app.binary_no_btn.config(state='normal')
        self.app.binary_stop_btn.config(state='normal')
        self.app.binary_undo_btn.config(state='normal')
        if hasattr(self.app, 'binary_export_btn') and self.app.binary_export_btn:
            self.app.binary_export_btn.config(state='normal')

        self.app.binary_answer = None
        self.app.binary_answer_event = threading.Event()

        def ask_callback(prompt="Czy zjawisko wystąpiło?", input_type='yesno', choices=None, default=None):
            self.app.binary_answer_event.clear()
            self.log(f"[Binary] {prompt}")
            if input_type == 'yesno':
                self.app.binary_answer_event.wait()
                return self.app.binary_answer
            elif input_type == 'choice':
                choice = simpledialog.askinteger("Wybór", prompt, minvalue=1, maxvalue=len(choices))
                self.app.binary_answer_event.set()
                return choice - 1 if choice is not None else None
            elif input_type == 'integer':
                val = simpledialog.askinteger("Liczba części", prompt, initialvalue=default)
                self.app.binary_answer_event.set()
                return val
            else:
                self.app.binary_answer_event.wait()
                return self.app.binary_answer

        self.app._start_binary_thread(ask_callback)
        self.app.binary_thread.start()
        self.app._update_binary_progress()

    def binary_answer_yes(self):
        if self.app.binary_thread and self.app.binary_thread.is_alive():
            self.app.binary_answer = True
            self.app.binary_answer_event.set()
            self.log("[Binary] TAK")
            self.app._update_binary_progress()

    def binary_answer_no(self):
        if self.app.binary_thread and self.app.binary_thread.is_alive():
            self.app.binary_answer = False
            self.app.binary_answer_event.set()
            self.log("[Binary] NIE")
            self.app._update_binary_progress()

    def stop_binary_search(self):
        if self.app.binary_thread:
            self.app.binary_thread.stop()
        self.app._binary_done()
        self.log("[Binary] Zatrzymano.")

    def send_to_error_sim(self):
        if not self.app.discovered_artifacts:
            messagebox.showinfo("Brak artefaktów", "Najpierw znajdź ramkę.")
            return
        name, art = list(self.app.discovered_artifacts.items())[-1]
        self.app.error_ctrl.set_from_artifact(art['id'], art['data'], art['ext'])
        self.app.notebook.select(self.app.tab_error)
        self.log(f"[Binary] Przekazano artefakt do symulacji błędów.")

    def send_to_missing_sim(self):
        if not self.app.discovered_artifacts:
            messagebox.showinfo("Brak artefaktów", "Najpierw znajdź ramkę.")
            return
        name, art = list(self.app.discovered_artifacts.items())[-1]
        self.app.missing_ctrl.add_custom_frame(art['id'], art['data'], art['ext'])
        self.app.notebook.select(self.app.tab_missing)
        self.log(f"[Binary] Dodano ramkę do symulacji modułu.")

    def send_to_error_sim(self):
        if not self.app.discovered_artifacts:
            messagebox.showinfo("Brak artefaktów", "Najpierw znajdź ramkę.")
            return
        name, art = list(self.app.discovered_artifacts.items())[-1]
        self.app.error_ctrl.set_from_artifact(art['id'], art['data'], art['ext'])
        self.app.notebook.select(self.app.tab_error)
        self.log(f"[Binary] Przekazano artefakt do symulacji błędów.")

    def send_to_missing_sim(self):
        if not self.app.discovered_artifacts:
            messagebox.showinfo("Brak artefaktów", "Najpierw znajdź ramkę.")
            return
        name, art = list(self.app.discovered_artifacts.items())[-1]
        self.app.missing_ctrl.add_custom_frame(art['id'], art['data'], art['ext'])
        self.app.notebook.select(self.app.tab_missing)
        self.log(f"[Binary] Dodano ramkę do symulacji modułu.")
