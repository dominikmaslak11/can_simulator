import cantools
import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


class DBCManager:
    def __init__(self):
        self.db: Optional[cantools.database.Database] = None
        self.file_path: Optional[str] = None

    def load_dbc(self, file_path: str) -> bool:
        try:
            self.db = cantools.database.load_file(file_path)
            self.file_path = file_path
            logger.info(f"Wczytano DBC: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Błąd wczytywania DBC: {e}")
            return False

    def decode_frame(self, frame_id: int, data: bytes):
        if not self.db:
            return None
        try:
            message = self.db.get_message_by_frame_id(frame_id)
            decoded = message.decode(data)
            limits = {}
            for sig in message.signals:
                limits[sig.name] = (sig.minimum, sig.maximum)
            return {
                "message_name": message.name,
                "signals": decoded,
                "limits": limits
            }
        except Exception:
            return None
                "message_name": message.name,
                "signals": decoded,
                "limits": limits
            }
        except Exception:
            return None
                "message_name": message.name,
                "signals": decoded,
                "limits": limits
            }
        except Exception:
            return None
                "message_name": message.name,
                "signals": decoded,
                "limits": limits
            }
        except Exception:
            return None
                "message_name": message.name,
                "signals": decoded
            }
        except Exception:
            return None

    def get_available_signals(self) -> List[str]:
        if not self.db:
            return []
        signals = []
        for msg in self.db.messages:
            for sig in msg.signals:
                signals.append(f"{msg.name}.{sig.name}")
        return signals

    def get_signal_info(self, signal_name: str):
        if not self.db:
            return None
        try:
            msg_name, sig_name = signal_name.split('.')
            msg = self.db.get_message_by_name(msg_name)
            sig = msg.get_signal_by_name(sig_name)
            return {
                "min": sig.minimum,
                "max": sig.maximum,
                "unit": sig.unit,
                "comment": sig.comment
            }
        except:
            return None
