import json
import os
from datetime import datetime

class SessionManager:
    """Zapis i odczyt stanu sesji do pliku JSON."""

    @staticmethod
    def save_session(filepath, app_state):
        """
        Zapisuje stan aplikacji do pliku .cansession.
        :param filepath: ścieżka do pliku
        :param app_state: słownik z danymi sesji
        """
        session_data = {
            "timestamp": datetime.now().isoformat(),
            "version": "1.0",
            "app_state": app_state
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def load_session(filepath):
        """
        Wczytuje stan sesji z pliku .cansession.
        :return: słownik z danymi sesji lub None w przypadku błędu
        """
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("app_state", {})
        except Exception:
            return None
