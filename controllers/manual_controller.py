from .base_controller import BaseController
from tkinter import messagebox
import threading
import time

class ManualController(BaseController):
    def manual_send_once(self):
        if not self.app.can.connected:
            messagebox.showerror("Błąd", "Połącz się z CAN")
            return
        try:
            can_id = int(self.app.manual_id.get().strip(), 16)
            data = bytes.fromhex(self.app.manual_data.get().strip())
        except ValueError:
            messagebox.showerror("Błąd", "Nieprawidłowy format ID lub danych")
            return
        success, msg = self.app.can.send_frame(can_id, data, self.app.manual_extended.get())
        self.log(msg)

    def manual_start_cyclic(self):
        if not self.app.can.connected:
            messagebox.showerror("Błąd", "Połącz się z CAN")
            return
        try:
            can_id = int(self.app.manual_id.get().strip(), 16)
            data = bytes.fromhex(self.app.manual_data.get().strip())
        except ValueError:
            messagebox.showerror("Błąd", "Nieprawidłowy format")
            return
        interval = self.app.manual_interval.get()
        if interval <= 0:
            messagebox.showerror("Błąd", "Interwał musi być > 0")
            return

        self.app.manual_cyclic_active = True
        self.app.manual_start_btn.config(state='disabled')
        self.app.manual_send_once_btn.config(state='disabled')
        self.app.manual_stop_btn.config(state='normal')

        def worker():
            while self.app.manual_cyclic_active:
                success, msg = self.app.can.send_frame(can_id, data, self.app.manual_extended.get())
                self.log(msg)
                time.sleep(interval)

        self.app.manual_cyclic_thread = threading.Thread(target=worker, daemon=True)
        self.app.manual_cyclic_thread.start()

    def manual_stop_cyclic(self):
        self.app.manual_cyclic_active = False
        self.app.manual_start_btn.config(state='normal')
        self.app.manual_send_once_btn.config(state='normal')
        self.app.manual_stop_btn.config(state='disabled')
        self.log("Zatrzymano wysyłanie cykliczne")
