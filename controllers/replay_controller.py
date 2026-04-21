from .base_controller import BaseController
from tkinter import messagebox
from threads import SimulationThread

class ReplayController(BaseController):
    def start_replay(self):
        if not self.app.loaded_frames:
            messagebox.showerror("Błąd", "Najpierw wczytaj plik")
            return
        self.app._start_sim()
        self.app.sim_thread.setup_replay(
            self.app.loaded_frames,
            self.app.replay_interval.get(),
            self.app.replay_loop.get(),
            self.app.replay_speed.get(),
            self.app.replay_use_timestamps.get()
        )
        self.app.sim_thread.start()
        self.app._simulation_started()
