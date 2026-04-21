import threading
import tkinter as tk

from controllers.base_controller import BaseController


class SnifferController(BaseController):
    def __init__(self, app):
        super().__init__(app)
        self.app.sniffer_queue = []
        self.app.sniffer_lock = threading.Lock()
        self.app.sniffer_last_data = {}
        self.app.sniffer_last_bits = {}
        self.app.sniffer_keep_alive_var = None
        self.app.sniffer_overwrite_var = None
        self.app.sniffer_bit_view_var = None
        self.keep_alive_active = False
        self.overwrite_active = False
        self.bit_view_active = False
        self.keep_alive_timeout = 2.0
        self.alive_items = {}
        self.overwrite_items = {}
        self.dbc_db = None
        self.dbc_decoding_active = False

        self.columns_normal_base = ('timestamp', 'id', 'ext', 'dlc', 'data')
        self.columns_bit_base = ('timestamp', 'id', 'ext', 'dlc', 'bits')

    # Metody, które będą nadpisywane lub używane przez mixiny
    def toggle_filter(self):
        if self.app.sniffer_filter_var.get():
            self.app.sniffer_filter_entry.config(state='normal')
        else:
            self.app.sniffer_filter_entry.config(state='disabled')

    def apply_filter(self):
        pass

    def _configure_columns(self):
        from .dbc_handler import DbcHandler
        DbcHandler._configure_columns(self)

    def _refresh_decoded_column(self):
        from .dbc_handler import DbcHandler
        DbcHandler._refresh_decoded_column(self)

    def _decode_frame(self, can_id, data):
        from .dbc_handler import DbcHandler
        return DbcHandler._decode_frame(self, can_id, data)

    def _hex_to_bits(self, hex_str):
        from .display_modes import DisplayModes
        return DisplayModes._hex_to_bits(self, hex_str)

    def _bits_to_hex(self, bits_str):
        from .display_modes import DisplayModes
        return DisplayModes._bits_to_hex(self, bits_str)


# Wstrzyknięcie metod z mixinów do klasy
from .display_modes import DisplayModes
from .dbc_handler import DbcHandler
from .core import CoreMethods
from .export import ExportMethods

for mixin in (DisplayModes, DbcHandler, CoreMethods, ExportMethods):
    for name, method in vars(mixin).items():
        if not name.startswith('_'):
            setattr(SnifferController, name, method)
