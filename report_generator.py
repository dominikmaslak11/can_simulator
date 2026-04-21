from datetime import datetime

class ReportGenerator:
    """Generuje raport tekstowy z sesji diagnostycznej."""

    @staticmethod
    def generate(state):
        """
        state: słownik zawierający dane sesji (podobny do zapisywanego w SessionManager)
        Zwraca tekst raportu.
        """
        lines = []
        lines.append("=" * 60)
        lines.append("RAPORT Z SESJI DIAGNOSTYCZNEJ CAN SIMULATOR")
        lines.append("=" * 60)
        lines.append(f"Data wygenerowania: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Plik źródłowy
        replay = state.get("replay", {})
        binary = state.get("binary", {})
        file_path = replay.get("file_path") or binary.get("file_path") or "Nieznany"
        lines.append(f"Plik źródłowy: {file_path}")
        lines.append("")

        # Parametry wyszukiwania
        lines.append("--- PARAMETRY WYSZUKIWANIA ---")
        lines.append(f"Tryb: {binary.get('mode', 'nieznany')}")
        lines.append(f"Interwał: {binary.get('interval', 0.1)} s")
        if binary.get('mode') in ('hunt_deactivator', 'rl_hunt'):
            lines.append(f"Alert ID: {binary.get('hunt_alert_id', '?')}")
            lines.append(f"Okres alertu: {binary.get('hunt_period', 1.0)} s")
            lines.append(f"Tolerancja: ±{binary.get('hunt_tolerance', 0.2)}")
            lines.append(f"Indeks startowy: {binary.get('hunt_start_index', 0)}")
        lines.append("")

        # Znalezione ramki
        frames_data = state.get("frames", {})
        loaded = frames_data.get("loaded", [])
        if loaded:
            lines.append("--- RAMKA ALERTU (początek zjawiska) ---")
            # Zakładamy, że pierwsza ramka z loaded to alert (lub można wskazać konkretną)
            cid, data_hex, is_ext = loaded[0] if loaded else ("?", "?", False)
            lines.append(f"ID: 0x{cid:08X}" if isinstance(cid, int) else f"ID: {cid}")
            lines.append(f"Dane: {data_hex}")
            lines.append(f"Rozszerzona: {'Tak' if is_ext else 'Nie'}")
            lines.append("")

        binary_frames = frames_data.get("binary", [])
        if binary_frames:
            lines.append("--- RAMKA DEZAKTYWATORA (koniec zjawiska) ---")
            cid, data_hex, is_ext = binary_frames[0] if binary_frames else ("?", "?", False)
            lines.append(f"ID: 0x{cid:08X}" if isinstance(cid, int) else f"ID: {cid}")
            lines.append(f"Dane: {data_hex}")
            lines.append(f"Rozszerzona: {'Tak' if is_ext else 'Nie'}")
            lines.append("")

        # Historia wyszukiwania
        history = state.get("history", {}).get("binary_history", [])
        if history:
            lines.append("--- HISTORIA DECYZJI ---")
            for step in history:
                ts = step.get("timestamp", "?")
                action = step.get("action", "?")
                left = step.get("left", "?")
                right = step.get("right", "?")
                lines.append(f"{ts}: {action} -> zakres [{left}..{right}]")
            lines.append("")

        # Statystyki
        lines.append("--- STATYSTYKI ---")
        lines.append(f"Liczba ramek w logu: {len(loaded) if loaded else '?'}")
        lines.append(f"Liczba kandydatów (dezaktywacja): {len(binary_frames) if binary_frames else '?'}")
        lines.append("")

        lines.append("=" * 60)
        lines.append("KONIEC RAPORTU")
        return "\n".join(lines)
