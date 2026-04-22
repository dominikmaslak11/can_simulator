import pytest
import json
import os
import tempfile
import tkinter as tk
from unittest.mock import MagicMock, patch
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from session_manager import SessionManager

class MockApp:
    def __init__(self):
        self.entry_iface = tk.StringVar(value="vcan0")
        self.theme_var = tk.StringVar(value="light")
        self.replay_file_var = tk.StringVar(value="test.log")
        self.replay_interval = tk.DoubleVar(value=0.5)
        self.bridge_url = "ws://localhost:8765"
        self.bridge_token = "secret"
        self.bridge_filter = "0x123,0x456"
        self.chart_last_id = "0x100"
        self.chart_last_byte = "2"
        self.current_category = "Sieć i zdalny dostęp"
        self.sidebar = MagicMock()
        self.sidebar.get.return_value = ["Połączenie CAN", "Sieć i zdalny dostęp"]
        self._on_category_select = MagicMock()
        # Inne atrybuty wymagane przez _collect_state
        self.missing_ctrl = MagicMock()
        self.missing_ctrl.frames = []
        self.error_ctrl = MagicMock()
        self.error_ctrl.frames = []
        self.generator_frames = []

def test_collect_state():
    app = MockApp()
    state = SessionManager._collect_state(app)
    assert state["can_interface"] == "vcan0"
    assert state["settings"]["bridge_url"] == "ws://localhost:8765"
    assert state["settings"]["bridge_token"] == "secret"
    assert state["current_category"] == "Sieć i zdalny dostęp"

def test_save_load_session():
    app = MockApp()
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.close()
        SessionManager.save_session(app, tmp.name)
        # Modyfikujemy stan
        app.bridge_url = "changed"
        # Wczytujemy
        assert SessionManager.load_session(app, tmp.name) is True
        assert app.bridge_url == "ws://localhost:8765"
        os.unlink(tmp.name)
