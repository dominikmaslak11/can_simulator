from .base_controller import BaseController
from threads import SimulationThread

class ErrorController(BaseController):
    def start_error(self):
        self.app._start_sim()
        try:
            code = int(self.app.error_code.get().strip(), 16)
        except ValueError:
            code = 0x19
        self.app.sim_thread.setup_error_frames(self.app.error_interval.get(), code)
        self.app.sim_thread.mode = 'error'
        self.app.sim_thread.start()
        self.app._simulation_started()
