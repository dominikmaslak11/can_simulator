import pytest
from parsers import parse_candump_line, parse_log_line

def test_parse_candump_line_standard():
    line = "(1776425664.880567) can0 0C00004C#0001000000030200"
    result = parse_candump_line(line)
    assert result is not None
    ts, can_id, data, is_ext = result
    assert ts == 1776425664.880567
    assert can_id == 0x0C00004C
    assert data.hex().upper() == "0001000000030200"
    assert is_ext is False

def test_parse_candump_line_extended():
    line = "(1776425664.885561) can0 08200067#0000000000000000"
    result = parse_candump_line(line)
    assert result is not None
    ts, can_id, data, is_ext = result
    assert can_id == 0x08200067
    assert is_ext is False

def test_parse_log_line():
    line = "[12:34:56] Wysłano ID=0x0C00008F Data=0101"
    result = parse_log_line(line)
    assert result is not None
    can_id, data, is_ext = result
    assert can_id == 0x0C00008F
    assert data.hex().upper() == "0101"
    assert is_ext is True

def test_parse_candump_invalid():
    assert parse_candump_line("invalid line") is None
    assert parse_candump_line("") is None
