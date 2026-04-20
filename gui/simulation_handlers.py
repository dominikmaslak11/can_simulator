import tkinter.messagebox as messagebox
import threading
import time
from threads import SimulationThread


class SimulationHandlers:
    def _update_step_preview(self):
        if self.step_frames and self.step_idx < len(self.step_frames):
            cid, data, is_ext = self.step_frames[self.step_idx]
            ext_str = " (EXT)" if is_ext else ""
            self.step_preview.config(text=f"Następna: ID=0x{cid:08X}{ext_str} Data={data.hex().upper()}")
        else:
            self.step_preview.config(text="Koniec listy")

    def step_next(self):
        if not self.step_frames or self.step_idx >= len(self.step_frames):
            messagebox.showinfo("Koniec", "Wszystkie ramki zostały wysłane")
            return
        if not self.can.connected:
            messagebox.showerror("Błąd", "Połącz się z CAN")
            return
        cid, data, is_ext = self.step_frames[self.step_idx]
        success, msg = self.can.send_frame(cid, data, is_ext)
        self.log(msg)
        self.step_idx += 1
        self.step_progress.config(text=f"{self.step_idx} / {len(self.step_frames)}")
        self._update_step_preview()

    def start_replay(self):
        if not self.loaded_frames:
            messagebox.showerror("Błąd", "Najpierw wczytaj plik")
            return
        self._start_sim()
        self.sim_thread.setup_replay(
            self.loaded_frames,
            self.replay_interval.get(),
            self.replay_loop.get(),
            self.replay_speed.get()
        )
        self.sim_thread.start()
        self._simulation_started()

    def start_missing(self):
        self._start_sim()
        self.sim_thread.setup_missing_module(
            self.missing_8f.get(),
            self.missing_diag.get(),
            self.missing_spor.get()
        )
        self.sim_thread.mode = 'missing'
        self.sim_thread.start()
        self._simulation_started()

    def start_error(self):
        self._start_sim()
        try:
            code = int(self.error_code.get().strip(), 16)
        except ValueError:
            code = 0x19
        self.sim_thread.setup_error_frames(self.error_interval.get(), code)
        self.sim_thread.mode = 'error'
        self.sim_thread.start()
        self._simulation_started()

    def _start_sim(self):
        if self.sim_thread and self.sim_thread.is_alive():
            self.sim_thread.stop()
            self.sim_thread.join(timeout=0.5)
        self.sim_thread = SimulationThread(self.can, self.log)

    def _simulation_started(self):
        self.replay_start_btn.config(text="Wznów", state='normal')
        self.replay_pause_btn.config(state='normal')
        self.replay_stop_btn.config(state='normal')

    def pause_sim(self):
        if self.sim_thread:
            self.sim_thread.pause()
            self.replay_start_btn.config(text="Wznów", state='normal')
            self.log("Pauza")

    def stop_sim(self):
        if self.sim_thread:
            self.sim_thread.stop()
            self.log("Zatrzymano")
        self.replay_start_btn.config(text="Start", state='normal')
        self.replay_pause_btn.config(state='disabled')
        self.replay_stop_btn.config(state='disabled')

    def manual_send_once(self):
        if not self.can.connected:
            messagebox.showerror("Błąd", "Połącz się z CAN")
            return
        try:
            can_id = int(self.manual_id.get().strip(), 16)
            data = bytes.fromhex(self.manual_data.get().strip())
        except ValueError:
            messagebox.showerror("Błąd", "Nieprawidłowy format ID lub danych")
            return
        success, msg = self.can.send_frame(can_id, data, self.manual_extended.get())
        self.log(msg)

    def manual_start_cyclic(self):
        if not self.can.connected:
            messagebox.showerror("Błąd", "Połącz się z CAN")
            return
        try:
            can_id = int(self.manual_id.get().strip(), 16)
            data = bytes.fromhex(self.manual_data.get().strip())
        except ValueError:
            messagebox.showerror("Błąd", "Nieprawidłowy format")
            return
        interval = self.manual_interval.get()
        if interval <= 0:
            messagebox.showerror("Błąd", "Interwał musi być > 0")
            return

        self.manual_cyclic_active = True
        self.manual_start_btn.config(state='disabled')
        self.manual_send_once_btn.config(state='disabled')
        self.manual_stop_btn.config(state='normal')

        def worker():
            while self.manual_cyclic_active:
                success, msg = self.can.send_frame(can_id, data, self.manual_extended.get())
                self.log(msg)
                time.sleep(interval)

        self.manual_cyclic_thread = threading.Thread(target=worker, daemon=True)
        self.manual_cyclic_thread.start()

    def manual_stop_cyclic(self):
        self.manual_cyclic_active = False
        self.manual_start_btn.config(state='normal')
        self.manual_send_once_btn.config(state='normal')
        self.manual_stop_btn.config(state='disabled')
        self.log("Zatrzymano wysyłanie cykliczne")
