"""Parser identyfikatorów J1939 (29-bit)."""

def parse_j1939_id(arb_id: int):
    """
    Rozbija 29-bitowy identyfikator J1939 na składowe:
    - priority (3 bity, najstarsze)
    - pgn (18 bitów)
    - source_address (8 bitów)
    Zwraca słownik.
    """
    priority = (arb_id >> 26) & 0x07
    pgn = (arb_id >> 8) & 0x3FFFF
    source_address = arb_id & 0xFF
    return {
        "priority": priority,
        "pgn": pgn,
        "source_address": source_address
    }
