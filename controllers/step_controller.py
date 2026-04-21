from .base_controller import BaseController
from tkinter import messagebox

class StepController(BaseController):
    def step_next(self):
        if not self.app.step_frames or self.app.step_idx >= len(self.app.step_frames):
            messagebox.showinfo("Koniec", "Wszystkie ramki zostały wysłane")
            return
        if not self.app.can.connected:
            messagebox.showerror("Błąd", "Połącz się z CAN")
            return
        cid, data, is_ext = self.app.step_frames[self.app.step_idx]
        success, msg = self.app.can.send_frame(cid, data, is_ext)
        self.log(msg)
        self.app.step_idx += 1
        self.app.step_progress.config(text=f"{self.app.step_idx} / {len(self.app.step_frames)}")
        self.app._update_step_preview()
