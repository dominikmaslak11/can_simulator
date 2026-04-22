import json
import os
from datetime import datetime

class SessionManager:
    @staticmethod
    def export_project(app, filepath):
        """Eksportuje cały projekt do pliku JSON (ręczny)."""
        project = SessionManager._collect_state(app)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(project, f, indent=2, ensure_ascii=False)

    @staticmethod
    def import_project(app, filepath):
        """Importuje projekt z pliku JSON."""
        with open(filepath, 'r', encoding='utf-8') as f:
            project = json.load(f)
        SessionManager._apply_state(app, project)

    @staticmethod
    def save_session(app, filepath="session.json"):
        """Zapisuje bieżący stan do pliku sesji."""
        state = SessionManager._collect_state(app)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    @staticmethod
    def load_session(app, filepath="session.json"):
        """Wczytuje stan z pliku sesji."""
        if not os.path.exists(filepath):
            return False
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                state = json.load(f)
            SessionManager._apply_state(app, state)
            return True
        except Exception:
            return False

    @staticmethod
    def _collect_state(app):
        """Zbiera cały stan aplikacji do słownika."""
        state = {
            "version": "2.0",
            "timestamp": datetime.now().isoformat(),
            "can_interface": app.entry_iface.get(),
            "notebook_tab": app.notebook.index(app.notebook.select()),
            "files": {
                "replay": getattr(app, 'replay_file_var', None) and app.replay_file_var.get(),
                "binary": getattr(app, 'binary_file_var', None) and app.binary_file_var.get(),
                "wizard": getattr(app, 'wizard_file_var', None) and app.wizard_file_var.get(),
                "normal_log": getattr(app, 'ml_normal_var', None) and app.ml_normal_var.get(),
                "anomaly_log": getattr(app, 'ml_anomaly_var', None) and app.ml_anomaly_var.get(),
                "test_log": getattr(app, 'ml_test_var', None) and app.ml_test_var.get(),
                "pattern_train": getattr(app, 'pattern_train_var', None) and app.pattern_train_var.get(),
                "pattern_test": getattr(app, 'pattern_test_var', None) and app.pattern_test_var.get(),
            },
            "settings": {
                "replay_interval": getattr(app, 'replay_interval', None) and app.replay_interval.get(),
                "replay_speed": getattr(app, 'replay_speed', None) and app.replay_speed.get(),
                "replay_loop": getattr(app, 'replay_loop', None) and app.replay_loop.get(),
                "replay_use_timestamps": getattr(app, 'replay_use_timestamps', None) and app.replay_use_timestamps.get(),
                "missing_use_timestamps": getattr(app, 'missing_use_timestamps', None) and app.missing_use_timestamps.get(),
                "missing_ref_file": getattr(app, 'missing_ref_file', None) and app.missing_ref_file.get(),
                "error_interval": getattr(app, 'error_interval', None) and app.error_interval.get(),
                "error_use_timestamps": getattr(app, 'error_use_timestamps', None) and app.error_use_timestamps.get(),
                "error_ref_file": getattr(app, 'error_ref_file', None) and app.error_ref_file.get(),
                "binary_interval": getattr(app, 'binary_interval', None) and app.binary_interval.get(),
                "binary_mode": getattr(app, 'binary_mode', None) and app.binary_mode.get(),
                "binary_parts": getattr(app, 'binary_parts', None) and app.binary_parts.get(),
                "binary_use_timestamps": getattr(app, 'binary_use_timestamps', None) and app.binary_use_timestamps.get(),
                "wizard_parts": getattr(app, 'wizard_parts_var', None) and app.wizard_parts_var.get(),
                "wizard_interval": getattr(app, 'wizard_interval', None) and app.wizard_interval.get(),
                "wizard_use_timestamps": getattr(app, 'wizard_use_timestamps', None) and app.wizard_use_timestamps.get(),
                "sniffer_filter": getattr(app, 'sniffer_filter_var', None) and app.sniffer_filter_var.get(),
                "sniffer_filter_text": getattr(app, 'sniffer_filter_entry', None) and app.sniffer_filter_entry.get(),
                "sniffer_keep_alive": getattr(app, 'sniffer_keep_alive_var', None) and app.sniffer_keep_alive_var.get(),
                "sniffer_overwrite": getattr(app, 'sniffer_overwrite_var', None) and app.sniffer_overwrite_var.get(),
                "sniffer_bit_view": getattr(app, 'sniffer_bit_view_var', None) and app.sniffer_bit_view_var.get(),
                "ml_threshold": getattr(app, 'ml_threshold', None) and app.ml_threshold.get(),
                "server_port": getattr(app, 'server_port', None) and app.server_port.get(),
                "generator_loop": getattr(app, 'generator_loop', None) and app.generator_loop.get(),
            },
            "tables": {
                "missing_frames": app.missing_ctrl.frames if hasattr(app, 'missing_ctrl') else [],
                "error_frames": app.error_ctrl.frames if hasattr(app, 'error_ctrl') else [],
                "generator_frames": getattr(app, 'generator_frames', [])
            }
        }
        return state

    @staticmethod
    def _apply_state(app, state):
        """Przywraca stan aplikacji ze słownika."""
        # Interfejs CAN
        if 'can_interface' in state:
            app.entry_iface.delete(0, 'end')
            app.entry_iface.insert(0, state['can_interface'])

        # Pliki
        files = state.get('files', {})
        if files.get('replay') and hasattr(app, 'replay_file_var'):
            app.replay_file_var.set(files['replay'])
        if files.get('binary') and hasattr(app, 'binary_file_var'):
            app.binary_file_var.set(files['binary'])
        if files.get('wizard') and hasattr(app, 'wizard_file_var'):
            app.wizard_file_var.set(files['wizard'])
        if files.get('normal_log') and hasattr(app, 'ml_normal_var'):
            app.ml_normal_var.set(files['normal_log'])
        if files.get('anomaly_log') and hasattr(app, 'ml_anomaly_var'):
            app.ml_anomaly_var.set(files['anomaly_log'])
        if files.get('test_log') and hasattr(app, 'ml_test_var'):
            app.ml_test_var.set(files['test_log'])
        if files.get('pattern_train') and hasattr(app, 'pattern_train_var'):
            app.pattern_train_var.set(files['pattern_train'])
        if files.get('pattern_test') and hasattr(app, 'pattern_test_var'):
            app.pattern_test_var.set(files['pattern_test'])

        # Ustawienia
        s = state.get('settings', {})
        if hasattr(app, 'replay_interval') and s.get('replay_interval') is not None:
            app.replay_interval.set(s['replay_interval'])
        if hasattr(app, 'replay_speed') and s.get('replay_speed') is not None:
            app.replay_speed.set(s['replay_speed'])
        if hasattr(app, 'replay_loop') and s.get('replay_loop') is not None:
            app.replay_loop.set(s['replay_loop'])
        if hasattr(app, 'replay_use_timestamps') and s.get('replay_use_timestamps') is not None:
            app.replay_use_timestamps.set(s['replay_use_timestamps'])
        if hasattr(app, 'missing_use_timestamps') and s.get('missing_use_timestamps') is not None:
            app.missing_use_timestamps.set(s['missing_use_timestamps'])
        if hasattr(app, 'missing_ref_file') and s.get('missing_ref_file') is not None:
            app.missing_ref_file.set(s['missing_ref_file'])
        if hasattr(app, 'error_interval') and s.get('error_interval') is not None:
            app.error_interval.set(s['error_interval'])
        if hasattr(app, 'error_use_timestamps') and s.get('error_use_timestamps') is not None:
            app.error_use_timestamps.set(s['error_use_timestamps'])
        if hasattr(app, 'error_ref_file') and s.get('error_ref_file') is not None:
            app.error_ref_file.set(s['error_ref_file'])
        if hasattr(app, 'binary_interval') and s.get('binary_interval') is not None:
            app.binary_interval.set(s['binary_interval'])
        if hasattr(app, 'binary_mode') and s.get('binary_mode') is not None:
            app.binary_mode.set(s['binary_mode'])
        if hasattr(app, 'binary_parts') and s.get('binary_parts') is not None:
            app.binary_parts.set(s['binary_parts'])
        if hasattr(app, 'binary_use_timestamps') and s.get('binary_use_timestamps') is not None:
            app.binary_use_timestamps.set(s['binary_use_timestamps'])
        if hasattr(app, 'wizard_parts_var') and s.get('wizard_parts') is not None:
            app.wizard_parts_var.set(s['wizard_parts'])
        if hasattr(app, 'wizard_interval') and s.get('wizard_interval') is not None:
            app.wizard_interval.set(s['wizard_interval'])
        if hasattr(app, 'wizard_use_timestamps') and s.get('wizard_use_timestamps') is not None:
            app.wizard_use_timestamps.set(s['wizard_use_timestamps'])
        if hasattr(app, 'sniffer_filter_var') and s.get('sniffer_filter') is not None:
            app.sniffer_filter_var.set(s['sniffer_filter'])
        if hasattr(app, 'sniffer_filter_entry') and s.get('sniffer_filter_text') is not None:
            app.sniffer_filter_entry.delete(0, 'end')
            app.sniffer_filter_entry.insert(0, s['sniffer_filter_text'])
        if hasattr(app, 'sniffer_keep_alive_var') and s.get('sniffer_keep_alive') is not None:
            app.sniffer_keep_alive_var.set(s['sniffer_keep_alive'])
        if hasattr(app, 'sniffer_overwrite_var') and s.get('sniffer_overwrite') is not None:
            app.sniffer_overwrite_var.set(s['sniffer_overwrite'])
        if hasattr(app, 'sniffer_bit_view_var') and s.get('sniffer_bit_view') is not None:
            app.sniffer_bit_view_var.set(s['sniffer_bit_view'])
        if hasattr(app, 'ml_threshold') and s.get('ml_threshold') is not None:
            app.ml_threshold.set(s['ml_threshold'])
        if hasattr(app, 'server_port') and s.get('server_port') is not None:
            app.server_port.set(s['server_port'])
        if hasattr(app, 'generator_loop') and s.get('generator_loop') is not None:
            app.generator_loop.set(s['generator_loop'])

        # Tabele
        tables = state.get('tables', {})
        if 'missing_frames' in tables and hasattr(app, 'missing_ctrl'):
            app.missing_ctrl.frames = tables['missing_frames']
            app.missing_ctrl._refresh_tree()
        if 'error_frames' in tables and hasattr(app, 'error_ctrl'):
            app.error_ctrl.frames = tables['error_frames']
            app.error_ctrl._refresh_tree()
        if 'generator_frames' in tables and hasattr(app, 'generator_frames'):
            app.generator_frames = tables['generator_frames']
            # odśwież drzewo
            if hasattr(app, 'generator_tree'):
                app.generator_tree.delete(*app.generator_tree.get_children())
                for f in app.generator_frames:
                    app.generator_tree.insert("", tk.END, values=(
                        f"0x{f['id']:08X}", f['data'].hex().upper(),
                        "X" if f['ext'] else "", f"{f['interval']:.3f}"
                    ))
                if app.generator_frames:
                    app.generator_start_btn.config(state='normal')
