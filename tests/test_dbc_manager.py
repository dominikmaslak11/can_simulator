import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dbc_manager import DBCManager

def test_dbc_manager_init():
    mgr = DBCManager()
    assert mgr.db is None
    assert mgr.file_path is None

def test_load_invalid_dbc():
    mgr = DBCManager()
    result = mgr.load_dbc("nonexistent.dbc")
    assert result is False

def test_decode_without_db():
    mgr = DBCManager()
    assert mgr.decode_frame(0x123, b'\x00\x01') is None

# Test z użyciem przykładowego pliku DBC (jeśli istnieje)
def test_load_example_dbc():
    mgr = DBCManager()
    example_path = os.path.join(os.path.dirname(__file__), "..", "example.dbc")
    if os.path.exists(example_path):
        assert mgr.load_dbc(example_path) is True
        signals = mgr.get_available_signals()
        assert len(signals) > 0
        # Sprawdź dekodowanie przykładowej ramki
        # Dla ID 0x100 (EngineData) z bajtami: 0x64,0x00,0x00,0x00,0x00,0x00,0x00,0x00
        # EngineSpeed powinno wynosić 100
        dec = mgr.decode_frame(0x100, bytes([0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))
        assert dec is not None
        assert "EngineSpeed" in dec["signals"]
        assert dec["signals"]["EngineSpeed"] == pytest.approx(100.0)
