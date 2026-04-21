import logging
logger = logging.getLogger("Parsers")

def parse_candump_line(line):
    line = line.strip()
    if not line or 'can0' not in line or '#' not in line:
        return None
    try:
        ts_part = line.split(')')[0].lstrip('(')
        timestamp = float(ts_part)
        rest = line.split('can0 ')[1]
        id_part, data_part = rest.split('#')
        can_id = int(id_part.strip(), 16)
        data = bytes.fromhex(data_part.strip())
        is_extended = (can_id > 0x7FF)
        return (timestamp, can_id, data, is_extended)
    except Exception:
        return None

def parse_log_line(line):
    if 'Wysłano:' not in line:
        return None
    parts = line.split('Wysłano:')
    if len(parts) < 2:
        return None
    candata = parts[1].strip()
    if '#' not in candata:
        return None
    id_part, data_part = candata.split('#')
    try:
        can_id = int(id_part.strip(), 16)
        data = bytes.fromhex(data_part.strip())
        is_extended = (can_id > 0x7FF)
        return (None, can_id, data, is_extended)   # timestamp = None
    except ValueError:
        return None

def load_frames_from_file(path):
    frames = []
    logger.info(f"Wczytywanie: {path}")
    with open(path, 'r') as f:
        for line in f:
            p = parse_candump_line(line)
            if p:
                ts, can_id, data, is_ext = p
                frames.append((can_id, data, is_ext, ts))
                continue
            p = parse_log_line(line)
            if p:
                ts, can_id, data, is_ext = p
                frames.append((can_id, data, is_ext, ts))
    logger.info(f"Wczytano {len(frames)} ramek")
    return frames
