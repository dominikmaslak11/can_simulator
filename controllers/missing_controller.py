from .base_controller import BaseController
from threads import SimulationThread


class MissingController(BaseController):
    def __init__(self, app):
        super().__init__(app)
        self.custom_frames = []  # lista (id, data, is_ext)

    def start_missing(self):
        self.app._start_sim()
        self.app.sim_thread.setup_missing_module(
            self.app.missing_8f.get(),
            self.app.missing_diag.get(),
            self.app.missing_spor.get(),
            self.custom_frames
        )
        self.app.sim_thread.mode = 'missing'
        self.app.sim_thread.start()
        self.app._simulation_started()

    def add_custom_frame(self, can_id, data, is_ext):
        self.custom_frames.append((can_id, data, is_ext))
        self.log(f"[Missing] Dodano niestandardową ramkę: 0x{can_id:08X}")
