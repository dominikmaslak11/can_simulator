import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
import threading
import time
import logging

from can_interface import CanInterface
from threads import SimulationThread, BinarySearchThread
from gui.tabs import replay_tab, missing_tab, error_tab, step_tab, manual_tab, binary_tab, wizard_tab, sniffer_tab, chart_tab, ml_analysis_tab, pattern_tab, server_tab, generator_tab, macro_tab, advanced_ml_tab
from gui.tabs.anomaly_tab import setup_anomaly_tab
from gui.tabs.remote_monitor_tab import setup_remote_monitor_tab
from gui.tabs.dbc_manager_tab import setup_dbc_manager_tab
from gui.tabs.bridge_tab import setup_bridge_tab
from gui.tabs.recording_tab import setup_recording_tab
from gui.tabs.console_tab import ConsoleWidget
from gui.tabs.ecu_tab import EcuTab
from gui.tabs.associative_tab import AssociativeTab
from gui.utils import write_log_to_file
from controllers import (
    CanController, ReplayController, MissingController, ErrorController,
    StepController, ManualController, BinaryController, WizardController, SnifferController
)
from controllers.associative_controller import AssociativeController

logger = logging.getLogger("App")


class CanSimulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CAN Simulator GUI")
        self.root.geometry("1000x850")

        self.can = CanInterface()
        self.sim_thread = None
        self.binary_thread = None
        self.loaded_frames = []
        self.step_frames = []
        self.step_idx = 0
        self.binary_frames = []

        self.manual_cyclic_active = False
        self.manual_cyclic_thread = None

        self.replay_use_timestamps = tk.BooleanVar(value=False)

        # Kreator
        self.wizard_frames = []
        self.wizard_id_var = tk.StringVar()
        self.wizard_data_var = tk.StringVar()
        self.wizard_extended_var = tk.BooleanVar(value=False)
        self.wizard_mode_var = tk.StringVar(value="single")
        self.wizard_sequence = []
        self.wizard_target = None
        self.wizard_left = 0
        self.wizard_right = 0
        self.wizard_history = []
        self.wizard_answer = None
        self.wizard_answer_event = threading.Event()

        # Sniffer
        self.sniffer_running = False
        self.sniffer_filter_var = tk.BooleanVar(value=False)
        self.sniffer_queue = []
        self.sniffer_lock = threading.Lock()
        self.sniffer_last_data = {}

        # Rejestr artefaktów
        self.discovered_artifacts = {}

        # Kontrolery
        self.can_ctrl = CanController(self)
        self.replay_ctrl = ReplayController(self)
        self.missing_ctrl = MissingController(self)
        self.error_ctrl = ErrorController(self)
        self.step_ctrl = StepController(self)
        self.manual_ctrl = ManualController(self)
        self.binary_ctrl = BinaryController(self)
        self.wizard_ctrl = WizardController(self)
        self.sniffer_ctrl = SnifferController(self)
        self.associative_ctrl = AssociativeController(self)

        # Rejestr artefaktów
        self.discovered_artifacts = {}

        self.theme_var = tk.StringVar(value="light")
        self.remote_monitor_tab = None
        # Sidebar i kategorie
        self.sidebar = None
        self.category_frames = {}
        self.current_category = None
        self.dbc_signals = []
        self.chart_last_byte = ""
        self.chart_last_id = ""
        self.bridge_filter = ""
        self.bridge_token = ""
        self.bridge_url = ""
        self._create_widgets()
        self.bind_shortcuts()
        # self.setup_detachable_tabs()  # wyłączone
        self.load_session()
        logger.info("Interfejs GUI utworzony")

    def log(self, msg):
        logger.info(msg)
        self.log_text.config(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.status_var.set(msg)

        if hasattr(self, 'replay_log_enable') and self.replay_log_enable.get():
            log_path = self.replay_log_var.get()
            if log_path:
                write_log_to_file(log_path, msg)

    def register_artifact(self, name, can_id, data, is_extended, context=""):
        self.discovered_artifacts[name] = {
            'id': can_id,
            'data': data,
            'ext': is_extended,
            'context': context
        }
        self.log(f"[Artefakt] Zarejestrowano '{name}': ID=0x{can_id:08X}")

    def _create_widgets(self):
        # Połączenie CAN
        frame_conn = ttk.LabelFrame(self.root, text="Połączenie CAN", padding=5)
        frame_conn.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(frame_conn, text="Interfejs:").grid(row=0, column=0, sticky=tk.W)
        self.entry_iface = ttk.Entry(frame_conn, width=15)
        self.entry_iface.insert(0, "can0")
        self.entry_iface.grid(row=0, column=1, padx=5)

        self.btn_connect = ttk.Button(frame_conn, text="Połącz", command=self.can_ctrl.toggle_connection)
        self.btn_connect.grid(row=0, column=2, padx=5)
        self.btn_export = ttk.Button(frame_conn, text="Eksportuj projekt", command=self.export_project)
        self.btn_export.grid(row=0, column=4, padx=5)
        self.btn_import = ttk.Button(frame_conn, text="Importuj projekt", command=self.import_project)
        self.btn_reset = ttk.Button(frame_conn, text="Resetuj sesję", command=self.reset_session)
        self.btn_reset.grid(row=0, column=6, padx=5)
        self.btn_theme = ttk.Button(frame_conn, text="Zmień motyw", command=self.toggle_theme)
        self.btn_theme.grid(row=0, column=8, padx=5)
        self.btn_import.grid(row=0, column=5, padx=5)

        self.lbl_status = ttk.Label(frame_conn, text="Niepołączony", foreground="red")
        self.lbl_status.grid(row=0, column=3, padx=10)

        # Zakładki
        # Sidebar i główny kontener
        main_panel = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Lewy panel – lista kategorii
        self.sidebar = tk.Listbox(main_panel, width=25, exportselection=False)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        main_panel.add(self.sidebar, weight=0)

        # Prawy panel – kontener na zawartość kategorii
        self.content_frame = ttk.Frame(main_panel)
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        main_panel.add(self.content_frame, weight=1)

        # Definicje kategorii i odpowiadających im funkcji setup
        categories = [
            ("Połączenie CAN", self._create_connection_frame),
            ("Narzędzia niszowe", self._create_niche_frame),
            ("Podstawowe narzędzia", self._create_basic_tools_frame),
            ("Wyszukiwanie i analiza", self._create_search_frame),
            ("Wizualizacja i ML", self._create_viz_ml_frame),
            ("Sieć i zdalny dostęp", self._create_network_frame),
            ("Makra", self._create_macro_frame),
            ("DBC Manager", self._create_dbc_frame),
            ("Uczenie asocjacyjne", self._create_associative_frame),
        ]

        for idx, (cat_name, setup_func) in enumerate(categories):
            self.sidebar.insert(tk.END, cat_name)
            frame = ttk.Frame(self.content_frame)
            self.category_frames[cat_name] = frame
            setup_func(frame)

        self.sidebar.bind('<<ListboxSelect>>', self._on_category_select)
        self.sidebar.selection_set(0)  # domyślnie pierwsza kategoria
        self._on_category_select()     # pokaż pierwszą kategorię


        
        # Log
        frame_log = ttk.LabelFrame(self.root, text="Log", padding=5)
        frame_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.log_text = scrolledtext.ScrolledText(frame_log, height=12, state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.status_var = tk.StringVar(value="Gotowy.")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN).pack(fill=tk.X, padx=10, pady=2)

    def _set_buttons_state(self, state):
        buttons = [
            self.replay_start_btn, self.missing_start_btn, self.error_start_btn,
            self.manual_send_once_btn, self.manual_start_btn, self.binary_start_btn
        ]
        for btn in buttons:
            btn.config(state=state)

        if state == 'disabled':
            disable_buttons = [
                self.replay_pause_btn, self.replay_stop_btn, self.manual_stop_btn,
                self.binary_yes_btn, self.binary_no_btn, self.binary_stop_btn, self.binary_undo_btn
            ]
            for btn in disable_buttons:
                btn.config(state=state)

    def _update_step_preview(self):
        if self.step_frames and self.step_idx < len(self.step_frames):
            cid, data, is_ext = self.step_frames[self.step_idx]
            ext_str = " (EXT)" if is_ext else ""
            self.step_preview.config(text=f"Następna: ID=0x{cid:08X}{ext_str} Data={data.hex().upper()}")
        else:
            self.step_preview.config(text="Koniec listy")

    def _start_sim(self):
        if self.sim_thread and self.sim_thread.is_alive():
            self.sim_thread.stop()
            self.sim_thread.join(timeout=0.5)
        self.sim_thread = SimulationThread(self.can, self.log)

    def _simulation_started(self):
        self.replay_start_btn.config(text="Wznów", state='normal')
        self.replay_pause_btn.config(state='normal')
        self.replay_stop_btn.config(state='normal')

    def pause_sim(self):
        if self.sim_thread:
            self.sim_thread.pause()
            self.replay_start_btn.config(text="Wznów", state='normal')
            self.log("Pauza")

    def stop_sim(self):
        if self.sim_thread:
            self.sim_thread.stop()
            self.log("Zatrzymano")
        self.replay_start_btn.config(text="Start", state='normal')
        self.replay_pause_btn.config(state='disabled')
        self.replay_stop_btn.config(state='disabled')

    def _start_binary_thread(self, ask_callback):
        mode = self.binary_mode.get()
        num_parts = self.binary_parts.get() if mode == 'manual_parts' else 2
        self.binary_thread = BinarySearchThread(
            self.can, self.log, ask_callback, self._binary_done, self._update_binary_progress, app=self
        )
        self.binary_thread.setup(
            self.binary_frames,
            self.binary_interval.get(),
            mode=mode,
            num_parts=num_parts,
            use_timestamps=self.binary_use_timestamps.get()
        )

    def _update_binary_progress(self):
        if self.binary_thread:
            left = self.binary_thread.left
            right = self.binary_thread.right
            mid = self.binary_thread.mid
            total = len(self.binary_frames)
            self.binary_progress.config(text=f"Zakres: [{left} .. {right}]  środek: {mid}  (razem: {total})")
            self._redraw_binary_progress()

    def _redraw_binary_progress(self):
        if not hasattr(self, 'binary_canvas') or not self.binary_frames:
            return
        canvas = self.binary_canvas
        canvas.delete("all")
        total = len(self.binary_frames)
        if total == 0:
            return
        width = canvas.winfo_width()
        if width <= 10:
            width = 600

        if self.binary_thread and self.binary_thread.running:
            left = self.binary_thread.left
            right = self.binary_thread.right
            mid = self.binary_thread.mid
        else:
            left, right = 0, total - 1
            mid = (left + right) // 2

        def idx_to_x(idx):
            return int((idx / (total - 1)) * width) if total > 1 else 0

        x_left = idx_to_x(left)
        x_right = idx_to_x(right)
        x_mid = idx_to_x(mid)

        canvas.create_rectangle(0, 0, width, 30, fill='lightgray', outline='')
        canvas.create_rectangle(x_left, 0, x_right, 30, fill='lightgreen', outline='darkgreen')
        canvas.create_line(x_mid, 0, x_mid, 30, fill='red', width=2)
        canvas.create_text(x_left, 15, text=str(left), anchor='e', font=('Arial', 8))
        canvas.create_text(x_right, 15, text=str(right), anchor='w', font=('Arial', 8))
        canvas.create_text(x_mid, 0, text=str(mid), anchor='s', font=('Arial', 8, 'bold'), fill='red')

    def _binary_done(self):
        self.binary_start_btn.config(state='normal')
        for btn in [self.binary_yes_btn, self.binary_no_btn, self.binary_stop_btn, self.binary_undo_btn]:
            btn.config(state='disabled')
        if hasattr(self, 'binary_export_btn') and self.binary_export_btn:
            self.binary_export_btn.config(state='disabled')
        if hasattr(self, 'binary_send_error_btn'):
            self.binary_send_error_btn.config(state='normal')
            self.binary_send_missing_btn.config(state='normal')
        if hasattr(self, 'binary_send_error_btn'):
            self.binary_send_error_btn.config(state='normal')
            self.binary_send_missing_btn.config(state='normal')
        self.binary_progress.config(text="Wyszukiwanie zakończone.")
        self._redraw_binary_progress()

    def _update_wizard_progress(self):
        if self.wizard_frames:
            total = len(self.wizard_frames)
            self.wizard_progress.config(text=f"Zakres: [{self.wizard_left} .. {self.wizard_right}] (razem: {total})")
            self._redraw_wizard_progress()

    def _redraw_wizard_progress(self):
        canvas = self.wizard_canvas
        canvas.delete("all")
        total = len(self.wizard_frames)
        if total == 0:
            return
        width = canvas.winfo_width()
        if width <= 10:
            width = 600

        left, right = self.wizard_left, self.wizard_right

        def idx_to_x(idx):
            return int((idx / (total - 1)) * width) if total > 1 else 0

        x_left = idx_to_x(left)
        x_right = idx_to_x(right)
        mid = (left + right) // 2
        x_mid = idx_to_x(mid)

        canvas.create_rectangle(0, 0, width, 30, fill='lightgray', outline='')
        canvas.create_rectangle(x_left, 0, x_right, 30, fill='lightblue', outline='darkblue')
        canvas.create_line(x_mid, 0, x_mid, 30, fill='red', width=2)
        canvas.create_text(x_left, 15, text=str(left), anchor='e', font=('Arial', 8))
        canvas.create_text(x_right, 15, text=str(right), anchor='w', font=('Arial', 8))
        canvas.create_text(x_mid, 0, text=str(mid), anchor='s', font=('Arial', 8, 'bold'), fill='red')

    
    def _on_category_select(self, event=None):
        selection = self.sidebar.curselection()
        if not selection:
            return
        cat_name = self.sidebar.get(selection[0])
        # Ukryj wszystkie ramki
        for frame in self.category_frames.values():
            frame.pack_forget()
        # Pokaż wybraną
        self.category_frames[cat_name].pack(fill=tk.BOTH, expand=True)
        self.current_category = cat_name

    def _create_connection_frame(self, parent):
        # Połączenie CAN (tak jak było wcześniej w głównym oknie, ale bez notebooka)
        frame_conn = ttk.LabelFrame(parent, text="Połączenie CAN", padding=5)
        frame_conn.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(frame_conn, text="Interfejs:").grid(row=0, column=0, sticky=tk.W)
        self.entry_iface = ttk.Entry(frame_conn, width=15)
        self.entry_iface.insert(0, "can0")
        self.entry_iface.grid(row=0, column=1, padx=5)

        self.btn_connect = ttk.Button(frame_conn, text="Połącz", command=self.can_ctrl.toggle_connection)
        self.btn_connect.grid(row=0, column=2, padx=5)
        self.btn_export = ttk.Button(frame_conn, text="Eksportuj projekt", command=self.export_project)
        self.btn_export.grid(row=0, column=4, padx=5)
        self.btn_import = ttk.Button(frame_conn, text="Importuj projekt", command=self.import_project)
        self.btn_import.grid(row=0, column=5, padx=5)
        self.btn_reset = ttk.Button(frame_conn, text="Resetuj sesję", command=self.reset_session)
        self.btn_reset.grid(row=0, column=6, padx=5)
        self.btn_theme = ttk.Button(frame_conn, text="Zmień motyw", command=self.toggle_theme)
        self.btn_theme.grid(row=0, column=8, padx=5)

        self.lbl_status = ttk.Label(frame_conn, text="Niepołączony", foreground="red")
        self.lbl_status.grid(row=0, column=3, padx=10)

    def _create_basic_tools_frame(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)

        tab_replay = ttk.Frame(notebook)
        notebook.add(tab_replay, text="Odtwarzanie pliku")
        replay_tab.setup_replay_tab(self, tab_replay)

        tab_missing = ttk.Frame(notebook)
        notebook.add(tab_missing, text="Symulacja modułu")
        missing_tab.setup_missing_tab(self, tab_missing)

        tab_error = ttk.Frame(notebook)
        notebook.add(tab_error, text="Ramki błędu")
        error_tab.setup_error_tab(self, tab_error)

        tab_step = ttk.Frame(notebook)
        notebook.add(tab_step, text="Tryb krokowy")
        step_tab.setup_step_tab(self, tab_step)

        tab_manual = ttk.Frame(notebook)
        notebook.add(tab_manual, text="Wysyłanie ręczne")
        manual_tab.setup_manual_tab(self, tab_manual)

    def _create_search_frame(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)

        tab_binary = ttk.Frame(notebook)
        notebook.add(tab_binary, text="Wyszukiwanie binarne")
        binary_tab.setup_binary_tab(self, tab_binary)

        tab_wizard = ttk.Frame(notebook)
        notebook.add(tab_wizard, text="Kreator wyszukiwania")
        wizard_tab.setup_wizard_tab(self, tab_wizard)

        tab_sniffer = ttk.Frame(notebook)
        notebook.add(tab_sniffer, text="Sniffer CAN")
        sniffer_tab.setup_sniffer_tab(self, tab_sniffer)

    def _create_viz_ml_frame(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)

        tab_chart = ttk.Frame(notebook)
        notebook.add(tab_chart, text="Wykresy")
        chart_tab.setup_chart_tab(self, tab_chart)

        tab_advanced_ml = ttk.Frame(notebook)
        notebook.add(tab_advanced_ml, text="Zaawansowane ML")
        advanced_ml_tab.setup_advanced_ml_tab(self, tab_advanced_ml)

        tab_pattern = ttk.Frame(notebook)
        notebook.add(tab_pattern, text="Analiza wzorców")
        pattern_tab.setup_pattern_tab(self, tab_pattern)

        tab_ml = ttk.Frame(notebook)
        notebook.add(tab_ml, text="Analiza ML")
        ml_analysis_tab.setup_ml_tab(self, tab_ml)

        tab_anomaly = ttk.Frame(notebook)
        notebook.add(tab_anomaly, text="Anomalie CAN")
        setup_anomaly_tab(self, tab_anomaly)

    def _create_network_frame(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)

        tab_server = ttk.Frame(notebook)
        notebook.add(tab_server, text="Serwer TCP")
        server_tab.setup_server_tab(self, tab_server)

        tab_remote = ttk.Frame(notebook)
        notebook.add(tab_remote, text="Zdalny monitoring")
        setup_remote_monitor_tab(self, tab_remote)

        tab_generator = ttk.Frame(notebook)
        notebook.add(tab_generator, text="Generator ruchu")
        generator_tab.setup_generator_tab(self, tab_generator)

        tab_bridge = ttk.Frame(notebook)
        notebook.add(tab_bridge, text="Mostek vCAN")
        setup_bridge_tab(self, tab_bridge)

        tab_recording = ttk.Frame(notebook)
        notebook.add(tab_recording, text="Nagrywanie sesji")
        setup_recording_tab(self, tab_recording)


    def _create_niche_frame(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)

        tab_console = ttk.Frame(notebook)
        notebook.add(tab_console, text="Konsola Python")
        self.console_tab = ConsoleWidget(self)
        # Konsola nie używa setup_, tylko jest widgetem – opakowujemy ją w ramkę
        self.console_tab.pack(in_=tab_console, fill=tk.BOTH, expand=True)

        tab_ecu = ttk.Frame(notebook)
        notebook.add(tab_ecu, text="Emulator ECU")
        self.ecu_tab = EcuTab(self)
        self.ecu_tab.pack(in_=tab_ecu, fill=tk.BOTH, expand=True)

    def _create_macro_frame(self, parent):
        tab_macro = ttk.Frame(parent)
        tab_macro.pack(fill=tk.BOTH, expand=True)
        macro_tab.setup_macro_tab(self, tab_macro)


    def _create_associative_frame(self, parent):
        self.associative_tab = AssociativeTab(self, parent)
        self.associative_tab.pack(fill=tk.BOTH, expand=True)

    def _create_dbc_frame(self, parent):
        tab_dbc = ttk.Frame(parent)
        tab_dbc.pack(fill=tk.BOTH, expand=True)
        setup_dbc_manager_tab(self, tab_dbc)


    def bind_shortcuts(self):
        """Przypisuje globalne skróty klawiszowe."""
        self.root.bind('<F5>', lambda e: self.sniffer_ctrl.start_sniffer() if not self.sniffer_running else None)
        self.root.bind('<F6>', lambda e: self.sniffer_ctrl.stop_sniffer())
        self.root.bind('<F7>', lambda e: self.sniffer_ctrl.clear_sniffer())
        self.root.bind('<Control-l>', lambda e: self.sniffer_ctrl.clear_sniffer())
        self.root.bind('<Control-s>', lambda e: self.export_project())
        self.root.bind('<Control-o>', lambda e: self.import_project())
        # Uczenie asocjacyjne – skróty globalne
        self.root.bind('<Control-h>', lambda e: self.associative_tab.toggle_event())
        self.root.bind('<Control-Shift-V>', lambda e: self.associative_tab.commit_value())
        self.root.bind('<Control-Shift-Z>', lambda e: self.associative_tab.undo_last_value())
        self.root.bind('<Control-Shift-S>', lambda e: self.associative_tab.search_sequence())
        # Można dodać więcej skrótów według potrzeb

    
    def reset_session(self):
        """Resetuje zapisaną sesję."""
        import os
        if os.path.exists("session.json"):
            os.remove("session.json")
            self.log("Sesja zresetowana.")
        else:
            messagebox.showinfo("Reset", "Brak zapisanej sesji.")

    
    def load_session(self):
        """Wczytuje poprzednią sesję."""
        from session_manager import SessionManager
        if SessionManager.load_session(self):
            self.log("Przywrócono poprzednią sesję.")
    
    def show_help(self, event=None):
        """Wyświetla okno pomocy."""
        help_win = tk.Toplevel(self.root)
        help_win.title("Pomoc – CAN Simulator GUI")
        help_win.geometry("650x500")
        help_win.transient(self.root)
        help_win.grab_set()

        text = tk.Text(help_win, wrap=tk.WORD, padx=10, pady=10)
        text.pack(fill=tk.BOTH, expand=True)

        help_content = """CAN Simulator GUI – skróty i wskazówki

SKRÓTY KLAWISZOWE:
  F1          – Pokaż to okno pomocy
  F5          – Start Sniffera
  F6          – Stop Sniffera
  F7 / Ctrl+L – Wyczyść Sniffera
  Ctrl+S      – Eksportuj projekt
  Ctrl+O      – Importuj projekt

ZAKŁADKI:
  • Odtwarzanie pliku – wczytaj candump i odtwórz z interwałem.
  • Symulacja modułu – zdefiniuj ramki wysyłane cyklicznie.
  • Ramki błędu – zdefiniuj sekwencję symulującą błąd.
  • Tryb krokowy – ręczne wysyłanie ramek z pliku.
  • Wysyłanie ręczne – wyślij pojedynczą ramkę.
  • Wyszukiwanie binarne – interaktywne znajdowanie ramki odpowiedzialnej za zjawisko.
  • Kreator wyszukiwania – znajdowanie konkretnej ramki/sekwencji.
  • Sniffer CAN – podgląd ruchu na magistrali w czasie rzeczywistym.
  • Wykresy – wizualizacja zmian wartości bajtów w czasie.
  • Serwer TCP – udostępnienie strumienia CAN przez sieć.
  • Analiza wzorców – wykrywanie anomalii za pomocą autoenkodera.
  • Analiza ML – klasyfikacja sesji, wykrywanie anomalii.
  • Generator ruchu – definiowanie własnych sekwencji testowych.
  • Makra – nagrywanie i odtwarzanie sekwencji akcji.

PRZYKŁADOWY PROJEKT:
  Kliknij przycisk „Przykładowy projekt” w głównym oknie,
  aby wygenerować zestaw plików demonstracyjnych w katalogu domowym.

WIĘCEJ INFORMACJI:
  Pełna dokumentacja dostępna na GitHub Wiki projektu.
"""
        text.insert(tk.END, help_content)
        text.config(state=tk.DISABLED)

        ttk.Button(help_win, text="Zamknij", command=help_win.destroy).pack(pady=5)

    def on_closing(self):
        self.manual_cyclic_active = False
        if self.sim_thread:
            self.sim_thread.stop()
        if self.binary_thread:
            self.binary_thread.stop()
        from session_manager import SessionManager
        SessionManager.save_session(self)
        self.can.disconnect()
        self.root.destroy()
    def register_artifact(self, name, can_id, data, is_extended, context=""):
        self.discovered_artifacts[name] = {
            'id': can_id,
            'data': data,
            'ext': is_extended,
            'context': context
        }
        self.log(f"[Artefakt] Zarejestrowano '{name}': ID=0x{can_id:08X}")

    def get_artifact(self, name):
        return self.discovered_artifacts.get(name)

    def export_project(self):
        from tkinter import filedialog
        from project_manager import ProjectManager
        filepath = filedialog.asksaveasfilename(defaultextension=".csp", filetypes=[("CAN Simulator Project", "*.csp")])
        if not filepath:
            return
        try:
            ProjectManager.export_project(self, filepath)
            self.log(f"Projekt wyeksportowany do {filepath}")
        except Exception as e:
            messagebox.showerror("Błąd eksportu", str(e))

    def import_project(self):
        from tkinter import filedialog
        from project_manager import ProjectManager
        filepath = filedialog.askopenfilename(filetypes=[("CAN Simulator Project", "*.csp")])
        if not filepath:
            return
        try:
            ProjectManager.import_project(self, filepath)
            self.log(f"Projekt zaimportowany z {filepath}")
        except Exception as e:
            messagebox.showerror("Błąd importu", str(e))

    def detach_tab_disabled(self, *args):
        """Odrywa zakładkę do osobnego okna."""
        tab_frame = self.notebook.nametowidget(self.notebook.tabs()[tab_index])
        tab_text = self.notebook.tab(tab_index, 'text')
        self.notebook.forget(tab_index)

        new_win = tk.Toplevel(self.root)
        new_win.title(f"CAN Simulator – {tab_text}")
        new_win.geometry("800x600")
        new_win.protocol("WM_DELETE_WINDOW", lambda: self.attach_tab(tab_frame, tab_text, new_win))
        tab_frame.pack(fill=tk.BOTH, expand=True)

    def attach_tab_disabled(self, *args):
        """Przywraca zakładkę do głównego okna."""
        popup.destroy()
        self.notebook.add(tab_frame, text=tab_text)
        self.notebook.select(tab_frame)

    def setup_detachable_tabs_disabled(self):
        pass
    def _show_tab_menu_disabled(self, event):
        pass
    def _detach_selected_tab_disabled(self):
        pass
    def show_progress(self, title="Proszę czekać", maximum=100):
        """Pokazuje okno z paskiem postępu."""
        self.progress_win = tk.Toplevel(self.root)
        self.progress_win.title(title)
        self.progress_win.geometry("300x100")
        self.progress_win.transient(self.root)
        self.progress_win.grab_set()
        tk.Label(self.progress_win, text=title).pack(pady=10)
        self.progress_bar = ttk.Progressbar(self.progress_win, length=250, mode='determinate', maximum=maximum)
        self.progress_bar.pack(pady=10)
        return self.progress_bar

    def hide_progress(self):
        if hasattr(self, 'progress_win'):
            self.progress_win.destroy()

    def toggle_theme(self):
        """Przełącza między jasnym a ciemnym motywem."""
        if self.theme_var.get() == "light":
            self._apply_dark_theme()
            self.theme_var.set("dark")
        else:
            self._apply_light_theme()
            self.theme_var.set("light")
        self.log(f"Motyw zmieniony na {self.theme_var.get()}")

    def _apply_dark_theme(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', background='#2e2e2e', foreground='#ffffff')
        style.configure('TLabel', background='#2e2e2e', foreground='#ffffff')
        style.configure('TFrame', background='#2e2e2e')
        style.configure('TLabelframe', background='#2e2e2e', foreground='#ffffff')
        style.configure('TNotebook', background='#2e2e2e', foreground='#ffffff')
        style.configure('TNotebook.Tab', background='#3e3e3e', foreground='#ffffff')
        self.root.configure(bg='#2e2e2e')
        self.log_text.configure(bg='#1e1e1e', fg='#ffffff')



    def _apply_light_theme(self):
        style = ttk.Style()
        style.theme_use('default')
        self.root.configure(bg='#f0f0f0')
        self.log_text.configure(bg='white', fg='black')
