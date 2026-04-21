from .base_controller import BaseController
from threads import SimulationThread


class ErrorController(BaseController):
    def __init__(self, app):
        super().__init__(app)
        self.app.error_custom_id = None
        self.app.error_custom_data = None
        self.app.error_use_custom = False

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

    def set_from_artifact(self, can_id, data, is_ext):
        """Wypełnia pola formularza na podstawie znalezionej ramki."""
        if len(data) >= 2:
            self.app.error_code.set(f"{data[1]:02X}")
        self.app.error_custom_id = can_id
        self.app.error_custom_data = data
        self.app.error_use_custom = True
        self.log(f"[Error] Ustawiono kod błędu z artefaktu: ID=0x{can_id:08X}")
