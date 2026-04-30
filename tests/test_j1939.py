"""Testy parsera J1939."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from parsers_j1939 import parse_j1939_id


def test_parse_j1939_id():
    result = parse_j1939_id(0x18FEF100)
    assert result["priority"] == 6
    assert result["pgn"] == 0xFEF1
    assert result["source_address"] == 0x00


def test_parse_another():
    result = parse_j1939_id(0x0CF0040B)
    assert result["priority"] == 3
    assert result["pgn"] == 0xF004
    assert result["source_address"] == 0x0B
