from .base_controller import BaseController
from tkinter import messagebox

class CanController(BaseController):
    def toggle_connection(self):
        if self.app.can.connected:
            self.app.can.disconnect()
            self.app.lbl_status.config(text="Niepołączony", foreground="red")
            self.app.btn_connect.config(text="Połącz")
            self.app._set_buttons_state('disabled')
            self.log("Rozłączono z CAN")
        else:
            iface = self.app.entry_iface.get().strip()
            if not iface:
                messagebox.showerror("Błąd", "Podaj nazwę interfejsu")
                return
            success, msg = self.app.can.connect()
            if success:
                self.app.lbl_status.config(text=f"Połączony: {iface}", foreground="green")
                self.app.btn_connect.config(text="Rozłącz")
                self.app._set_buttons_state('normal')
                self.log(msg)
            else:
                messagebox.showerror("Błąd", msg)
