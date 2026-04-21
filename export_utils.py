import csv
import os
from datetime import datetime


def export_candidates_to_csv(candidates, filename=None):
    """
    Eksportuje listę kandydatów (ramki przed dezaktywacją) do pliku CSV.
    candidates: lista krotek (can_id, data, is_ext, timestamp)
    """
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"candidates_{timestamp}.csv"

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Index", "ID", "Data (hex)", "Extended", "Timestamp"])
        for i, (cid, data, is_ext, ts) in enumerate(candidates, 1):
            writer.writerow([i, f"0x{cid:08X}", data.hex().upper(), "Yes" if is_ext else "No", f"{ts:.6f}"])
    return filename


def export_frame_to_csv(cid, data, is_ext, filename=None):
    """
    Eksportuje pojedynczą ramkę (np. znaleziony alert/dezaktywator) do CSV.
    """
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"frame_{timestamp}.csv"

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Data (hex)", "Extended"])
        writer.writerow([f"0x{cid:08X}", data.hex().upper(), "Yes" if is_ext else "No"])
    return filename


def export_frames_to_csv(frames, filename=None):
    """
    Eksportuje listę ramek (bez timestampów) do CSV.
    frames: lista krotek (can_id, data, is_ext)
    """
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"frames_{timestamp}.csv"

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Index", "ID", "Data (hex)", "Extended"])
        for i, (cid, data, is_ext) in enumerate(frames, 1):
            writer.writerow([i, f"0x{cid:08X}", data.hex().upper(), "Yes" if is_ext else "No"])
    return filename
