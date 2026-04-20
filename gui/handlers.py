import tkinter.messagebox as messagebox


class ConnectionHandlers:
    def toggle_connection(self):
        if self.can.connected:
            self.can.disconnect()
            self.lbl_status.config(text="Niepołączony", foreground="red")
            self.btn_connect.config(text="Połącz")
            self._set_buttons_state('disabled')
        else:
            iface = self.entry_iface.get().strip()
            if not iface:
                messagebox.showerror("Błąd", "Podaj nazwę interfejsu")
                return
            success, msg = self.can.connect()
            if success:
                self.lbl_status.config(text=f"Połączony: {iface}", foreground="green")
                self.btn_connect.config(text="Rozłącz")
                self._set_buttons_state('normal')
                self.log(msg)
            else:
                messagebox.showerror("Błąd", msg)

    def _set_buttons_state(self, state):
        buttons = [
            self.replay_start_btn, self.missing_start_btn, self.error_start_btn,
            self.manual_send_once_btn, self.manual_start_btn, self.binary_start_btn
        ]
        for btn in buttons:
            btn.config(state=state)
        if state == 'disabled':
            disable_buttons = [
                self.replay_pause_btn, self.replay_stop_btn, self.manual_stop_btn,
                self.binary_yes_btn, self.binary_no_btn, self.binary_stop_btn, self.binary_undo_btn
            ]
            for btn in disable_buttons:
                btn.config(state=state)
