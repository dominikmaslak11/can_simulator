import json
import os
from datetime import datetime

class ProjectManager:
    @staticmethod
    def export_project(app, filepath):
        """Zapisuje stan aplikacji do pliku JSON."""
        project = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "can_interface": app.entry_iface.get(),
            "files": {
                "replay": getattr(app, 'replay_file_var', None) and app.replay_file_var.get(),
                "binary": getattr(app, 'binary_file_var', None) and app.binary_file_var.get(),
                "wizard": getattr(app, 'wizard_file_var', None) and app.wizard_file_var.get(),
                "normal_log": getattr(app, 'ml_normal_var', None) and app.ml_normal_var.get(),
                "anomaly_log": getattr(app, 'ml_anomaly_var', None) and app.ml_anomaly_var.get(),
                "test_log": getattr(app, 'ml_test_var', None) and app.ml_test_var.get(),
                "dbc": getattr(app, 'sniffer_dbc_status', None) and app.sniffer_ctrl.dbc_db and "dbc_loaded"
            },
            "settings": {
                "replay_interval": getattr(app, 'replay_interval', None) and app.replay_interval.get(),
                "replay_speed": getattr(app, 'replay_speed', None) and app.replay_speed.get(),
                "replay_loop": getattr(app, 'replay_loop', None) and app.replay_loop.get(),
                "replay_use_timestamps": getattr(app, 'replay_use_timestamps', None) and app.replay_use_timestamps.get(),
                "missing_8f": getattr(app, 'missing_8f', None) and app.missing_8f.get(),
                "missing_diag": getattr(app, 'missing_diag', None) and app.missing_diag.get(),
                "missing_spor": getattr(app, 'missing_spor', None) and app.missing_spor.get(),
                "missing_use_timestamps": getattr(app, 'missing_use_timestamps', None) and app.missing_use_timestamps.get(),
                "error_interval": getattr(app, 'error_interval', None) and app.error_interval.get(),
                "error_code": getattr(app, 'error_code', None) and app.error_code.get(),
                "error_use_timestamps": getattr(app, 'error_use_timestamps', None) and app.error_use_timestamps.get(),
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
                "ml_threshold": getattr(app, 'ml_threshold', None) and app.ml_threshold.get()
            }
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(project, f, indent=2, ensure_ascii=False)

    @staticmethod
    def import_project(app, filepath):
        """Wczytuje stan aplikacji z pliku JSON."""
        with open(filepath, 'r', encoding='utf-8') as f:
            project = json.load(f)

        # Interfejs CAN
        if 'can_interface' in project:
            app.entry_iface.delete(0, 'end')
            app.entry_iface.insert(0, project['can_interface'])

        # Pliki
        files = project.get('files', {})
        if files.get('replay'):
            app.replay_file_var.set(files['replay'])
        if files.get('binary'):
            app.binary_file_var.set(files['binary'])
        if files.get('wizard'):
            app.wizard_file_var.set(files['wizard'])
        if files.get('normal_log'):
            app.ml_normal_var.set(files['normal_log'])
        if files.get('anomaly_log'):
            app.ml_anomaly_var.set(files['anomaly_log'])
        if files.get('test_log'):
            app.ml_test_var.set(files['test_log'])

        # Ustawienia
        s = project.get('settings', {})
        if hasattr(app, 'replay_interval') and s.get('replay_interval') is not None:
            app.replay_interval.set(s['replay_interval'])
        if hasattr(app, 'replay_speed') and s.get('replay_speed') is not None:
            app.replay_speed.set(s['replay_speed'])
        if hasattr(app, 'replay_loop') and s.get('replay_loop') is not None:
            app.replay_loop.set(s['replay_loop'])
        if hasattr(app, 'replay_use_timestamps') and s.get('replay_use_timestamps') is not None:
            app.replay_use_timestamps.set(s['replay_use_timestamps'])
        if hasattr(app, 'missing_8f') and s.get('missing_8f') is not None:
            app.missing_8f.set(s['missing_8f'])
        if hasattr(app, 'missing_diag') and s.get('missing_diag') is not None:
            app.missing_diag.set(s['missing_diag'])
        if hasattr(app, 'missing_spor') and s.get('missing_spor') is not None:
            app.missing_spor.set(s['missing_spor'])
        if hasattr(app, 'missing_use_timestamps') and s.get('missing_use_timestamps') is not None:
            app.missing_use_timestamps.set(s['missing_use_timestamps'])
        if hasattr(app, 'error_interval') and s.get('error_interval') is not None:
            app.error_interval.set(s['error_interval'])
        if hasattr(app, 'error_code') and s.get('error_code') is not None:
            app.error_code.set(s['error_code'])
        if hasattr(app, 'error_use_timestamps') and s.get('error_use_timestamps') is not None:
            app.error_use_timestamps.set(s['error_use_timestamps'])
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
