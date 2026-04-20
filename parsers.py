import logging
logger = logging.getLogger("Parsers")

def parse_candump_line(line):
    line = line.strip()
    if not line or 'can0' not in line or '#' not in line:
        return None
    try:
        ts = float(line.split(')')[0].lstrip('('))
        rest = line.split('can0 ')[1]
        id_part, data_part = rest.split('#')
        can_id = int(id_part.strip(), 16)
        data = bytes.fromhex(data_part.strip())
        return (ts, can_id, data, can_id > 0x7FF)
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
        return (can_id, data, can_id > 0x7FF)
    except ValueError:
        return None

def load_frames_from_file(path):
    frames = []
    logger.info(f"Wczytywanie: {path}")
    with open(path) as f:
        for line in f:
            p = parse_candump_line(line) or parse_log_line(line)
            if p:
                frames.append((p[1] if len(p)==4 else p[0],
                               p[2] if len(p)==4 else p[1],
                               p[3] if len(p)==4 else p[2]))
    logger.info(f"Wczytano {len(frames)} ramek")
    return frames
