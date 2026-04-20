import pytest
import tempfile
import os
from parsers import parse_candump_line, parse_log_line, load_frames_from_file


def test_parse_candump_line_valid():
    line = "(1776425664.880567) can0 0C00004C#0001000000030200"
    result = parse_candump_line(line)
    assert result is not None
    ts, can_id, data, is_ext = result
    assert ts == 1776425664.880567
    assert can_id == 0x0C00004C
    assert data.hex().upper() == "0001000000030200"
    assert is_ext is False


def test_parse_candump_line_extended():
    line = "(1776425664.885561) can0 1CFF66F0#11007530753000DD"
    result = parse_candump_line(line)
    assert result is not None
    ts, can_id, data, is_ext = result
    assert can_id == 0x1CFF66F0
    assert is_ext is True


def test_parse_candump_line_invalid():
    assert parse_candump_line("invalid line") is None
    assert parse_candump_line("") is None
    assert parse_candump_line("(123) can0 123#ZZ") is None  # niepoprawny hex


def test_parse_log_line_valid():
    line = "Wysłano: 0C00008F#0101"
    result = parse_log_line(line)
    assert result is not None
    can_id, data, is_ext = result
    assert can_id == 0x0C00008F
    assert data.hex().upper() == "0101"
    assert is_ext is True


def test_parse_log_line_invalid():
    assert parse_log_line("Brak ramki") is None
    assert parse_log_line("Wysłano: 123") is None


def test_load_frames_from_file():
    content = """(1776425664.880567) can0 0C00004C#0001000000030200
(1776425664.885561) can0 1CFF66F0#11007530753000DD
Wysłano: 0C00008F#0101
"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write(content)
        temp_path = f.name

    try:
        frames = load_frames_from_file(temp_path)
        assert len(frames) == 3
        # Pierwsza ramka (standardowa)
        assert frames[0][0] == 0x0C00004C
        assert not frames[0][2]
        # Druga ramka (rozszerzona)
        assert frames[1][0] == 0x1CFF66F0
        assert frames[1][2]
        # Trzecia ramka z logu
        assert frames[2][0] == 0x0C00008F
    finally:
        os.unlink(temp_path)
