from .base_controller import BaseController
from threads import SimulationThread

class MissingController(BaseController):
    def start_missing(self):
        self.app._start_sim()
        self.app.sim_thread.setup_missing_module(
            self.app.missing_8f.get(),
            self.app.missing_diag.get(),
            self.app.missing_spor.get()
        )
        self.app.sim_thread.mode = 'missing'
        self.app.sim_thread.start()
        self.app._simulation_started()
